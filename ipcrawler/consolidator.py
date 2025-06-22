#!/usr/bin/env python3
"""
ipcrawler Results Consolidator
==============================

A comprehensive HTML report generator that consolidates all ipcrawler scan results
into a single, beautifully themed, interactive HTML report with intelligent prioritization.

Features:
- Spider/web-themed dark interface (avoiding typical AI purple/blue colors)
- Intelligent result prioritization (ports, vhosts, critical findings first)
- Rich integration for consistent styling with ipcrawler
- Interactive collapsible sections
- Smart parsing of different result file types
- Search functionality and responsive design
"""

import os
import re
import xml.etree.ElementTree as ET
import time
import signal
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import argparse

# Rich imports for consistent theming
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not available. Install with: pip install rich")

@dataclass
class ServiceInfo:
    """Information about a discovered service"""
    port: int
    protocol: str
    service: str
    state: str = "open"
    version: str = ""
    banner: str = ""
    ssl_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WebInfo:
    """Information about web services"""
    url: str
    title: str = ""
    status_code: int = 0
    server: str = ""
    technologies: List[str] = field(default_factory=list)
    directories: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    vhosts: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)

@dataclass
class TargetResults:
    """Consolidated results for a single target"""
    target: str
    ip_address: str = ""
    open_ports: List[ServiceInfo] = field(default_factory=list)
    web_services: List[WebInfo] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    manual_commands: List[str] = field(default_factory=list)
    scan_timestamp: str = ""
    scan_duration: str = ""

