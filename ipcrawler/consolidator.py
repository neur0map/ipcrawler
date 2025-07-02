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
try:
    import defusedxml.ElementTree as ET
except ImportError:
    # Fallback to standard library with warning
    import xml.etree.ElementTree as ET
    import warnings
    warnings.warn("defusedxml not available, using potentially unsafe xml.etree.ElementTree. Install defusedxml for security.", UserWarning)
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
    
    # Enhanced fields for comprehensive service data
    enumeration_data: Dict[str, Any] = field(default_factory=dict)  # Plugin-specific findings
    vulnerabilities: List[str] = field(default_factory=list)  # Service-specific vulns
    access_info: Dict[str, Any] = field(default_factory=dict)  # Auth/access details
    config_info: Dict[str, Any] = field(default_factory=dict)  # Configuration details

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
    hostnames: List[str] = field(default_factory=list)
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
        
        # Check if file exists and is readable
        if not os.path.exists(xml_path):
            if RICH_AVAILABLE:
                console.print(f"[yellow]Warning: XML file {xml_path} does not exist[/yellow]")
            return services
        
        # Check if file is empty
        if os.path.getsize(xml_path) == 0:
            if RICH_AVAILABLE:
                console.print(f"[yellow]Warning: XML file {xml_path} is empty, skipping...[/yellow]")
            return services
        
        try:
            # Try to parse the XML file
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Validate that this is an nmap XML file
            if root.tag != 'nmaprun':
                if RICH_AVAILABLE:
                    console.print(f"[yellow]Warning: {xml_path} does not appear to be a valid nmap XML file[/yellow]")
                return services
            
            for host in root.findall('host'):
                for port in host.findall('.//port'):
                    port_id = port.get('portid')
                    protocol = port.get('protocol')
                    
                    if port_id is None or protocol is None:
                        continue
                    
                    try:
                        port_num = int(port_id)
                    except ValueError:
                        continue
                    
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
                        
        except ET.ParseError as e:
            # Handle XML parsing errors more gracefully
            if RICH_AVAILABLE:
                console.print(f"[yellow]Warning: XML file {xml_path} appears to be corrupted or incomplete (Parse error: {e}). Trying text fallback...[/yellow]")
                console.print(f"[dim]   ↳ This usually happens when scans are interrupted. Report generation will continue with available data.[/dim]")
            else:
                print(f"Warning: XML file {xml_path} appears to be corrupted or incomplete (Parse error: {e}). Trying text fallback...")
                print(f"   ↳ This usually happens when scans are interrupted. Report generation will continue with available data.")
            
            # Try to read as text and extract basic port information
            try:
                with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Look for port entries in the XML text even if it's malformed
                port_matches = re.findall(r'<port protocol="(tcp|udp)" portid="(\d+)".*?<state state="(open|closed|filtered)".*?(?:<service name="([^"]*)".*?/>)?', content, re.DOTALL)
                for protocol, port_id, state, service_name in port_matches:
                    if state == 'open':
                        services.append(ServiceInfo(
                            port=int(port_id),
                            protocol=protocol,
                            service=service_name or 'unknown',
                            state=state,
                            version='',
                            banner=''
                        ))
            except Exception as text_e:
                if RICH_AVAILABLE:
                    console.print(f"[red]Error: Could not parse XML file {xml_path} as text either: {text_e}[/red]")
                else:
                    print(f"Error: Could not parse XML file {xml_path} as text either: {text_e}")
                    
        except FileNotFoundError:
            if RICH_AVAILABLE:
                console.print(f"[yellow]Warning: XML file {xml_path} not found[/yellow]")
            else:
                print(f"Warning: XML file {xml_path} not found")
                
        except PermissionError:
            if RICH_AVAILABLE:
                console.print(f"[red]Error: Permission denied reading XML file {xml_path}[/red]")
            else:
                print(f"Error: Permission denied reading XML file {xml_path}")
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Unexpected error parsing XML {xml_path}: {e}[/red]")
            else:
                print(f"Unexpected error parsing XML {xml_path}: {e}")
        
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
        """Parse virtual host enumeration results from ffuf CSV output"""
        vhosts = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check if this is CSV format (ffuf output)
            if 'url,redirectlocation,position,status_code,content_length,content_words,content_lines,content_type,duration' in content:
                # Parse CSV format
                lines = content.strip().split('\n')
                for line_num, line in enumerate(lines):
                    line = line.strip()
                    if not line or line.startswith('url,'):  # Skip header and empty lines
                        continue
                    
                    # CSV format: url,redirectlocation,position,status_code,content_length,content_words,content_lines,content_type,duration
                    try:
                        parts = line.split(',')
                        if len(parts) >= 4:
                            url = parts[0]
                            status_code = parts[3]
                            
                            # Only include successful responses (not 404, 500, etc.)
                            if status_code in ['200', '301', '302', '303', '403', '401']:
                                # Extract hostname from URL
                                import urllib.parse
                                parsed_url = urllib.parse.urlparse(url if url.startswith('http') else f'http://{url}')
                                hostname = parsed_url.hostname
                                
                                if hostname and hostname not in vhosts:
                                    # Extract just the subdomain part (before the main domain)
                                    if '.' in hostname:
                                        # For test.example.com, we want "test"
                                        # For admin.dev.example.com, we want "admin.dev"
                                        parts_hostname = hostname.split('.')
                                        if len(parts_hostname) > 2:
                                            # Keep everything except the last 2 parts (domain.tld)
                                            subdomain = '.'.join(parts_hostname[:-2])
                                            if subdomain and subdomain not in vhosts:
                                                vhosts.append(subdomain)
                                        else:
                                            # It's just domain.tld, still add it
                                            if hostname not in vhosts:
                                                vhosts.append(hostname)
                    except (IndexError, ValueError) as e:
                        continue  # Skip malformed lines
            # Check if this file just contains a wordlist (old problematic files)
            elif content.count('\n') > 100 and not any(char in content[:1000] for char in [',', 'http', '://', 'Status:']):
                # This looks like a raw wordlist file (all failed attempts), skip it entirely
                if RICH_AVAILABLE:
                    console.print(f"[yellow]Skipping wordlist file (no discoveries): {os.path.basename(file_path)}[/yellow]")
                else:
                    print(f"Skipping wordlist file (no discoveries): {os.path.basename(file_path)}")
                return []
            else:
                # Fallback: parse as regular text output or simple subdomain lists
                for line in content.split('\n'):
                    line = line.strip()
                    
                    # Skip commented lines (starting with #)
                    if line.startswith('#') or not line:
                        continue
                    
                    # Check if this line contains status codes (typical ffuf/tool output)
                    if re.search(r'\b(200|301|302|403)\b', line) and not re.search(r'\b(404|500|502|503)\b', line):
                        # Extract hostname from the line
                        host_match = re.search(r'([a-zA-Z0-9.-]+(?:\.[a-zA-Z0-9.-]+)*)', line)
                        if host_match:
                            hostname = host_match.group(1)
                            # Only add if it looks like a valid hostname/subdomain
                            if '.' in hostname and len(hostname) > 2 and hostname not in vhosts:
                                vhosts.append(hostname)
                    # Check if this line looks like a direct subdomain (e.g., "test.example.com")
                    elif re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z0-9.-]+$', line) and len(line.split('.')) >= 2:
                        # This looks like a discovered virtual host/subdomain
                        hostname = line
                        if hostname not in vhosts and len(hostname) > 2:
                            vhosts.append(hostname)
                            
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
    
    def _is_valid_manual_command(self, line: str) -> bool:
        """Check if a line is a valid manual command"""
        if not line or len(line) < 10:
            return False
            
        # Skip comments and empty lines
        if line.startswith('#') or line.startswith('//'):
            return False
            
        # Skip section headers and decorative text
        decorative_patterns = [
            r'^[🎯🔧⚙️🌐]+\s*\w+\s*on\s+tcp/',  # "🎯 ssh on tcp/22"
            r'^[🎯🔧⚙️🌐]+\s*\([^)]+\)\s*',      # "🔧 (feroxbuster) Multi-threaded..."
            r'^[🎯🔧⚙️🌐]+\s*[A-Z][^:]*:$',      # "🔧 Bruteforce logins:"
            r'^\s*[-=_]{3,}\s*$',                 # Separator lines
            r'^\s*$',                             # Empty lines
        ]
        
        for pattern in decorative_patterns:
            if re.match(pattern, line):
                return False
        
        # Must contain actual command-like content
        command_indicators = [
            # Common penetration testing tools
            r'\b(nmap|hydra|medusa|feroxbuster|gobuster|wpscan|nikto|sqlmap|dirb|ffuf)\b',
            # Common shell commands with arguments
            r'\b(curl|wget|ssh|ftp|telnet|nc|netcat)\s+',
            # Tools with specific flags
            r'\s-[a-zA-Z]\b',  # Command line flags
            r'\s--[a-zA-Z]',   # Long flags
            # File paths and URLs
            r'https?://',
            r'/[a-zA-Z0-9].*\.(txt|php|html|asp|jsp)',
        ]
        
        for pattern in command_indicators:
            if re.search(pattern, line, re.IGNORECASE):
                return True
                
        return False
    
    # === NEW PARSING METHODS FOR ALL SERVICE TYPES ===
    
    def parse_ssh_scan(self, file_path: str) -> Dict[str, Any]:
        """Parse SSH enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract SSH version and algorithms
                if 'SSH-' in content:
                    ssh_match = re.search(r'SSH-(\d+\.\d+)-(.+)', content)
                    if ssh_match:
                        data['version'] = ssh_match.group(0)
                        data['protocol_version'] = ssh_match.group(1)
                        data['software'] = ssh_match.group(2)
                
                # Extract host keys - fix regex to be more specific
                # Look for nmap ssh-hostkey script output specifically
                if '| ssh-hostkey:' in content:
                    # Parse nmap ssh-hostkey script output
                    hostkey_section = re.search(r'\| ssh-hostkey:(.*?)(?=\||$)', content, re.DOTALL)
                    if hostkey_section:
                        # More specific pattern: require longer hex strings and proper format
                        keys = re.findall(r'(\w+)\s+(\d+)\s+([a-fA-F0-9:]{47,})', hostkey_section.group(1))
                        if keys:
                            data['host_keys'] = [{'type': k[0], 'bits': k[1], 'fingerprint': k[2]} for k in keys]
                else:
                    # Fallback: more specific regex requiring longer hex strings
                    host_keys = re.findall(r'(\w+)\s+(\d+)\s+([a-fA-F0-9:]{47,})', content)
                    if host_keys:
                        data['host_keys'] = [{'type': hk[0], 'bits': hk[1], 'fingerprint': hk[2]} for hk in host_keys]
                
                # Extract supported algorithms
                if 'kex algorithms' in content.lower():
                    data['kex_algorithms'] = re.findall(r'kex algorithms:\s*(.+)', content, re.IGNORECASE)
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing SSH scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_smb_scan(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Parse SMB/NetBIOS enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                if 'smbmap' in filename:
                    # Parse smbmap share enumeration
                    shares = re.findall(r'(\w+)\s+(\w+)\s+(.+)', content)
                    if shares:
                        data['shares'] = [{'name': s[0], 'permissions': s[1], 'comment': s[2]} for s in shares]
                
                elif 'enum4linux' in filename:
                    # Parse enum4linux output
                    if 'Domain Name:' in content:
                        domain_match = re.search(r'Domain Name:\s*(.+)', content)
                        if domain_match:
                            data['domain_name'] = domain_match.group(1).strip()
                    
                    # Extract users
                    users = re.findall(r'user:\[(.+?)\]', content, re.IGNORECASE)
                    if users:
                        data['users'] = list(set(users))  # Deduplicate
                
                elif 'smbclient' in filename:
                    # Parse smbclient listings
                    files = re.findall(r'(\S+)\s+[DAH]?\s+\d+', content)
                    if files:
                        data['files'] = files[:20]  # Limit to first 20
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing SMB scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_snmp_scan(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Parse SNMP enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # System information
                if 'system_info' in filename or 'system' in filename:
                    sys_info = {}
                    if 'sysName' in content:
                        sys_match = re.search(r'sysName\.0\s*=\s*(.+)', content)
                        if sys_match:
                            sys_info['hostname'] = sys_match.group(1).strip()
                    
                    if 'sysDescr' in content:
                        desc_match = re.search(r'sysDescr\.0\s*=\s*(.+)', content)
                        if desc_match:
                            sys_info['description'] = desc_match.group(1).strip()
                    
                    data['system_info'] = sys_info
                
                # User accounts
                elif 'user' in filename:
                    users = re.findall(r'hrSWRunName\.(\d+)\s*=\s*(.+)', content)
                    if users:
                        data['running_processes'] = [{'pid': u[0], 'name': u[1]} for u in users[:10]]
                
                # Network interfaces
                elif 'interface' in filename:
                    interfaces = re.findall(r'ifDescr\.(\d+)\s*=\s*(.+)', content)
                    if interfaces:
                        data['interfaces'] = [{'index': i[0], 'description': i[1]} for i in interfaces]
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing SNMP scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_database_scan(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Parse database enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                if 'redis' in filename:
                    # Parse Redis INFO output
                    if 'redis_version' in content:
                        version_match = re.search(r'redis_version:(.+)', content)
                        if version_match:
                            data['version'] = version_match.group(1).strip()
                    
                    # Redis configuration
                    config_items = re.findall(r'(\w+):(.+)', content)
                    if config_items:
                        data['config'] = {item[0]: item[1].strip() for item in config_items[:20]}
                
                elif 'mysql' in filename:
                    # Parse MySQL version and info
                    if 'Server version:' in content:
                        version_match = re.search(r'Server version:\s*(.+)', content)
                        if version_match:
                            data['version'] = version_match.group(1).strip()
                    
                    # Extract databases
                    databases = re.findall(r'Database:\s*(.+)', content)
                    if databases:
                        data['databases'] = databases
                
                # Add more database types as needed
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing database scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_ftp_scan(self, file_path: str) -> Dict[str, Any]:
        """Parse FTP enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for anonymous access
                if 'anonymous' in content.lower():
                    data['anonymous_access'] = 'allowed' in content.lower()
                
                # Extract banner
                banner_match = re.search(r'220[\s-](.+)', content)
                if banner_match:
                    data['banner'] = banner_match.group(1).strip()
                
                # File listings
                files = re.findall(r'-rw.+\s+(.+)', content)
                if files:
                    data['files'] = files[:10]  # Limit to first 10
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing FTP scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_dns_scan(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Parse DNS enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract DNS records
                if 'A record' in content or 'AAAA record' in content:
                    a_records = re.findall(r'(\S+)\s+IN\s+A\s+(\S+)', content)
                    if a_records:
                        data['a_records'] = [{'hostname': r[0], 'ip': r[1]} for r in a_records]
                
                # Extract subdomains
                subdomains = re.findall(r'(\S+\.\S+)', content)
                if subdomains:
                    # Filter valid subdomains and limit
                    valid_subs = [s for s in subdomains if '.' in s and len(s) < 100][:20]
                    data['subdomains'] = list(set(valid_subs))
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing DNS scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_ldap_scan(self, file_path: str) -> Dict[str, Any]:
        """Parse LDAP enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract base DN
                base_dn_match = re.search(r'baseDN:\s*(.+)', content)
                if base_dn_match:
                    data['base_dn'] = base_dn_match.group(1).strip()
                
                # Extract domain components
                dc_matches = re.findall(r'dc=([^,\s]+)', content)
                if dc_matches:
                    data['domain_components'] = list(set(dc_matches))
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing LDAP scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_mail_scan(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Parse mail service enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract service banner
                if '220' in content:
                    banner_match = re.search(r'220\s+(.+)', content)
                    if banner_match:
                        data['banner'] = banner_match.group(1).strip()
                
                # SMTP capabilities
                if 'smtp' in filename and 'EHLO' in content:
                    capabilities = re.findall(r'250[\s-](\w+)', content)
                    if capabilities:
                        data['capabilities'] = list(set(capabilities))
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing mail scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_spring_scan(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Parse Spring Boot application enumeration results"""
        data = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Spring Boot actuator endpoints
                if 'actuator' in filename:
                    endpoints = re.findall(r'/actuator/(\w+)', content)
                    if endpoints:
                        data['endpoints'] = list(set(endpoints))
                
                # Application information
                if 'Eureka' in content:
                    data['type'] = 'Netflix Eureka Server'
                elif 'Spring Boot' in content:
                    data['type'] = 'Spring Boot Application'
                
                # Extract configuration
                if 'application.properties' in content or 'application.yml' in content:
                    data['config_found'] = True
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing Spring scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_ssl_scan(self, file_path: str) -> Dict[str, Any]:
        """Parse SSL scan results"""
        data = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract SSL version and protocols
            if 'ssl' in content.lower() or 'tls' in content.lower():
                # Look for supported protocols
                protocols = re.findall(r'(SSLv[0-9\.]+|TLSv[0-9\.]+)', content, re.IGNORECASE)
                if protocols:
                    data['supported_protocols'] = list(set(protocols))
                
                # Look for cipher suites
                ciphers = re.findall(r'cipher[s]?[:\s]+([A-Z0-9_-]+)', content, re.IGNORECASE)
                if ciphers:
                    data['cipher_suites'] = list(set(ciphers))
                
                # Look for certificate information
                cert_info = {}
                subject_match = re.search(r'subject[:\s]+(.+)', content, re.IGNORECASE)
                if subject_match:
                    cert_info['subject'] = subject_match.group(1).strip()
                
                issuer_match = re.search(r'issuer[:\s]+(.+)', content, re.IGNORECASE)
                if issuer_match:
                    cert_info['issuer'] = issuer_match.group(1).strip()
                
                # Look for expiration dates
                expires_match = re.search(r'not.*after[:\s]+(.+)', content, re.IGNORECASE)
                if expires_match:
                    cert_info['expires'] = expires_match.group(1).strip()
                
                if cert_info:
                    data['certificate'] = cert_info
                
                # Check for weak ciphers or vulnerabilities
                vulnerabilities = []
                weak_indicators = ['weak', 'insecure', 'deprecated', 'vulnerable', 'NULL', 'MD5', 'RC4']
                for indicator in weak_indicators:
                    if indicator.lower() in content.lower():
                        vulnerabilities.append(f"SSL/TLS {indicator} detected")
                
                if vulnerabilities:
                    data['ssl_vulnerabilities'] = vulnerabilities
        
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing SSL scan {file_path}: {e}[/red]")
        
        return data
    
    def parse_nmap_script_output(self, file_path: str) -> Dict[str, Any]:
        """Parse generic nmap script output for any service"""
        data = {}
        vulnerabilities = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract vulnerabilities
                vuln_patterns = [
                    r'VULNERABLE',
                    r'CVE-\d{4}-\d+',
                    r'POTENTIAL SECURITY RISK',
                    r'weak cipher',
                    r'anonymous login'
                ]
                
                for pattern in vuln_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    vulnerabilities.extend(matches)
                
                if vulnerabilities:
                    data['vulnerabilities'] = list(set(vulnerabilities))
                
                # Extract script results
                script_results = re.findall(r'\|\s+(.+)', content)
                if script_results:
                    data['script_output'] = script_results[:10]  # Limit output
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]Error parsing nmap script output {file_path}: {e}[/red]")
        
        return data

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
        xml_parsed_successfully = False
        
        if xml_dir.exists():
            for xml_file in sorted(xml_dir.glob("*nmap*.xml")):
                services = self.parser.parse_nmap_xml(str(xml_file))
                if services:  # Only extend if we got actual services
                    results.open_ports.extend(services)
                    xml_parsed_successfully = True
        
        # If no XML results or XML parsing failed, parse text files
        if not results.open_ports:
            for nmap_file in sorted(scan_dir.glob("*nmap*.txt")):
                services = self.parser.parse_nmap_text(str(nmap_file))
                results.open_ports.extend(services)
                
            # If text files also don't exist, try to find any scan results
            if not results.open_ports and xml_dir.exists():
                if RICH_AVAILABLE:
                    console.print(f"[yellow]📡 No port data found for {target}. Scan may be incomplete or failed.[/yellow]")
                else:
                    print(f"No port data found for {target}. Scan may be incomplete or failed.")
        
        # Remove duplicates and sort by port
        unique_ports = {}
        for service in results.open_ports:
            key = (service.port, service.protocol)
            if key not in unique_ports or len(service.version) > len(unique_ports[key].version):
                unique_ports[key] = service
        results.open_ports = sorted(unique_ports.values(), key=lambda s: s.port)
        
        # Parse service-specific results
        for port_dir in sorted(scan_dir.glob("tcp*")):
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
        
        # Debug logging for HTB troubleshooting
        files_in_dir = sorted(list(port_dir.glob("*")))
        file_count = len([f for f in files_in_dir if f.is_file()])
        
        if RICH_AVAILABLE:
            console.print(f"[dim]🔍 Parsing port {port_num}: {file_count} files found[/dim]")
        
        # Find corresponding service info
        target_service = None
        web_service = None
        
        for service in results.open_ports:
            if service.port == port_num:
                target_service = service
                # Create web service if applicable
                if service.service in ['http', 'https', 'http-alt', 'http-proxy']:
                    scheme = 'https' if service.service == 'https' or 'ssl' in service.service.lower() else 'http'
                    url = f"{scheme}://{results.target}:{port_num}"
                    web_service = WebInfo(url=url)
                    results.web_services.append(web_service)
                break
        
        # If no service found in open_ports, create a basic one
        if not target_service:
            target_service = ServiceInfo(port=port_num, protocol='tcp', service='unknown')
            results.open_ports.append(target_service)
        
        # Parse all files in the service directory
        files_processed = 0
        files_skipped = 0
        
        for file_path in files_in_dir:
            if file_path.is_file():
                filename = file_path.name.lower()
                file_size = file_path.stat().st_size
                
                # Skip empty files with warning
                if file_size == 0:
                    files_skipped += 1
                    if RICH_AVAILABLE:
                        console.print(f"[yellow]⚠️ Skipping empty file: {filename}[/yellow]")
                    continue
                
                files_processed += 1
                if RICH_AVAILABLE:
                    console.print(f"[dim]📄 Processing: {filename} ({file_size} bytes)[/dim]")
                
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
                
                # === NON-WEB SERVICE PARSING (NEW) ===
                
                # SSH enumeration
                elif 'ssh' in filename:
                    ssh_data = self.parser.parse_ssh_scan(str(file_path))
                    if target_service and ssh_data:
                        target_service.enumeration_data.update(ssh_data)
                        if 'host_keys' in ssh_data:
                            target_service.config_info['host_keys'] = ssh_data['host_keys']
                
                # SMB/NetBIOS enumeration  
                elif any(tool in filename for tool in ['smbmap', 'smbclient', 'enum4linux', 'nbtscan']):
                    smb_data = self.parser.parse_smb_scan(str(file_path), filename)
                    if target_service and smb_data:
                        target_service.enumeration_data.update(smb_data)
                        if 'shares' in smb_data:
                            target_service.access_info['shares'] = smb_data['shares']
                
                # SNMP enumeration
                elif 'snmp' in filename:
                    snmp_data = self.parser.parse_snmp_scan(str(file_path), filename)
                    if target_service and snmp_data:
                        target_service.enumeration_data.update(snmp_data)
                        if 'system_info' in snmp_data:
                            target_service.config_info.update(snmp_data['system_info'])
                
                # Database services (Redis, MySQL, etc.)
                elif any(db in filename for db in ['redis', 'mysql', 'mssql', 'oracle', 'mongo', 'cassandra']):
                    db_data = self.parser.parse_database_scan(str(file_path), filename)
                    if target_service and db_data:
                        target_service.enumeration_data.update(db_data)
                        if 'config' in db_data:
                            target_service.config_info.update(db_data['config'])
                
                # FTP enumeration
                elif 'ftp' in filename:
                    ftp_data = self.parser.parse_ftp_scan(str(file_path))
                    if target_service and ftp_data:
                        target_service.enumeration_data.update(ftp_data)
                        if 'anonymous_access' in ftp_data:
                            target_service.access_info['anonymous'] = ftp_data['anonymous_access']
                
                # DNS enumeration
                elif 'dns' in filename or 'dig' in filename or 'nslookup' in filename:
                    dns_data = self.parser.parse_dns_scan(str(file_path), filename)
                    if target_service and dns_data:
                        target_service.enumeration_data.update(dns_data)
                
                # LDAP enumeration
                elif 'ldap' in filename:
                    ldap_data = self.parser.parse_ldap_scan(str(file_path))
                    if target_service and ldap_data:
                        target_service.enumeration_data.update(ldap_data)
                        if 'base_dn' in ldap_data:
                            target_service.config_info['base_dn'] = ldap_data['base_dn']
                
                # Mail services (SMTP, IMAP, POP3)
                elif any(mail in filename for mail in ['smtp', 'imap', 'pop3']):
                    mail_data = self.parser.parse_mail_scan(str(file_path), filename)
                    if target_service and mail_data:
                        target_service.enumeration_data.update(mail_data)
                
                # Spring Boot / Java applications
                elif 'spring' in filename or 'actuator' in filename:
                    spring_data = self.parser.parse_spring_scan(str(file_path), filename)
                    if target_service and spring_data:
                        target_service.enumeration_data.update(spring_data)
                        if 'endpoints' in spring_data:
                            target_service.access_info['endpoints'] = spring_data['endpoints']
                
                # SSL scan results  
                elif 'sslscan' in filename:
                    ssl_data = self.parser.parse_ssl_scan(str(file_path))
                    if target_service and ssl_data:
                        target_service.enumeration_data.update(ssl_data)
                        if 'certificates' in ssl_data:
                            target_service.config_info['ssl_certificates'] = ssl_data['certificates']
                
                # Robots.txt and security files
                elif 'robots' in filename or 'security' in filename:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().strip()
                        if content and target_service:
                            if 'robots' in filename:
                                target_service.enumeration_data['robots_txt'] = content
                            elif 'security' in filename:
                                target_service.enumeration_data['security_txt'] = content
                    except Exception:
                        pass
                
                # Generic nmap script results for any service
                elif 'nmap' in filename and filename.endswith('.txt'):
                    nmap_data = self.parser.parse_nmap_script_output(str(file_path))
                    if target_service and nmap_data:
                        target_service.enumeration_data.update(nmap_data)
                        # Extract vulnerabilities
                        if 'vulnerabilities' in nmap_data:
                            target_service.vulnerabilities.extend(nmap_data['vulnerabilities'])
                
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
                
                # Catch-all for unrecognized but potentially useful files
                else:
                    # Log unprocessed files for debugging
                    if RICH_AVAILABLE:
                        console.print(f"[dim]🔍 Unprocessed file: {filename} ({file_size} bytes)[/dim]")
                    
                    # Try generic text extraction for any file with useful keywords
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        # Look for common security indicators
                        security_indicators = ['CVE-', 'vulnerable', 'EXPLOIT', 'password', 'admin', 'root', 'shell', 'exposed', 'misconfigured']
                        findings = []
                        for indicator in security_indicators:
                            if indicator.lower() in content.lower():
                                findings.append(f"Found '{indicator}' in {filename}")
                        
                        if findings and target_service:
                            if 'generic_findings' not in target_service.enumeration_data:
                                target_service.enumeration_data['generic_findings'] = []
                            target_service.enumeration_data['generic_findings'].extend(findings)
                            if RICH_AVAILABLE:
                                console.print(f"[cyan]🔍 Generic scan findings in {filename}: {len(findings)} indicators[/cyan]")
                                
                    except Exception:
                        pass  # Ignore parsing errors for unknown files
        
        # Debug summary for HTB troubleshooting
        if RICH_AVAILABLE and files_skipped > 0:
            console.print(f"[yellow]📊 Port {port_num}: {files_processed} files processed, {files_skipped} skipped[/yellow]")
        
        # Check if we found any meaningful data
        if target_service and target_service.enumeration_data:
            if RICH_AVAILABLE:
                data_types = list(target_service.enumeration_data.keys())
                console.print(f"[green]✅ Port {port_num}: Found data types: {', '.join(data_types[:5])}{('...' if len(data_types) > 5 else '')}[/green]")
        elif files_processed > 0:
            if RICH_AVAILABLE:
                console.print(f"[yellow]⚠️ Port {port_num}: {files_processed} files processed but no data extracted[/yellow]")
    
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
                    # Filter out non-executable content
                    if self.parser._is_valid_manual_command(line):
                        results.manual_commands.append(line)
                        
            except Exception as e:
                if RICH_AVAILABLE:
                    console.print(f"[red]Error parsing manual commands: {e}[/red]")
        
        # Parse hostname discovery
        hostname_file = scan_dir / "_hostname_discovery.txt"
        if hostname_file.exists():
            try:
                with open(hostname_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for line in content.split('\n'):
                    line = line.strip()
                    # Skip header line and empty lines
                    if line and not line.startswith('Discovered hostnames:') and not line.startswith('#'):
                        # Remove leading whitespace/bullets
                        hostname = line.lstrip(' -•*').strip()

                        # Validate hostname before adding
                        if hostname and hostname not in results.hostnames:
                            # Basic hostname validation
                            import re
                            if re.match(r'^[a-zA-Z0-9.-]+$', hostname) and '..' not in hostname:
                                if not hostname.endswith('.html') and not hostname.endswith('.php'):
                                    if not hostname.endswith('home') and not hostname.endswith('index'):
                                        results.hostnames.append(hostname)
                                        if RICH_AVAILABLE:
                                            console.print(f"[green]🌐 Found hostname: {hostname}[/green]")
                                    else:
                                        if RICH_AVAILABLE:
                                            console.print(f"[yellow]⚠️ Skipped invalid hostname (looks like path): {hostname}[/yellow]")
                                else:
                                    if RICH_AVAILABLE:
                                        console.print(f"[yellow]⚠️ Skipped invalid hostname (file extension): {hostname}[/yellow]")
                            else:
                                if RICH_AVAILABLE:
                                    console.print(f"[yellow]⚠️ Skipped invalid hostname format: {hostname}[/yellow]")
                            
            except Exception as e:
                if RICH_AVAILABLE:
                    console.print(f"[red]Error parsing hostname discovery: {e}[/red]")
    
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
    else:
        # Standard mode: consolidate results only
        consolidator.consolidate_all_targets(args.target)
        
        if RICH_AVAILABLE:
            console.print()
            console.print(f"[bold green]✅ Results consolidated for {len(consolidator.targets)} target(s)[/bold green]")
            console.print("[dim]Use the report_renderer module to generate Markdown reports[/dim]")
            console.print()
        else:
            print(f"\n✅ Results consolidated for {len(consolidator.targets)} target(s)")
            print("Use the report_renderer module to generate Markdown reports\n")


if __name__ == "__main__":
    main()