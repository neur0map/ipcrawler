"""LEGACY Master report generator for IPCrawler - DEPRECATED
USE: src.core.reporting.reporting_engine.ReportingEngine instead
This file is kept for compatibility but should not be used in new code.
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from ..base_reporter import BaseReporter


class MasterReporter(BaseReporter):
    """DEPRECATED - Use ReportingEngine instead"""
    
    def __init__(self, output_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize master text reporter"""
        super().__init__(output_dir)
        self.theme = theme
    
    def get_format_name(self) -> str:
        """Get the report format name"""
        return "MASTER_TXT"
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate comprehensive master TXT report
        
        Args:
            data: Combined workflow data
            **kwargs: Additional options (target, timestamp)
            
        Returns:
            Path to generated report
        """
        
        # Prepare comprehensive context
        context = self._prepare_master_context(data, **kwargs)
        
        target = kwargs.get('target', data.get('target', 'unknown'))
        filename = f"master_report_{self._sanitize_filename(target)}.txt"
        output_path = self.output_dir / filename
        
        try:
            # Generate simple master report directly (no template dependency)
            content = self._generate_simple_master_report(data, **kwargs)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return output_path
            
        except Exception as e:
            # Fallback to basic master report
            return self._generate_fallback_master_report(data, **kwargs)
    
    def _prepare_master_context(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare comprehensive context for master report"""
        target = kwargs.get('target', data.get('target', 'Unknown'))
        
        # Base context
        context = {
            'data': data,
            'target': target,
            'title': f'IPCrawler Security Assessment - {target}',
            'workflow': 'comprehensive',
            'generated': datetime.now(),
        }
        
        # Aggregate summary from all workflows
        context['summary'] = self._build_comprehensive_summary(data)
        
        # Extract and organize workflow data with enhanced processing
        context['hosts'] = self._process_hosts_data(data.get('hosts', []))
        context['http_scan'] = self._process_http_scan_data(data.get('http_scan', {}))
        context['mini_spider'] = self._process_mini_spider_data(data.get('mini_spider', {}))
        context['smartlist'] = self._process_smartlist_data(data.get('smartlist', {}))
        
        # Add metadata
        context['metadata'] = {
            'generator': 'IPCrawler',
            'version': '2.0',
            'timestamp': datetime.now(),
            'target': target,
            'workflows_included': self._get_included_workflows(data)
        }
        
        # Add theme info for template
        context['theme'] = {
            'name': self.theme
        }
        
        return context
    
    def _process_hosts_data(self, hosts: list) -> list:
        """Process and enhance host data for comprehensive reporting"""
        processed_hosts = []
        
        for host in hosts:
            processed_host = host.copy()
            
            # Normalize host data structure
            if 'address' in host:
                processed_host['ip'] = host['address']
            elif 'host' in host:
                processed_host['ip'] = host['host']
            
            # Categorize ports for better display
            if 'ports' in host:
                ports = host['ports']
                processed_host['open_ports'] = [p for p in ports if p.get('state') == 'open']
                processed_host['closed_ports'] = [p for p in ports if p.get('state') == 'closed']
                processed_host['filtered_ports'] = [p for p in ports if p.get('state') == 'filtered']
                
                services = {}
                for port in processed_host['open_ports']:
                    service = port.get('service', 'unknown')
                    if service not in services:
                        services[service] = []
                    services[service].append(port)
                
                service_lines = []
                for service, service_ports in services.items():
                    port_nums = [str(p.get('port', '?')) for p in service_ports]
                    service_lines.append(f"{service} ({', '.join(port_nums)})")
                processed_host['service_summary_text'] = '; '.join(service_lines)
            
            processed_hosts.append(processed_host)
        
        return processed_hosts
    
    def _process_http_scan_data(self, http_scan: dict) -> dict:
        """Process and enhance HTTP scan data for comprehensive reporting"""
        if not http_scan:
            return {}
        
        processed = http_scan.copy()
        
        # Add vulnerability summary
        if 'vulnerabilities' in http_scan:
            vuln_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
            
            for vuln in http_scan['vulnerabilities']:
                severity = vuln.get('severity', 'info').lower()
                if severity in vuln_counts:
                    vuln_counts[severity] += 1
            
            processed['vulnerability_summary'] = vuln_counts
            processed['total_vulnerabilities'] = sum(vuln_counts.values())
        
        # Enhance service data
        if 'services' in http_scan:
            for service in processed['services']:
                if 'technologies' in service:
                    if isinstance(service['technologies'], list):
                        service['tech_list'] = ', '.join(service['technologies'])
                    else:
                        service['tech_list'] = str(service['technologies'])
                else:
                    service['tech_list'] = 'None detected'
        
        return processed
    
    def _process_mini_spider_data(self, mini_spider: dict) -> dict:
        """Process and enhance Mini Spider data for comprehensive reporting"""
        if not mini_spider:
            return {}
        
        processed = mini_spider.copy()
        
        # Calculate URL statistics
        if 'categorized_urls' in mini_spider:
            category_stats = {}
            total_urls = 0
            
            for category, urls in mini_spider['categorized_urls'].items():
                category_name = category if isinstance(category, str) else str(category)
                url_count = len(urls) if isinstance(urls, list) else 0
                category_stats[category_name] = url_count
                total_urls += url_count
            
            processed['category_stats'] = category_stats
            processed['total_discovered_urls'] = total_urls
        elif 'discovered_urls' in mini_spider:
            processed['total_discovered_urls'] = len(mini_spider['discovered_urls'])
        
        return processed
    
    def _process_smartlist_data(self, smartlist: dict) -> dict:
        """Process and enhance SmartList data for comprehensive reporting - NO HARDCODED PATHS"""
        if not smartlist:
            return {}
        
        processed = smartlist.copy()
        
        # Add recommendation statistics
        if 'wordlist_recommendations' in smartlist:
            total_wordlists = 0
            confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
            ports_with_recommendations = set()
            
            for service_rec in smartlist['wordlist_recommendations']:
                # Extract port from service identifier
                service_id = service_rec.get('service', '')
                if ':' in service_id:
                    port = service_id.split(':')[1]
                    ports_with_recommendations.add(port)
                
                if 'top_wordlists' in service_rec:
                    total_wordlists += len(service_rec['top_wordlists'])
                    
                    # NO HARDCODED PATH INJECTION - Use SmartList resolved paths only
                    # SmartList engine should provide all necessary path information
                
                confidence = service_rec.get('confidence', 'low').lower()
                if confidence in confidence_counts:
                    confidence_counts[confidence] += 1
            
            processed['stats'] = {
                'total_wordlists': total_wordlists,
                'confidence_counts': confidence_counts,
                'services_analyzed': len(smartlist['wordlist_recommendations']),
                'ports_analyzed': len(ports_with_recommendations),
                'port_list': sorted(list(ports_with_recommendations))
            }
        
        # Enhance summary with port-based organization hints
        if 'stats' in processed:
            port_count = processed['stats']['ports_analyzed']
            if port_count > 1:
                processed['summary'] = processed.get('summary', {})
                processed['summary']['organization_note'] = f"Recommendations organized by {port_count} different ports/services"
        
        return processed
    
    def _build_comprehensive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive summary from all workflow data"""
        summary = {
            'total_hosts': 0,
            'up_hosts': 0,
            'down_hosts': 0,
            'total_ports': 0,
            'open_ports': 0,
            'services_detected': 0,
            'http_services': 0,
            'discovered_urls': 0,
            'vulnerabilities': 0,
            'wordlist_recommendations': 0,
            'duration': data.get('total_execution_time', data.get('duration', 0))
        }
        
        # Aggregate from base scan data
        if 'hosts' in data:
            hosts = data['hosts']
            summary['total_hosts'] = len(hosts)
            
            for host in hosts:
                if host.get('status') == 'up':
                    summary['up_hosts'] += 1
                else:
                    summary['down_hosts'] += 1
                
                ports = host.get('ports', [])
                summary['total_ports'] += len(ports)
                open_ports = [p for p in ports if p.get('state') == 'open']
                summary['open_ports'] += len(open_ports)
                summary['services_detected'] += len([p for p in open_ports if p.get('service')])
        
        # Add HTTP scan data
        if 'http_scan' in data:
            http_data = data['http_scan']
            summary['http_services'] = len(http_data.get('services', []))
            summary['vulnerabilities'] += len(http_data.get('vulnerabilities', []))
        
        # Add Mini Spider data
        if 'mini_spider' in data:
            spider_data = data['mini_spider']
            summary['discovered_urls'] = len(spider_data.get('discovered_urls', []))
        
        # Add SmartList data
        if 'smartlist' in data:
            smartlist_data = data['smartlist']
            summary['wordlist_recommendations'] = len(smartlist_data.get('wordlist_recommendations', []))
        
        return summary
    
    def _get_included_workflows(self, data: Dict[str, Any]) -> list:
        """Get list of workflows included in the data"""
        workflows = []
        
        workflow_keys = ['hosts', 'http_scan', 'mini_spider', 'smartlist']
        for key in workflow_keys:
            if key in data and data[key]:
                workflows.append(key)
        
        return workflows
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility, preserving dots for IPs"""
        # Replace only truly invalid filesystem characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        return sanitized
    
    def _generate_simple_master_report(self, data: Dict[str, Any], **kwargs) -> str:
        """Generate simple master TXT report"""
        target = kwargs.get('target', data.get('target', 'unknown'))
        summary = self._build_comprehensive_summary(data)
        
        txt_content = f"""{'=' * 80}
IPCrawler Master Report - {target}
{'=' * 80}

{'-' * 80}
SCAN SUMMARY
{'-' * 80}
Target(s): {summary['total_hosts']} host(s) analyzed
Hosts Up: {summary['up_hosts']}
Total Ports: {summary['total_ports']}
Open Ports: {summary['open_ports']}
Services Detected: {summary['services_detected']}
HTTP Services: {summary['http_services']}
URLs Discovered: {summary['discovered_urls']}
Vulnerabilities: {summary['vulnerabilities']}
Wordlist Recommendations: {summary['wordlist_recommendations']}
Scan Duration: {summary['duration']:.2f} seconds

"""

        # Add hosts section
        if 'hosts' in data and data['hosts']:
            txt_content += f"""{'=' * 80}
HOST DISCOVERY RESULTS
{'=' * 80}

"""
            for host in data['hosts']:
                host_ip = host.get('address', host.get('ip', 'Unknown'))
                hostname = host.get('hostname', '')
                status = host.get('status', 'unknown')
                
                txt_content += f"{'-' * 80}\n"
                txt_content += f"Host: {host_ip}\n"
                if hostname:
                    txt_content += f"Hostname: {hostname}\n"
                txt_content += f"Status: {status.upper()}\n"
                
                # Add ports
                ports = host.get('ports', [])
                open_ports = [p for p in ports if p.get('state') == 'open']
                if open_ports:
                    txt_content += f"\nOpen Ports ({len(open_ports)}):\n"
                    for port in open_ports[:20]:  # Limit to first 20 ports
                        port_num = port.get('port', 'N/A')
                        service = port.get('service', 'unknown')
                        protocol = port.get('protocol', 'tcp')
                        txt_content += f"  {port_num}/{protocol} - {service}\n"
                        
                        if 'version' in port:
                            txt_content += f"    Version: {port['version']}\n"
                        if 'product' in port:
                            txt_content += f"    Product: {port['product']}\n"
                    
                    if len(open_ports) > 20:
                        txt_content += f"  ... and {len(open_ports) - 20} more ports\n"
                else:
                    txt_content += "\nNo open ports detected on this host.\n"
                
                txt_content += "\n"

        # Add HTTP scan results
        if 'http_scan' in data and data['http_scan']:
            http_data = data['http_scan']
            txt_content += f"""{'=' * 80}
HTTP SCANNING RESULTS
{'=' * 80}
"""
            
            if 'services' in http_data:
                txt_content += f"HTTP Services Analyzed: {len(http_data['services'])}\n\n"
                
                for service in http_data['services']:
                    txt_content += f"{'-' * 40}\n"
                    txt_content += f"URL: {service.get('url', 'N/A')}\n"
                    txt_content += f"Status Code: {service.get('status_code', 'N/A')}\n"
                    txt_content += f"Server: {service.get('server', 'Unknown')}\n"
                    
                    # Add technologies
                    if 'technologies' in service:
                        tech_list = service['technologies'] if isinstance(service['technologies'], str) else ', '.join(service.get('technologies', []))
                        txt_content += f"Technologies: {tech_list or 'None detected'}\n"
                    
                    # Add discovered paths (limited)
                    if 'discovered_paths' in service and service['discovered_paths']:
                        paths = service['discovered_paths'][:10]
                        txt_content += f"Discovered Paths: {len(service['discovered_paths'])} found\n"
                        for path in paths:
                            txt_content += f"  • {path}\n"
                        if len(service['discovered_paths']) > 10:
                            txt_content += f"  ... and {len(service['discovered_paths']) - 10} more paths\n"
                    
                    txt_content += "\n"
            
            # Add vulnerability summary
            if 'vulnerabilities' in http_data and http_data['vulnerabilities']:
                vuln_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
                for vuln in http_data['vulnerabilities']:
                    severity = vuln.get('severity', 'info').lower()
                    if severity in vuln_counts:
                        vuln_counts[severity] += 1
                
                txt_content += f"\nSecurity Vulnerabilities Summary:\n"
                for severity, count in vuln_counts.items():
                    if count > 0:
                        txt_content += f"  {severity.upper()}: {count}\n"

        # Add Mini Spider results
        if 'mini_spider' in data and data['mini_spider']:
            spider_data = data['mini_spider']
            txt_content += f"""\n{'=' * 80}
CONTENT DISCOVERY (MINI SPIDER)
{'=' * 80}
"""
            
            if 'discovered_urls' in spider_data:
                txt_content += f"Total URLs Discovered: {len(spider_data['discovered_urls'])}\n\n"
                
                # Show first 20 URLs
                for url in spider_data['discovered_urls'][:20]:
                    if isinstance(url, dict):
                        txt_content += f"  • {url.get('url', str(url))}\n"
                    else:
                        txt_content += f"  • {url}\n"
                
                if len(spider_data['discovered_urls']) > 20:
                    txt_content += f"  ... and {len(spider_data['discovered_urls']) - 20} more URLs\n"

        # Add SmartList results - DYNAMIC ONLY, NO HARDCODED PATHS
        if 'smartlist' in data and data['smartlist']:
            smartlist_data = data['smartlist']
            txt_content += f"""\n{'=' * 80}
SMARTLIST WORDLIST RECOMMENDATIONS
{'=' * 80}
"""
            
            if 'wordlist_recommendations' in smartlist_data:
                # Group recommendations by port
                port_groups = {}
                for service_rec in smartlist_data['wordlist_recommendations']:
                    service_id = service_rec.get('service', 'unknown:unknown')
                    if ':' in service_id:
                        port = service_id.split(':')[1]
                        service_name = service_rec.get('service_name', 'unknown')
                        port_key = f"{port}/{service_name}"
                        
                        if port_key not in port_groups:
                            port_groups[port_key] = []
                        port_groups[port_key].append(service_rec)
                
                txt_content += f"Total Services Analyzed: {len(smartlist_data['wordlist_recommendations'])}\n"
                txt_content += f"Ports with Recommendations: {len(port_groups)}\n\n"
                
                # Display recommendations grouped by port
                for port_key, services in port_groups.items():
                    port_num, service_name = port_key.split('/', 1)
                    txt_content += f"{'=' * 60}\n"
                    txt_content += f"PORT {port_num}/tcp - {service_name.title()} Service\n"
                    txt_content += f"{'=' * 60}\n\n"
                    
                    for service_rec in services:
                        txt_content += f"Target: {service_rec.get('service', 'Unknown')}\n"
                        if 'detected_technology' in service_rec:
                            txt_content += f"Technology: {service_rec['detected_technology']}\n"
                        txt_content += f"Overall Confidence: {service_rec.get('confidence', 'Unknown').upper()}\n\n"
                        
                        if 'top_wordlists' in service_rec and service_rec['top_wordlists']:
                            txt_content += f"PRIORITY WORDLIST RECOMMENDATIONS:\n"
                            txt_content += f"{'-' * 50}\n\n"
                            
                            # Sort wordlists by score (highest first)
                            wordlists = sorted(service_rec['top_wordlists'], 
                                             key=lambda x: x.get('score', 0), reverse=True)
                            
                            for wl in wordlists:
                                score = wl.get('score', 0)
                                confidence = wl.get('confidence', 'low')
                                
                                # Determine priority level
                                if score >= 80 or confidence == 'high':
                                    priority = "CRITICAL"
                                elif score >= 60:
                                    priority = "HIGH"
                                elif score >= 40:
                                    priority = "MEDIUM"
                                else:
                                    priority = "LOW"
                                
                                txt_content += f"{priority}: {wl.get('wordlist', 'N/A')} (Score: {score})\n"
                                
                                # Use ONLY paths provided by SmartList - NO HARDCODED FALLBACKS
                                if 'path' in wl and wl['path']:
                                    txt_content += f"  📁 Path: {wl['path']}\n"
                                else:
                                    txt_content += f"  📁 Path: [Path resolution required]\n"
                                
                                if 'reason' in wl:
                                    txt_content += f"  🎯 Reason: {wl['reason']}\n"
                                
                                if wl.get('category') and wl['category'] != 'none':
                                    txt_content += f"  📂 Category: {wl['category']}\n"
                                
                                txt_content += "\n"
                        else:
                            txt_content += "No specific wordlist recommendations available for this service.\n\n"
                    
                    txt_content += "\n"
                
                # Add overall usage notes
                txt_content += f"{'-' * 80}\n"
                txt_content += "💡 USAGE NOTES:\n"
                txt_content += "• Use CRITICAL and HIGH priority wordlists first for maximum efficiency\n"
                txt_content += "• All paths are dynamically resolved by SmartList engine\n"
                txt_content += "• Combine multiple wordlists for comprehensive coverage\n"
                txt_content += "• Consider service-specific context when selecting wordlists\n\n"

        txt_content += f"""\n{'=' * 80}
REPORT GENERATED BY IPCRAWLER SMARTLIST ENGINE
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 80}
"""
        
        return txt_content
    
    def _generate_fallback_master_report(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate simple master TXT report as fallback"""
        target = kwargs.get('target', data.get('target', 'unknown'))
        filename = f"master_report_{self._sanitize_filename(target)}.txt"
        output_path = self.output_dir / filename
        
        try:
            content = self._generate_simple_master_report(data, **kwargs)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return output_path
        except Exception as e:
            # Absolute minimal fallback
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"IPCrawler Master Report - {target}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Error generating full report: {e}\n")
                f.write(f"\nRaw data:\n{data}\n")
            return output_path