class ResultParser:
    """Parses different types of ipcrawler result files"""
    
    def __init__(self):
        self.nmap_port_regex = re.compile(r'(\d+)/(tcp|udp)\s+(open|closed|filtered)\s+(.+)')
        self.http_title_regex = re.compile(r'<title[^>]*>([^<]+)</title>', re.IGNORECASE)
        self.server_regex = re.compile(r'Server:\s*(.+)', re.IGNORECASE)
        
    def parse_nmap_xml(self, xml_path: str) -> List[ServiceInfo]:
        """Parse nmap XML output to extract service information"""
        services = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for host in root.findall('host'):
                for port in host.findall('.//port'):
                    port_id = port.get('portid')
                    protocol = port.get('protocol')
                    
                    if port_id is None or protocol is None:
                        continue
                    
                    port_num = int(port_id)
                    
                    state_elem = port.find('state')
                    state = state_elem.get('state') if state_elem is not None else 'unknown'
                    
                    service_elem = port.find('service')
                    if service_elem is not None:
                        service_name = service_elem.get('name', 'unknown')
                        version = service_elem.get('version', '')
                        product = service_elem.get('product', '')
                        if product and version:
                            version = f"{product} {version}".strip()
                        elif product:
                            version = product
                    else:
                        service_name = 'unknown'
                        version = ''
                    
                    # Check for script results (banners, etc.)
                    banner = ""
                    for script in port.findall('script'):
                        script_id = script.get('id', '')
                        if 'banner' in script_id or 'service' in script_id:
                            banner = script.get('output', '')[:200]  # Limit banner size
                            break
                    
                    if state == 'open':
                        services.append(ServiceInfo(
                            port=port_num,
                            protocol=protocol,
                            service=service_name,
                            state=state,
                            version=version,
                            banner=banner
                        ))
                        
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing XML {xml_path}: {e}[/red]")
            else:
                print(f"Error parsing XML {xml_path}: {e}")
        
        return services
    
    def parse_nmap_text(self, text_path: str) -> List[ServiceInfo]:
        """Parse nmap text output to extract service information"""
        services = []
        try:
            with open(text_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for line in content.split('\n'):
                match = self.nmap_port_regex.search(line)
                if match:
                    port = int(match.group(1))
                    protocol = match.group(2)
                    state = match.group(3)
                    service_info = match.group(4).strip()
                    
                    # Parse service name and version
                    service_parts = service_info.split()
                    service_name = service_parts[0] if service_parts else 'unknown'
                    version = ' '.join(service_parts[1:]) if len(service_parts) > 1 else ''
                    
                    if state == 'open':
                        services.append(ServiceInfo(
                            port=port,
                            protocol=protocol,
                            service=service_name,
                            state=state,
                            version=version
                        ))
                        
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing text {text_path}: {e}[/red]")
            else:
                print(f"Error parsing text {text_path}: {e}")
        
        return services
    
    def parse_web_response(self, file_path: str, url: str = "") -> WebInfo:
        """Parse web service response files (curl, whatweb, etc.)"""
        web_info = WebInfo(url=url)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract title
            title_match = self.http_title_regex.search(content)
            if title_match:
                web_info.title = title_match.group(1).strip()
            
            # Extract server info
            server_match = self.server_regex.search(content)
            if server_match:
                web_info.server = server_match.group(1).strip()
            
            # Extract status code from HTTP response
            status_match = re.search(r'HTTP/\d\.\d\s+(\d+)', content)
            if status_match:
                web_info.status_code = int(status_match.group(1))
            
            # Extract technologies from whatweb output
            if 'WhatWeb report' in content:
                # Parse technologies from whatweb summary
                summary_match = re.search(r'Summary\s*:\s*(.+)', content)
                if summary_match:
                    tech_line = summary_match.group(1)
                    # Extract technologies like X-Powered-By[Next.js], HTTPServer[cloudflare]
                    tech_matches = re.findall(r'(\w+(?:-\w+)*)\[([^\]]+)\]', tech_line)
                    seen_techs = set()
                    for tech_type, tech_value in tech_matches:
                        tech_entry = f"{tech_type}: {tech_value}"
                        if tech_entry not in seen_techs:
                            web_info.technologies.append(tech_entry)
                            seen_techs.add(tech_entry)
            
            # Extract X-Powered-By (avoid duplicates from whatweb)
            powered_by_match = re.search(r'X-Powered-By:\s*(.+)', content, re.IGNORECASE)
            if powered_by_match:
                powered_by_tech = f"Powered-By: {powered_by_match.group(1).strip()}"
                if powered_by_tech not in web_info.technologies:
                    web_info.technologies.append(powered_by_tech)
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing web response {file_path}: {e}[/red]")
            else:
                print(f"Error parsing web response {file_path}: {e}")
        
        return web_info
    
    def parse_directory_scan(self, file_path: str) -> Tuple[List[str], List[str]]:
        """Parse directory/file enumeration results (feroxbuster, dirbuster, etc.)"""
        directories = []
        files = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse feroxbuster/dirbuster output
            for line in content.split('\n'):
                line = line.strip()
                
                # Look for successful directory/file discoveries
                if re.search(r'\b(200|301|302|403)\b', line):
                    # Extract path from the line
                    path_match = re.search(r'(https?://[^\s]+|/[^\s]*)', line)
                    if path_match:
                        path = path_match.group(1)
                        if path.endswith('/'):
                            directories.append(path)
                        else:
                            files.append(path)
                            
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing directory scan {file_path}: {e}[/red]")
            else:
                print(f"Error parsing directory scan {file_path}: {e}")
        
        return directories, files
    
    def parse_vhost_scan(self, file_path: str) -> List[str]:
        """Parse virtual host enumeration results"""
        vhosts = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Look for successful vhost discoveries
            for line in content.split('\n'):
                line = line.strip()
                # Look for status codes indicating successful vhost discovery
                if re.search(r'\b(200|301|302|403)\b', line) and not re.search(r'\b404\b', line):
                    # Extract hostname from the line
                    host_match = re.search(r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
                    if host_match:
                        vhost = host_match.group(1)
                        if vhost not in vhosts:
                            vhosts.append(vhost)
                            
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing vhost scan {file_path}: {e}[/red]")
            else:
                print(f"Error parsing vhost scan {file_path}: {e}")
        
        return vhosts
    
    def parse_vulnerability_scan(self, file_path: str) -> List[str]:
        """Parse vulnerability scan results (nikto, nmap scripts, etc.)"""
        vulnerabilities = []
        seen_vulns = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse nikto output specifically
            if 'nikto' in str(file_path).lower():
                vulnerabilities.extend(self._parse_nikto_vulnerabilities(content, seen_vulns))
            
            # Parse nmap script output
            if 'nmap' in str(file_path).lower():
                vulnerabilities.extend(self._parse_nmap_vulnerabilities(content, seen_vulns))
            
            # Generic vulnerability patterns
            vuln_patterns = [
                (r'OSVDB-\d+[^\\n]*', 'OSVDB Reference'),
                (r'CVE-\d{4}-\d+[^\\n]*', 'CVE Reference'),
                (r'VULNERABLE[^\\n]*', 'Vulnerability Found'),
            ]
            
            for pattern, vuln_type in vuln_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    vuln_text = match.group(0).strip()
                    if len(vuln_text) > 10:
                        # Clean up the vulnerability text
                        vuln_text = self._clean_vulnerability_text(vuln_text)
                        vuln_key = vuln_text[:100].lower()  # Use first 100 chars as dedup key
                        if vuln_key not in seen_vulns:
                            vulnerabilities.append(vuln_text)
                            seen_vulns.add(vuln_key)
                            
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing vulnerability scan {file_path}: {e}[/red]")
            else:
                print(f"Error parsing vulnerability scan {file_path}: {e}")
        
        return vulnerabilities
    
    def _parse_nikto_vulnerabilities(self, content: str, seen_vulns: set) -> List[str]:
        """Parse nikto-specific vulnerability output"""
        vulnerabilities = []
        
        # Nikto uses + to indicate findings
        nikto_lines = []
        for line in content.split('\\n'):
            line = line.strip()
            if line.startswith('+ ') and len(line) > 10:
                # Remove the + prefix and clean up
                vuln_text = line[2:].strip()
                vuln_text = self._clean_vulnerability_text(vuln_text)
                vuln_key = vuln_text[:100].lower()
                if vuln_key not in seen_vulns:
                    nikto_lines.append(vuln_text)
                    seen_vulns.add(vuln_key)
        
        # Group similar vulnerabilities
        grouped_vulns = self._group_similar_vulnerabilities(nikto_lines)
        vulnerabilities.extend(grouped_vulns)
        
        return vulnerabilities
    
    def _parse_nmap_vulnerabilities(self, content: str, seen_vulns: set) -> List[str]:
        """Parse nmap script vulnerability output"""
        vulnerabilities = []
        
        # Look for nmap script output patterns
        script_patterns = [
            r'\\|_[^\\n]+vulnerable[^\\n]*',
            r'\\|_[^\\n]+VULNERABLE[^\\n]*',
            r'\\|[^\\n]+CVE-[^\\n]*',
            r'\\|[^\\n]+OSVDB-[^\\n]*'
        ]
        
        for pattern in script_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                vuln_text = match.group(0).strip()
                # Clean up nmap script formatting
                vuln_text = re.sub(r'^\\|_?\\s*', '', vuln_text)
                vuln_text = self._clean_vulnerability_text(vuln_text)
                vuln_key = vuln_text[:100].lower()
                if len(vuln_text) > 10 and vuln_key not in seen_vulns:
                    vulnerabilities.append(vuln_text)
                    seen_vulns.add(vuln_key)
        
        return vulnerabilities
    
    def _clean_vulnerability_text(self, text: str) -> str:
        """Clean up vulnerability text for better display"""
        # Remove backslash-n artifacts
        text = text.replace('\\n', ' ')
        
        # Remove multiple spaces
        text = re.sub(r'\\s+', ' ', text)
        
        # Remove trailing backslashes
        text = text.rstrip('\\\\')
        
        # Truncate long URLs but keep them readable
        if 'http' in text and len(text) > 150:
            # Find URL and truncate it nicely
            url_match = re.search(r'https?://[^\\s]+', text)
            if url_match:
                url = url_match.group(0)
                if len(url) > 60:
                    truncated_url = url[:50] + '...[truncated]'
                    text = text.replace(url, truncated_url)
        
        # Overall length limit
        if len(text) > 300:
            text = text[:297] + '...'
        
        return text.strip()
    
    def _group_similar_vulnerabilities(self, vulns: List[str]) -> List[str]:
        """Group similar vulnerabilities to reduce repetition"""
        grouped = {}
        
        for vuln in vulns:
            # Extract the main issue (before the colon or first URL)
            main_issue = vuln.split(':')[0].split('http')[0].strip()
            
            # Remove file paths to group similar issues
            main_issue = re.sub(r'/[^\\s]*\\.(php|html|txt|js)', '/[file]', main_issue)
            
            if main_issue in grouped:
                # Count occurrences instead of repeating
                if 'instances' not in grouped[main_issue]:
                    grouped[main_issue]['instances'] = 1
                    grouped[main_issue]['example'] = grouped[main_issue]['text']
                grouped[main_issue]['instances'] += 1
            else:
                grouped[main_issue] = {'text': vuln, 'instances': 1}
        
        # Format grouped results
        result = []
        for key, data in grouped.items():
            if data['instances'] > 1:
                result.append(f"{data['example']} (Found {data['instances']} instances)")
            else:
                result.append(data['text'])
        
        return result

class IPCrawlerConsolidator:
    """Main consolidator class for ipcrawler results"""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.parser = ResultParser()
        self.targets: Dict[str, TargetResults] = {}
        self.last_update_time = 0.0
        self.watch_mode = False
        self._stop_watching = False
        self.specific_target: Optional[str] = None
        self.auto_partial_reports = True  # Auto-generate reports for interrupted scans
        self.daemon_mode = False  # Real-time monitoring mode
        self.update_interval = 5  # Seconds between updates in daemon mode
        self.known_targets = set()  # Track targets we're already monitoring
        
    def discover_targets(self) -> List[str]:
        """Discover all target directories in the results folder"""
        targets = []
        
        if not self.results_dir.exists():
            if RICH_AVAILABLE:
                console.print(f"[red]Results directory {self.results_dir} does not exist[/red]")
            else:
                print(f"Results directory {self.results_dir} does not exist")
            return targets
        
        for item in self.results_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Skip directories like 'scans' that might exist at root level
                scan_dir = item / "scans"
                if scan_dir.exists():
                    targets.append(item.name)
                    
        return sorted(targets)
    
    def detect_interrupted_scans(self) -> List[str]:
        """Detect targets with potentially interrupted scans"""
        interrupted_targets = []
        
        for target in self.discover_targets():
            target_dir = self.results_dir / target
            scans_dir = target_dir / "scans"
            report_dir = target_dir / "report"
            
            if not scans_dir.exists():
                continue
                
            # Check if there's scan data but no recent report
            has_scan_data = False
            latest_scan_time = 0
            
            # Look for any scan files
            for scan_file in scans_dir.rglob("*"):
                if scan_file.is_file() and not scan_file.name.startswith('.'):
                    has_scan_data = True
                    try:
                        scan_time = scan_file.stat().st_mtime
                        if scan_time > latest_scan_time:
                            latest_scan_time = scan_time
                    except (OSError, FileNotFoundError):
                        continue
            
            if not has_scan_data:
                continue
                
            # Check if report exists and is recent
            report_file = report_dir / "ipcrawler_report.html"
            report_exists = report_file.exists()
            report_recent = False
            
            if report_exists:
                try:
                    report_time = report_file.stat().st_mtime
                    # Consider report recent if it's within 5 minutes of latest scan
                    report_recent = (latest_scan_time - report_time) < 300
                except (OSError, FileNotFoundError):
                    report_exists = False
            
            # Target is interrupted if it has scan data but no recent report
            if has_scan_data and (not report_exists or not report_recent):
                interrupted_targets.append(target)
                
        return interrupted_targets
    
    def detect_new_scans(self) -> List[str]:
        """Detect newly started scans (targets with scan directories but no reports yet)"""
        new_scans = []
        current_targets = set(self.discover_targets())
        
        for target in current_targets:
            if target not in self.known_targets:
                target_dir = self.results_dir / target
                scans_dir = target_dir / "scans"
                
                # Check if scan has actually started (has some files)
                if scans_dir.exists():
                    scan_files = list(scans_dir.rglob("*"))
                    if any(f.is_file() and not f.name.startswith('.') for f in scan_files):
                        new_scans.append(target)
                        self.known_targets.add(target)
        
        return new_scans
    
    def start_daemon_mode(self, update_interval: int = 5):
        """Start background daemon mode for real-time report generation"""
        self.daemon_mode = True
        self.update_interval = update_interval
        self._stop_watching = False
        
        if RICH_AVAILABLE:
            console.print(f"[bold cyan]🕷️  Starting ipcrawler Live Report Daemon[/bold cyan]")
            console.print(f"[dim]📂 Monitoring: {self.results_dir}[/dim]")
            console.print(f"[dim]🔄 Update interval: {update_interval} seconds[/dim]")
            console.print(f"[dim]⏹️  Press Ctrl+C to stop[/dim]")
        else:
            print(f"🕷️  Starting ipcrawler Live Report Daemon")
            print(f"📂 Monitoring: {self.results_dir}")
            print(f"🔄 Update interval: {update_interval} seconds")
            print(f"⏹️  Press Ctrl+C to stop")
        
        # Initialize known targets
        self.known_targets = set(self.discover_targets())
        
        # Start monitoring loop
        try:
            while not self._stop_watching:
                self._daemon_update_cycle()
                time.sleep(self.update_interval)
        except KeyboardInterrupt:
            if RICH_AVAILABLE:
                console.print("\n[yellow]🕸️  Live Report Daemon stopped by user[/yellow]")
            else:
                print("\n🕸️  Live Report Daemon stopped by user")
    
    def _daemon_update_cycle(self):
        """Single update cycle for daemon mode"""
        try:
            # Check for new scans starting
            new_scans = self.detect_new_scans()
            
            # Generate initial reports for new scans
            for target in new_scans:
                if RICH_AVAILABLE:
                    console.print(f"[green]🎯 New scan detected: {target}[/green]")
                else:
                    print(f"🎯 New scan detected: {target}")
                
                # Generate initial target-specific report
                self._generate_live_report(target)
            
            # Update reports for all active targets
            active_targets = self._get_active_scan_targets()
            for target in active_targets:
                self._generate_live_report(target)
            
            # Generate consolidated report if we have any targets
            if self.known_targets:
                self._generate_consolidated_live_report()
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error in daemon update cycle: {e}[/red]")
            else:
                print(f"Error in daemon update cycle: {e}")
    
    def _generate_consolidated_live_report(self):
        """Generate the consolidated report in live mode"""
        try:
            # Parse results for all known targets
            self.consolidate_all_targets(None)
            
            # Generate consolidated HTML report
            consolidated_output = self.results_dir / "consolidated_report.html"
            html_content = self._generate_html_template(partial=False)
            
            with open(consolidated_output, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error generating consolidated live report: {e}[/red]")
            else:
                print(f"Error generating consolidated live report: {e}")
    
    def _get_active_scan_targets(self) -> List[str]:
        """Get targets that have active or recent scan activity"""
        active_targets = []
        current_time = time.time()
        
        for target in self.known_targets:
            target_dir = self.results_dir / target
            scans_dir = target_dir / "scans"
            
            if not scans_dir.exists():
                continue
            
            # Check for recent file activity (within last 2 minutes)
            latest_activity = 0
            for scan_file in scans_dir.rglob("*"):
                if scan_file.is_file():
                    try:
                        file_time = scan_file.stat().st_mtime
                        if file_time > latest_activity:
                            latest_activity = file_time
                    except (OSError, FileNotFoundError):
                        continue
            
            # Consider target active if there's been activity in last 2 minutes
            if current_time - latest_activity < 120:
                active_targets.append(target)
        
        return active_targets
    
    def _generate_live_report(self, target: str):
        """Generate a live report for a specific target"""
        try:
            # Parse current results for this target
            target_data = self.parse_target_results(target)
            self.targets[target] = target_data
            
            # Generate report
            target_dir = self.results_dir / target / "report"
            target_dir.mkdir(parents=True, exist_ok=True)
            output_file = target_dir / "ipcrawler_report.html"
            
            # Set specific target for report generation
            original_target = self.specific_target
            self.specific_target = target
            
            # Generate HTML content
            html_content = self._generate_html_template(partial=True)
            
            # Write report
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Restore original target
            self.specific_target = original_target
            
            if RICH_AVAILABLE:
                console.print(f"[dim]📄 Updated: {target}[/dim]")
            
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error generating live report for {target}: {e}[/red]")
            else:
                print(f"Error generating live report for {target}: {e}")
    
    def parse_target_results(self, target: str) -> TargetResults:
        """Parse all results for a specific target"""
        target_dir = self.results_dir / target
        scan_dir = target_dir / "scans"
        
        results = TargetResults(target=target)
        
        # Determine IP address from target name or nmap results
        if re.match(r'\d+\.\d+\.\d+\.\d+', target):
            results.ip_address = target
        
        # Parse port scans first (XML preferred, then text)
        xml_dir = scan_dir / "xml"
        if xml_dir.exists():
            for xml_file in xml_dir.glob("*nmap*.xml"):
                services = self.parser.parse_nmap_xml(str(xml_file))
                results.open_ports.extend(services)
        
        # If no XML results, parse text files
        if not results.open_ports:
            for nmap_file in scan_dir.glob("*nmap*.txt"):
                services = self.parser.parse_nmap_text(str(nmap_file))
                results.open_ports.extend(services)
        
        # Remove duplicates and sort by port
        unique_ports = {}
        for service in results.open_ports:
            key = (service.port, service.protocol)
            if key not in unique_ports or len(service.version) > len(unique_ports[key].version):
                unique_ports[key] = service
        results.open_ports = sorted(unique_ports.values(), key=lambda s: s.port)
        
        # Parse service-specific results
        for port_dir in scan_dir.glob("tcp*"):
            if port_dir.is_dir():
                port_num = int(port_dir.name.replace('tcp', ''))
                self._parse_service_dir(port_dir, port_num, results)
        
        # Parse global log files
        self._parse_log_files(scan_dir, results)
        
        # Set scan timestamp from directory modification time
        if target_dir.exists():
            timestamp = datetime.fromtimestamp(target_dir.stat().st_mtime)
            results.scan_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        return results
    
    def _parse_service_dir(self, port_dir: Path, port_num: int, results: TargetResults):
        """Parse results for a specific service/port"""
        
        # Find corresponding web service info
        web_service = None
        for service in results.open_ports:
            if service.port == port_num:
                if service.service in ['http', 'https', 'http-alt', 'http-proxy']:
                    scheme = 'https' if service.service == 'https' or 'ssl' in service.service.lower() else 'http'
                    url = f"{scheme}://{results.target}:{port_num}"
                    web_service = WebInfo(url=url)
                    results.web_services.append(web_service)
                break
        
        # Parse all files in the service directory
        for file_path in port_dir.glob("*"):
            if file_path.is_file():
                filename = file_path.name.lower()
                
                # Web responses (curl, etc.)
                if 'curl' in filename and filename.endswith('.html'):
                    if web_service:
                        parsed_web = self.parser.parse_web_response(str(file_path), web_service.url)
                        web_service.title = parsed_web.title or web_service.title
                        web_service.server = parsed_web.server or web_service.server
                        web_service.status_code = parsed_web.status_code or web_service.status_code
                        # Deduplicate technologies
                        for tech in parsed_web.technologies:
                            if tech not in web_service.technologies:
                                web_service.technologies.append(tech)
                
                # WhatWeb results
                elif 'whatweb' in filename:
                    if web_service:
                        parsed_web = self.parser.parse_web_response(str(file_path), web_service.url)
                        # Deduplicate technologies
                        for tech in parsed_web.technologies:
                            if tech not in web_service.technologies:
                                web_service.technologies.append(tech)
                
                # Directory enumeration
                elif any(tool in filename for tool in ['feroxbuster', 'dirbuster', 'dirb', 'gobuster']):
                    directories, files = self.parser.parse_directory_scan(str(file_path))
                    if web_service:
                        # Deduplicate directories and files
                        for directory in directories:
                            if directory not in web_service.directories:
                                web_service.directories.append(directory)
                        for file in files:
                            if file not in web_service.files:
                                web_service.files.append(file)
                
                # Virtual host enumeration
                elif 'vhost' in filename or 'subdomain' in filename:
                    vhosts = self.parser.parse_vhost_scan(str(file_path))
                    if web_service:
                        # Deduplicate vhosts
                        for vhost in vhosts:
                            if vhost not in web_service.vhosts:
                                web_service.vhosts.append(vhost)
                
                # Vulnerability scans
                elif any(tool in filename for tool in ['nikto', 'nmap']):
                    vulns = self.parser.parse_vulnerability_scan(str(file_path))
                    if web_service:
                        # Deduplicate vulnerabilities
                        for vuln in vulns:
                            if vuln not in web_service.vulnerabilities:
                                web_service.vulnerabilities.append(vuln)
                    # Also add to global vulnerabilities list (deduplicated)
                    for vuln in vulns:
                        if vuln not in results.vulnerabilities:
                            results.vulnerabilities.append(vuln)
    
    def _parse_log_files(self, scan_dir: Path, results: TargetResults):
        """Parse global log files"""
        
        # Parse patterns log
        patterns_file = scan_dir / "_patterns.log"
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and len(line) > 5:
                        if line not in results.patterns:
                            results.patterns.append(line)
                            
            except Exception as e:
                if RICH_AVAILABLE:
                    console.print(f"[red]Error parsing patterns log: {e}[/red]")
        
        # Parse manual commands
        manual_file = scan_dir / "_manual_commands.txt"
        if manual_file.exists():
            try:
                with open(manual_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and len(line) > 10:
                        results.manual_commands.append(line)
                        
            except Exception as e:
                if RICH_AVAILABLE:
                    console.print(f"[red]Error parsing manual commands: {e}[/red]")
    
    def consolidate_all_targets(self, specific_target: Optional[str] = None) -> Dict[str, TargetResults]:
        """Parse results for all discovered targets or a specific target"""
        targets = self.discover_targets()
        
        # Filter to specific target if requested
        if specific_target:
            if specific_target in targets:
                targets = [specific_target]
                if RICH_AVAILABLE:
                    console.print(f"[cyan]🕷️  Generating report for target: {specific_target}[/cyan]")
                else:
                    print(f"Generating report for target: {specific_target}")
            else:
                if RICH_AVAILABLE:
                    console.print(f"[red]Target '{specific_target}' not found. Available targets: {', '.join(targets)}[/red]")
                else:
                    print(f"Target '{specific_target}' not found. Available targets: {', '.join(targets)}")
                return {}
        else:
            if RICH_AVAILABLE:
                console.print(f"[cyan]🕷️  Discovered {len(targets)} targets: {', '.join(targets)}[/cyan]")
            else:
                print(f"Discovered {len(targets)} targets: {', '.join(targets)}")
        
        for target in targets:
            if RICH_AVAILABLE:
                console.print(f"[green]📡 Parsing results for {target}...[/green]")
            else:
                print(f"Parsing results for {target}...")
                
            self.targets[target] = self.parse_target_results(target)
        
        return self.targets
    
    def generate_html_report(self, output_file: str = None, force_update: bool = False, static_mode: bool = False):
        """Generate the consolidated HTML report"""
        
        # Check if we need to update (for incremental mode)
        if not force_update and self.last_update_time > 0:
            newest_file_time = self._get_newest_file_time()
            if newest_file_time <= self.last_update_time:
                return  # No new files since last update
        
        if not self.targets or force_update:
            self.consolidate_all_targets(self.specific_target)
        
        if not self.targets:
            if RICH_AVAILABLE:
                console.print("[red]No targets found to generate report[/red]")
            else:
                print("No targets found to generate report")
            return
        
        # Determine output file(s) based on targets
        output_files = []
        
        if not output_file:
            # Always generate individual target reports
            for target_name in self.targets.keys():
                target_dir = self.results_dir / target_name / "report"
                target_dir.mkdir(parents=True, exist_ok=True)
                target_output = target_dir / "ipcrawler_report.html"
                output_files.append(str(target_output))
            
            # Always create consolidated report in results root
            consolidated_output = self.results_dir / "consolidated_report.html"
            output_files.append(str(consolidated_output))
        else:
            # Custom output file specified
            output_files.append(output_file)
        
        # Generate reports
        for i, output_path in enumerate(output_files):
            if len(self.targets) > 1 and i < len(self.targets) and not output_file:
                # Generate individual target report
                target_name = list(self.targets.keys())[i]
                old_targets = self.targets.copy()
                self.targets = {target_name: old_targets[target_name]}
                html_content = self._generate_html_template(static_mode=static_mode)
                self.targets = old_targets  # Restore all targets
            else:
                # Generate consolidated report with all targets
                html_content = self._generate_html_template(static_mode=static_mode)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            if not self.watch_mode:  # Only print when not in watch mode to avoid spam
                if RICH_AVAILABLE:
                    console.print(f"[bold green]🕸️  HTML report generated: {output_path}[/bold green]")
                else:
                    print(f"HTML report generated: {output_path}")
        
        self.last_update_time = time.time()
    
    def _get_newest_file_time(self) -> float:
        """Get the modification time of the newest file in results directory"""
        newest_time = 0.0
        
        if not self.results_dir.exists():
            return newest_time
        
        for root, dirs, files in os.walk(self.results_dir):
            for file in files:
                file_path = Path(root) / file
                try:
                    file_time = file_path.stat().st_mtime
                    if file_time > newest_time:
                        newest_time = file_time
                except (OSError, FileNotFoundError):
                    continue
        
        return newest_time
    
    def watch_and_update(self, output_file: str = None, interval: int = 30):
        """Watch for file changes and update report incrementally"""
        self.watch_mode = True
        
        if RICH_AVAILABLE:
            console.print(f"[cyan]🕷️  Starting incremental report generation...[/cyan]")
            console.print(f"[dim]Watching: {self.results_dir}[/dim]")
            console.print(f"[dim]Output: {output_file}[/dim]")
            console.print(f"[dim]Update interval: {interval} seconds[/dim]")
            console.print(f"[dim]Press Ctrl+C to stop[/dim]")
        else:
            print(f"🕷️  Starting incremental report generation...")
            print(f"Watching: {self.results_dir}")
            print(f"Output: {output_file}")
            print(f"Update interval: {interval} seconds")
            print(f"Press Ctrl+C to stop")
        
        # Generate initial report
        self.generate_html_report(output_file, force_update=True)
        
        # Set up signal handler for graceful shutdown
        def signal_handler(signum, frame):
            if RICH_AVAILABLE:
                console.print(f"\n[yellow]🕸️  Stopping incremental updates...[/yellow]")
            else:
                print(f"\n🕸️  Stopping incremental updates...")
            self._stop_watching = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        update_count = 0
        
        try:
            while not self._stop_watching:
                time.sleep(interval)
                
                if self._stop_watching:
                    break
                
                # Check for new files and update if needed
                old_count = sum(len(target.open_ports) for target in self.targets.values())
                
                self.generate_html_report(output_file)
                
                new_count = sum(len(target.open_ports) for target in self.targets.values())
                
                if new_count != old_count:
                    update_count += 1
                    if RICH_AVAILABLE:
                        console.print(f"[green]📡 Update #{update_count}: {new_count} total open ports found[/green]")
                    else:
                        print(f"📡 Update #{update_count}: {new_count} total open ports found")
                
        except KeyboardInterrupt:
            pass
        
        if RICH_AVAILABLE:
            console.print(f"[green]✅ Final report saved: {output_file}[/green]")
        else:
            print(f"✅ Final report saved: {output_file}")
    
    def generate_partial_report(self, output_file: str = None):
        """Generate a report even from incomplete/interrupted scans"""
        
        if RICH_AVAILABLE:
            console.print("[cyan]🕷️  Generating partial report from incomplete scans...[/cyan]")
        else:
            print("🕷️  Generating partial report from incomplete scans...")
        
        # Force consolidation even with incomplete data
        self.consolidate_all_targets(self.specific_target)
        
        if not self.targets:
            if RICH_AVAILABLE:
                console.print("[red]No scan data found to generate partial report[/red]")
            else:
                print("No scan data found to generate partial report")
            return
        
        # Generate HTML with partial scan warning
        html_content = self._generate_html_template(partial=True)
        
        # Auto-determine output file if not specified
        if output_file is None:
            if self.specific_target and self.specific_target in self.targets:
                # Generate target-specific report
                target_dir = self.results_dir / self.specific_target / "report"
                target_dir.mkdir(parents=True, exist_ok=True)
                output_file = target_dir / "ipcrawler_report.html"
            else:
                # Generate consolidated report
                output_file = self.results_dir / "consolidated_report.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if RICH_AVAILABLE:
            console.print(f"[bold yellow]⚠️  Partial report generated: {output_file}[/bold yellow]")
            console.print("[dim]This report may contain incomplete data from interrupted scans[/dim]")
        else:
            print(f"⚠️  Partial report generated: {output_file}")
            print("This report may contain incomplete data from interrupted scans")
    
    def _generate_html_template(self, partial: bool = False, static_mode: bool = False) -> str:
        """Generate the full HTML report template"""
        
        # Calculate summary statistics
        total_ports = sum(len(target.open_ports) for target in self.targets.values())
        total_web_services = sum(len(target.web_services) for target in self.targets.values())
        total_vulnerabilities = sum(len(target.vulnerabilities) for target in self.targets.values())
        
        # Generate report timestamp with status indicator
        report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add live status indicator (only if not in static mode)
        if not static_mode:
            if self.daemon_mode:
                report_time += " | 🔴 LIVE (Auto-updating)"
            elif partial:
                report_time += " | ⚠️ PARTIAL"
        elif partial:
            report_time += " | ⚠️ PARTIAL"
        
        # Auto-refresh meta tag for live modes (only if not in static mode)
        auto_refresh = ''
        if not static_mode:
            if self.daemon_mode:
                auto_refresh = f'<meta http-equiv="refresh" content="{self.update_interval}">'
            elif self.watch_mode:
                auto_refresh = '<meta http-equiv="refresh" content="60">'
        
        # Partial scan warning
        partial_warning = """
        <div class="partial-warning">
            ⚠️ <strong>Partial Report:</strong> This report contains incomplete data from interrupted scans. 
            Some targets may have missing information.
        </div>
        """ if partial else ""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {auto_refresh}
    <title>🕷️ ipcrawler - Network Reconnaissance Report</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {partial_warning}
        <!-- Header -->
        <div class="header">
            <div class="header-content">
                <div class="logo">
                    <span class="spider">🕷️</span>
                    <h1>ipcrawler</h1>
                    <span class="web">🕸️</span>
                </div>
                <p class="subtitle">Network Reconnaissance Report</p>
                <div class="developer-info">
                    <p>
                        🚀 <strong>Developed by:</strong> <a href="https://github.com/neur0map" class="dev-link" target="_blank">neur0map</a> | 
                        📂 <strong>Repository:</strong> <a href="https://github.com/neur0map/ipcrawler" class="repo-link" target="_blank">github.com/neur0map/ipcrawler</a>
                    </p>
                    <p class="star-request">
                        ⭐ <strong>Like this tool?</strong> <a href="https://github.com/neur0map/ipcrawler" class="star-link" target="_blank">Star the project on GitHub!</a> ⭐
                    </p>
                </div>
                <div class="metadata">
                    Generated: {report_time} | Targets: {len(self.targets)} | Open Ports: {total_ports} | Web Services: {total_web_services}
                </div>
            </div>
        </div>

        <!-- Executive Summary -->
        <div class="section" id="summary">
            <h2>🎯 Executive Summary</h2>
            <div class="summary-grid">
                <div class="summary-card critical">
                    <div class="card-header">Critical Findings</div>
                    <div class="card-value">{self._count_critical_findings()}</div>
                </div>
                <div class="summary-card">
                    <div class="card-header">Open Ports</div>
                    <div class="card-value">{total_ports}</div>
                </div>
                <div class="summary-card">
                    <div class="card-header">Web Services</div>
                    <div class="card-value">{total_web_services}</div>
                </div>
                <div class="summary-card">
                    <div class="card-header">Vulnerabilities</div>
                    <div class="card-value">{total_vulnerabilities}</div>
                </div>
            </div>
        </div>

        <!-- Quick Access -->
        <div class="section" id="quick-access">
            <h2>⚡ Quick Access</h2>
            <div class="quick-access-grid">
                {self._generate_quick_access_section()}
            </div>
        </div>

        <!-- Target Details -->
        <div class="section" id="targets">
            <h2>🎯 Target Analysis</h2>
            {self._generate_target_sections()}
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Generated by ipcrawler consolidator | 🕷️ Multi-threaded Network Reconnaissance & Service Crawler 🕸️</p>
        </div>
    </div>

    <script>
        {self._get_javascript()}
    </script>
</body>
</html>"""
        
        return html
    
    def _get_css_styles(self) -> str:
        """Generate CSS styles with spider/web theme"""
        return """
        /* Spider/Web Theme CSS - Dark mode with web patterns */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
            color: #e0e0e0;
            line-height: 1.6;
            min-height: 100vh;
            background-attachment: fixed;
        }

        /* Subtle web pattern overlay */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                radial-gradient(circle at 20% 50%, transparent 20%, rgba(34, 139, 34, 0.02) 21%, rgba(34, 139, 34, 0.02) 30%, transparent 31%),
                radial-gradient(circle at 80% 20%, transparent 20%, rgba(255, 69, 0, 0.02) 21%, rgba(255, 69, 0, 0.02) 30%, transparent 31%),
                radial-gradient(circle at 40% 80%, transparent 20%, rgba(220, 20, 60, 0.02) 21%, rgba(220, 20, 60, 0.02) 30%, transparent 31%);
            pointer-events: none;
            z-index: -1;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Header Styles */
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 20px;
            background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
            border-radius: 15px;
            border: 2px solid #333;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
        }

        .logo {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            margin-bottom: 10px;
        }

        .logo h1 {
            font-size: 3em;
            font-weight: bold;
            background: linear-gradient(45deg, #ff6b35, #f7931e, #228b22, #dc143c);
            background-size: 400% 400%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientShift 6s ease-in-out infinite;
        }

        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }

        .spider, .web {
            font-size: 2.5em;
            animation: pulse 3s ease-in-out infinite;
        }

        .spider { animation-delay: 0s; }
        .web { animation-delay: 1.5s; }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.1); opacity: 1; }
        }

        .subtitle {
            font-size: 1.3em;
            color: #ccc;
            margin-bottom: 15px;
            font-style: italic;
        }

        .developer-info {
            margin: 20px 0;
            padding: 15px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            border: 1px solid #444;
            text-align: center;
        }

        .developer-info p {
            margin: 8px 0;
            font-size: 1em;
            color: #ccc;
        }

        .dev-link, .repo-link {
            color: #ff6b35;
            text-decoration: none;
            font-weight: bold;
            transition: color 0.3s ease;
        }

        .dev-link:hover, .repo-link:hover {
            color: #f7931e;
            text-decoration: underline;
        }

        .star-request {
            margin-top: 12px !important;
            font-size: 1.1em !important;
        }

        .star-link {
            color: #ffd700;
            text-decoration: none;
            font-weight: bold;
            animation: sparkle 2s ease-in-out infinite;
            transition: all 0.3s ease;
        }

        .star-link:hover {
            color: #ffed4e;
            text-decoration: underline;
            transform: scale(1.05);
        }

        @keyframes sparkle {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        .metadata {
            font-size: 1em;
            color: #888;
            padding: 10px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            display: inline-block;
            margin-top: 15px;
        }

        /* Section Styles */
        .section {
            margin-bottom: 40px;
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            border-radius: 12px;
            padding: 30px;
            border: 1px solid #333;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
        }

        .section h2 {
            font-size: 2em;
            margin-bottom: 20px;
            color: #ff6b35;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Summary Grid */
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .summary-card {
            background: linear-gradient(135deg, #2d2d2d 0%, #3d3d3d 100%);
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            border: 2px solid #444;
            transition: all 0.3s ease;
        }

        .summary-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(255, 107, 53, 0.2);
        }

        .summary-card.critical {
            border-color: #dc143c;
            background: linear-gradient(135deg, #3d1a1a 0%, #4d2a2a 100%);
        }

        .card-header {
            font-size: 1.1em;
            color: #ccc;
            margin-bottom: 10px;
        }

        .card-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #ff6b35;
        }

        .critical .card-value {
            color: #dc143c;
        }

        /* Quick Access */
        .quick-access-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .quick-access-item {
            background: linear-gradient(135deg, #2a2a2a 0%, #3a3a3a 100%);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #ff6b35;
        }

        .quick-access-item h4 {
            color: #ff6b35;
            margin-bottom: 10px;
        }

        .quick-access-list {
            list-style: none;
        }

        .quick-access-list li {
            padding: 5px 0;
            color: #ccc;
            border-bottom: 1px dotted #444;
        }

        .quick-access-list li:last-child {
            border-bottom: none;
        }

        /* Target Sections */
        .target-section {
            margin-bottom: 30px;
            background: linear-gradient(135deg, #1e1e1e 0%, #2e2e2e 100%);
            border-radius: 10px;
            padding: 25px;
            border: 1px solid #444;
        }

        .target-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #333;
        }

        .target-title {
            font-size: 1.5em;
            color: #f7931e;
        }

        .target-ip {
            color: #888;
            font-size: 1.1em;
        }

        /* Collapsible Sections */
        .collapsible {
            background: #333;
            color: #fff;
            cursor: pointer;
            padding: 15px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 1.1em;
            border-radius: 8px;
            margin: 10px 0;
            transition: all 0.3s ease;
        }

        .collapsible:hover {
            background: #444;
        }

        .collapsible.active {
            background: #ff6b35;
        }

        .collapsible::after {
            content: '\\002B';
            color: #fff;
            float: right;
            font-weight: bold;
        }

        .collapsible.active::after {
            content: '\\2212';
        }

        .content {
            padding: 0 15px;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 0 0 8px 8px;
        }

        .content.active {
            padding: 15px;
            max-height: 800px;
            overflow-y: auto;
        }

        /* Tables */
        .table-container {
            overflow-x: auto;
            margin: 15px 0;
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.2);
            max-height: 600px;
            overflow-y: auto;
        }

        .table {
            width: 100%;
            border-collapse: collapse;
            background: rgba(0, 0, 0, 0.2);
            min-width: 600px;
        }

        .table th,
        .table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #444;
        }

        .table th {
            background: #333;
            color: #ff6b35;
            font-weight: bold;
        }

        .table tr:hover {
            background: rgba(255, 107, 53, 0.1);
        }

        /* Lists */
        .styled-list {
            list-style: none;
            padding-left: 0;
        }

        .styled-list li {
            padding: 8px 0;
            border-bottom: 1px dotted #444;
            position: relative;
            padding-left: 25px;
        }

        .styled-list li::before {
            content: '🕸️';
            position: absolute;
            left: 0;
            top: 8px;
        }

        .styled-list li:last-child {
            border-bottom: none;
        }

        /* Code blocks */
        .code-block {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #00ff00;
        }

        /* Vulnerability styling */
        .vulnerability {
            background: rgba(220, 20, 60, 0.1);
            border-left: 4px solid #dc143c;
            padding: 10px;
            margin: 5px 0;
            border-radius: 0 5px 5px 0;
        }

        /* URL links */
        .url {
            color: #4da6ff;
            text-decoration: none;
        }

        .url:hover {
            color: #66b3ff;
            text-decoration: underline;
        }

        /* Partial Report Warning */
        .partial-warning {
            background: linear-gradient(135deg, #4d1a1a 0%, #6d2a2a 100%);
            border: 2px solid #dc143c;
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
            color: #ffcccc;
            text-align: center;
            font-size: 1.1em;
            animation: pulse-warning 2s ease-in-out infinite;
        }

        @keyframes pulse-warning {
            0%, 100% { box-shadow: 0 0 5px rgba(220, 20, 60, 0.3); }
            50% { box-shadow: 0 0 20px rgba(220, 20, 60, 0.6); }
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            border-top: 1px solid #333;
            margin-top: 40px;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .logo h1 {
                font-size: 2em;
            }
            
            .summary-grid {
                grid-template-columns: 1fr;
            }
            
            .quick-access-grid {
                grid-template-columns: 1fr;
            }
            
            .target-header {
                flex-direction: column;
                align-items: flex-start;
            }
        }

        /* Scrollbar Styling */
        ::-webkit-scrollbar {
            width: 12px;
        }

        ::-webkit-scrollbar-track {
            background: #1a1a1a;
        }

        ::-webkit-scrollbar-thumb {
            background: #ff6b35;
            border-radius: 6px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #f7931e;
        }
        """
    
    def _get_javascript(self) -> str:
        """Generate JavaScript for interactive features"""
        return """
        // Collapsible sections functionality
        document.addEventListener('DOMContentLoaded', function() {
            var collapsibles = document.getElementsByClassName('collapsible');
            
            for (var i = 0; i < collapsibles.length; i++) {
                collapsibles[i].addEventListener('click', function() {
                    this.classList.toggle('active');
                    var content = this.nextElementSibling;
                    
                    if (content.style.maxHeight) {
                        content.style.maxHeight = null;
                        content.classList.remove('active');
                    } else {
                        content.style.maxHeight = content.scrollHeight + 'px';
                        content.classList.add('active');
                    }
                });
            }
            
            // Auto-expand critical findings
            var criticalSections = document.querySelectorAll('.collapsible[data-critical="true"]');
            criticalSections.forEach(function(section) {
                section.click();
            });
        });

        // Search functionality
        function searchReport(query) {
            var sections = document.querySelectorAll('.target-section');
            var found = false;
            
            sections.forEach(function(section) {
                var text = section.textContent.toLowerCase();
                if (text.includes(query.toLowerCase())) {
                    section.style.display = 'block';
                    found = true;
                } else {
                    section.style.display = query ? 'none' : 'block';
                }
            });
            
            return found;
        }

        // Smooth scrolling for internal links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                
                document.querySelector(this.getAttribute('href')).scrollIntoView({
                    behavior: 'smooth'
                });
            });
        });
        """
    
    def _count_critical_findings(self) -> int:
        """Count critical findings across all targets"""
        critical_count = 0
        
        for target in self.targets.values():
            # Count high-risk ports
            for service in target.open_ports:
                if service.port in [21, 22, 23, 25, 53, 135, 139, 445, 1433, 3389, 5432, 3306]:
                    critical_count += 1
            
            # Count vulnerabilities
            critical_count += len(target.vulnerabilities)
            
            # Count web services with potential issues
            for web in target.web_services:
                if len(web.directories) > 5 or len(web.vhosts) > 0:
                    critical_count += 1
        
        return critical_count
    
    def _generate_quick_access_section(self) -> str:
        """Generate quick access section HTML"""
        # Collect all unique open ports
        all_ports = set()
        all_web_services = []
        all_vhosts = set()
        
        for target in self.targets.values():
            for service in target.open_ports:
                all_ports.add(f"{service.port}/{service.protocol} ({service.service})")
            
            for web in target.web_services:
                all_web_services.append(f"{web.url} - {web.title}" if web.title else web.url)
                all_vhosts.update(web.vhosts)
        
        html = ""
        
        # Open Ports
        if all_ports:
            ports_list = "\n".join([f"<li>{port}</li>" for port in sorted(all_ports)])
            html += f"""
            <div class="quick-access-item">
                <h4>🎯 All Open Ports</h4>
                <ul class="quick-access-list">
                    {ports_list}
                </ul>
            </div>
            """
        
        # Web Services
        if all_web_services:
            web_list = "\n".join([f'<li><a href="{url.split(" - ")[0]}" class="url" target="_blank">{url}</a></li>' 
                                 for url in all_web_services[:10]])  # Limit to first 10
            html += f"""
            <div class="quick-access-item">
                <h4>🌐 Web Services</h4>
                <ul class="quick-access-list">
                    {web_list}
                </ul>
            </div>
            """
        
        # Virtual Hosts
        if all_vhosts:
            vhost_list = "\n".join([f"<li>{vhost}</li>" for vhost in sorted(all_vhosts)[:10]])
            html += f"""
            <div class="quick-access-item">
                <h4>🏠 Virtual Hosts</h4>
                <ul class="quick-access-list">
                    {vhost_list}
                </ul>
            </div>
            """
        
        return html
    
    def _generate_target_sections(self) -> str:
        """Generate HTML for all target sections"""
        html = ""
        
        for target_name, target_data in self.targets.items():
            html += self._generate_single_target_section(target_name, target_data)
        
        return html
    
    def _generate_single_target_section(self, target_name: str, target_data: TargetResults) -> str:
        """Generate HTML for a single target"""
        
        ip_display = f"({target_data.ip_address})" if target_data.ip_address and target_data.ip_address != target_name else ""
        
        html = f"""
        <div class="target-section">
            <div class="target-header">
                <div class="target-title">🎯 {target_name} {ip_display}</div>
                <div class="target-ip">Scanned: {target_data.scan_timestamp}</div>
            </div>
        """
        
        # Open Ports Section
        if target_data.open_ports:
            html += f"""
            <button class="collapsible" data-critical="true">🔍 Open Ports ({len(target_data.open_ports)})</button>
            <div class="content">
                <div class="table-container">
                    <table class="table">
                    <thead>
                        <tr>
                            <th>Port</th>
                            <th>Protocol</th>
                            <th>Service</th>
                            <th>Version</th>
                            <th>State</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for service in target_data.open_ports:
                html += f"""
                        <tr>
                            <td><strong>{service.port}</strong></td>
                            <td>{service.protocol.upper()}</td>
                            <td>{service.service}</td>
                            <td>{service.version[:50]}{"..." if len(service.version) > 50 else ""}</td>
                            <td><span style="color: #228b22;">{service.state}</span></td>
                        </tr>
                """
            
            html += """
                    </tbody>
                    </table>
                </div>
            </div>
            """
        
        # Web Services Section
        if target_data.web_services:
            html += f"""
            <button class="collapsible" data-critical="true">🌐 Web Services ({len(target_data.web_services)})</button>
            <div class="content">
            """
            
            for web in target_data.web_services:
                html += f"""
                <div style="margin-bottom: 20px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                    <h4><a href="{web.url}" class="url" target="_blank">{web.url}</a></h4>
                    <p><strong>Title:</strong> {web.title or 'N/A'}</p>
                    <p><strong>Server:</strong> {web.server or 'N/A'}</p>
                    <p><strong>Status:</strong> {web.status_code if web.status_code else 'N/A'}</p>
                """
                
                if web.technologies:
                    tech_list = "</li><li>".join(web.technologies)
                    html += f"""
                    <p><strong>Technologies:</strong></p>
                    <ul class="styled-list">
                        <li>{tech_list}</li>
                    </ul>
                    """
                
                if web.directories:
                    dir_list = "</li><li>".join(web.directories[:10])  # Limit to first 10
                    html += f"""
                    <p><strong>Directories Found:</strong></p>
                    <ul class="styled-list">
                        <li>{dir_list}</li>
                    </ul>
                    """
                
                if web.vhosts:
                    vhost_list = "</li><li>".join(web.vhosts)
                    html += f"""
                    <p><strong>Virtual Hosts:</strong></p>
                    <ul class="styled-list">
                        <li>{vhost_list}</li>
                    </ul>
                    """
                
                if web.vulnerabilities:
                    html += f"""
                    <p><strong>Vulnerabilities:</strong></p>
                    """
                    for vuln in web.vulnerabilities:
                        html += f'<div class="vulnerability">{vuln}</div>'
                
                html += "</div>"
            
            html += "</div>"
        
        # Vulnerabilities Section
        if target_data.vulnerabilities:
            html += f"""
            <button class="collapsible" data-critical="true">⚠️ Vulnerabilities ({len(target_data.vulnerabilities)})</button>
            <div class="content">
            """
            for vuln in target_data.vulnerabilities:
                html += f'<div class="vulnerability">{vuln}</div>'
            html += "</div>"
        
        # Pattern Matches Section
        if target_data.patterns:
            html += f"""
            <button class="collapsible">🕸️ Pattern Matches ({len(target_data.patterns)})</button>
            <div class="content">
                <ul class="styled-list">
            """
            for pattern in target_data.patterns[:20]:  # Limit to first 20
                html += f"<li>{pattern}</li>"
            html += """
                </ul>
            </div>
            """
        
        # Manual Commands Section
        if target_data.manual_commands:
            html += f"""
            <button class="collapsible">⚙️ Manual Commands ({len(target_data.manual_commands)})</button>
            <div class="content">
            """
            for cmd in target_data.manual_commands[:10]:  # Limit to first 10
                html += f'<div class="code-block">{cmd}</div>'
            html += "</div>"
        
        html += "</div>"  # Close target-section
        
        return html


def main():
    """Main function to run the consolidator"""
    parser = argparse.ArgumentParser(
        description="ipcrawler Results Consolidator - Generate comprehensive HTML reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 consolidator.py                              # Generate reports for all targets
  python3 consolidator.py -d                           # Start daemon mode (live monitoring)
  python3 consolidator.py -w                           # Watch mode (live updates)
  python3 consolidator.py -p                           # Partial report from interrupted scans
  python3 consolidator.py -t hackerhub.me              # Report for specific target only
  python3 consolidator.py -w -i 15                     # Watch mode with 15s updates
  python3 consolidator.py -r /path/results             # Custom results directory
  python3 consolidator.py -o custom.html               # Custom output filename
  
Modes:
  • One-time: Generate static report from completed scans
  • Watch mode (-w): Continuously update report as scans progress (perfect for long scans)
  • Partial mode (-p): Generate report from interrupted/incomplete scans

Spider/Web themed report with intelligent prioritization of:
- Open ports and services (most critical first)
- Web services with vhosts and directories
- Vulnerabilities and pattern matches
- Manual commands for further testing
        """
    )
    
    parser.add_argument(
        '-r', '--results-dir',
        default='results',
        help='Path to ipcrawler results directory (default: results)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output HTML filename (default: auto-placed in target report directories)'
    )
    
    parser.add_argument(
        '-w', '--watch',
        action='store_true',
        help='Watch mode: continuously update report as scans progress'
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=30,
        help='Update interval in seconds for watch mode (default: 30)'
    )
    
    parser.add_argument(
        '-p', '--partial',
        action='store_true',
        help='Generate partial report from incomplete/interrupted scans'
    )
    
    parser.add_argument(
        '--no-auto-partial',
        action='store_true',
        help='Disable automatic partial report generation for interrupted scans'
    )
    
    parser.add_argument(
        '-d', '--daemon',
        action='store_true',
        help='Run in daemon mode: continuously monitor and generate live reports'
    )
    
    parser.add_argument(
        '--daemon-interval',
        type=int,
        default=5,
        help='Update interval in seconds for daemon mode (default: 5)'
    )
    
    parser.add_argument(
        '-t', '--target',
        type=str,
        help='Generate report for specific target only (e.g., hackerhub.me)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='ipcrawler-consolidator 1.1.0'
    )
    
    args = parser.parse_args()
    
    # Display banner
    if RICH_AVAILABLE:
        console.print()
        console.print("🕷️" + "=" * 70 + "🕸️", style="cyan")
        console.print()
        console.print(Panel(
            Text.assemble(
                ("🕷️  ", "cyan"), ("ipcrawler", "bold cyan"), (" Results Consolidator  ", "white"), ("🕸️", "cyan")
            ),
            box=box.DOUBLE,
            border_style="cyan",
            padding=(1, 2)
        ))
        console.print()
        console.print("=" * 75, style="cyan")
        console.print()
    else:
        print("\n🕷️" + "=" * 70 + "🕸️")
        print("ipcrawler Results Consolidator")
        print("=" * 75 + "\n")
    
    # Initialize consolidator
    consolidator = IPCrawlerConsolidator(args.results_dir)
    
    # Configure auto-partial reports
    if args.no_auto_partial:
        consolidator.auto_partial_reports = False
    
    # Set specific target if provided
    if args.target:
        consolidator.specific_target = args.target
    
    # Handle different modes
    if args.daemon:
        # Daemon mode: real-time monitoring and live reports
        try:
            consolidator.start_daemon_mode(args.daemon_interval)
        except KeyboardInterrupt:
            if RICH_AVAILABLE:
                console.print("\n[yellow]🕸️  Daemon mode stopped by user[/yellow]")
            else:
                print("\n🕸️  Daemon mode stopped by user")
    elif args.watch:
        # Watch mode: continuously update report
        try:
            consolidator.watch_and_update(args.output)
        except KeyboardInterrupt:
            if RICH_AVAILABLE:
                console.print("\n[yellow]🕸️  Watch mode stopped by user[/yellow]")
            else:
                print("\n🕸️  Watch mode stopped by user")
    elif args.partial:
        # Partial mode: generate report from incomplete scans
        consolidator.generate_partial_report(args.output)
    else:
        # Standard mode: one-time report generation
        
        # First check for interrupted scans and auto-generate partial reports
        if consolidator.auto_partial_reports:
            interrupted_targets = consolidator.detect_interrupted_scans()
            if interrupted_targets:
                if RICH_AVAILABLE:
                    console.print(f"[yellow]🕸️  Detected {len(interrupted_targets)} interrupted scan(s): {', '.join(interrupted_targets)}[/yellow]")
                    console.print(f"[cyan]🕷️  Auto-generating partial reports...[/cyan]")
                else:
                    print(f"🕸️  Detected {len(interrupted_targets)} interrupted scan(s): {', '.join(interrupted_targets)}")
                    print(f"🕷️  Auto-generating partial reports...")
                
                # Generate reports for interrupted scans
                for target in interrupted_targets:
                    consolidator.specific_target = target
                    consolidator.generate_partial_report(None)
                
                # Reset specific target for main report generation
                consolidator.specific_target = args.target
        
        # Generate main report
        consolidator.generate_html_report(args.output)
        
        if RICH_AVAILABLE:
            console.print()
            console.print(f"[bold green]✅ Report successfully generated: {args.output}[/bold green]")
            console.print("[dim]Open the HTML file in your browser to view the interactive report[/dim]")
            console.print()
        else:
            print(f"\n✅ Report successfully generated: {args.output}")
            print("Open the HTML file in your browser to view the interactive report\n")


if __name__ == "__main__":
    main()