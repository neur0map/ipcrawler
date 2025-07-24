"""Text report formatter for IPCrawler

Generates human-readable text reports from scan data.
"""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from ..base.reporter import BaseReporter


class TextReporter(BaseReporter):
    """Generates detailed text reports"""
    
    def __init__(self, output_dir: Path):
        super().__init__(output_dir)
    
    def get_format(self) -> str:
        """Get the report format name"""
        return 'txt'
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate text report
        
        Args:
            data: Scan data to format
            **kwargs: Additional options (target, workflow, timestamp)
            
        Returns:
            Path to generated text file
        """
        target = kwargs.get('target', 'unknown')
        workflow = kwargs.get('workflow', 'scan')
        timestamp = kwargs.get('timestamp', datetime.now())
        
        # Generate filename
        filename = f"{workflow}_report_{target}_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.output_dir / filename
        
        # Format content
        content = self._format_text_report(target, data)
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _format_text_report(self, target: str, data: Dict[str, Any]) -> str:
        """Generate detailed text report content"""
        report = []
        report.append("IP CRAWLER SCAN REPORT")
        report.append(f"Target: {target}")
        report.append(f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Command: {data.get('command', 'N/A')}")
        report.append(f"Duration: {data.get('duration', 0):.2f} seconds")
        report.append(f"Hosts: {data.get('total_hosts', 0)} total, {data.get('up_hosts', 0)} up, {data.get('down_hosts', 0)} down")
        
        # Add hostname mappings from fast scan
        if 'hostname_mappings' in data and data['hostname_mappings']:
            report.append(f"\nDiscovered Hostname Mappings (from fast scan):")
            for mapping in data['hostname_mappings']:
                report.append(f"  {mapping['hostname']} → {mapping['ip']}")
        
        report.append("=" * 80)
        
        # Host details
        for host in data.get('hosts', []):
            report.append(f"\nHost: {host['ip']}")
            if host.get('hostname'):
                report.append(f"Hostname: {host['hostname']}")
            if host.get('os'):
                report.append(f"OS: {host['os']} (Accuracy: {host.get('os_accuracy', 'N/A')}%)")
            if host.get('mac_address'):
                report.append(f"MAC: {host['mac_address']} ({host.get('mac_vendor', 'Unknown vendor')})")
            
            # Open ports
            open_ports = [p for p in host.get('ports', []) if p.get('state') == 'open']
            if open_ports:
                report.append(f"\nOpen Ports: {len(open_ports)}")
                for port in open_ports:
                    report.append(f"  {port['port']}/{port['protocol']} - {port.get('service', 'unknown')}")
                    if port.get('version'):
                        report.append(f"    Version: {port['version']}")
                    if port.get('product'):
                        report.append(f"    Product: {port['product']}")
                    
                    # Script results
                    if port.get('scripts'):
                        for script in port['scripts']:
                            report.append(f"    Script: {script['id']}")
                            for line in script['output'].strip().split('\n'):
                                report.append(f"      {line}")
            
            report.append("-" * 80)
        
        # HTTP scan results
        if 'http_scan' in data:
            report.extend(self._format_http_section(data['http_scan']))
        
        # SmartList recommendations
        if 'smartlist' in data:
            report.extend(self._format_smartlist_section(data['smartlist']))
        
        # Mini Spider results
        if 'mini_spider' in data:
            report.extend(self._format_mini_spider_section(data['mini_spider']))
        
        return "\n".join(report)
    
    def _format_http_section(self, http_data: Dict[str, Any]) -> list:
        """Format HTTP scan results section"""
        report = []
        report.append("\n" + "=" * 80)
        report.append("HTTP/HTTPS SCAN RESULTS")
        report.append("=" * 80)
        
        # Check if HTTP scan has any data
        has_data = any([
            http_data.get('services'),
            http_data.get('vulnerabilities'),
            http_data.get('dns_records'),
            http_data.get('subdomains')
        ])
        
        if not has_data:
            if http_data.get('fallback_mode'):
                report.append("\nHTTP scan completed using fallback mode (curl+nslookup).")
                report.append("No HTTP services found or target not responding to HTTP requests.")
            else:
                report.append("\nNo HTTP scan data collected. This may be due to:")
                report.append("  • Target not responding to HTTP requests")
                report.append("  • Scanner configuration issues")
                report.append("  • Network connectivity problems")
        else:
            # Add scan engine info
            scan_engine = http_data.get('scan_engine', 'unknown')
            if http_data.get('fallback_mode'):
                report.append(f"\nHTTP scan completed using fallback mode ({scan_engine})")
            else:
                report.append(f"\nHTTP scan completed using {scan_engine}")
        
        # HTTP Services
        services = http_data.get('services', [])
        if services:
            report.append(f"\nHTTP Services Found: {len(services)}")
            for service in services:
                report.append(f"\n  {service.get('url', 'Unknown URL')}")
                report.append(f"    Status: {service.get('status_code', 'N/A')}")
                report.append(f"    Server: {service.get('server', 'Unknown')}")
                if service.get('technologies'):
                    report.append(f"    Technologies: {', '.join(service['technologies'])}")
                if service.get('discovered_paths'):
                    report.append(f"    Discovered Paths: {len(service['discovered_paths'])}")
                    for path in service['discovered_paths']:
                        report.append(f"      • {path}")
        
        # Vulnerabilities
        vulns = http_data.get('vulnerabilities', [])
        if vulns:
            report.append(f"\nHTTP Vulnerabilities: {len(vulns)}")
            severity_order = ['critical', 'high', 'medium', 'low']
            for severity in severity_order:
                severity_vulns = [v for v in vulns if v.get('severity') == severity]
                if severity_vulns:
                    report.append(f"\n  {severity.upper()} ({len(severity_vulns)})")
                    for vuln in severity_vulns[:3]:  # Show first 3 of each severity
                        report.append(f"    • {vuln.get('description', 'N/A')}")
                        if vuln.get('evidence'):
                            report.append(f"      Evidence: {vuln['evidence']}")
        
        # DNS and Subdomains
        subdomains = http_data.get('subdomains', [])
        if subdomains:
            report.append(f"\nDiscovered Subdomains: {len(subdomains)}")
            for subdomain in subdomains[:10]:
                report.append(f"  • {subdomain}")
        
        dns_records = http_data.get('dns_records', [])
        if dns_records:
            report.append(f"\nDNS Records: {len(dns_records)}")
            for record in dns_records[:10]:
                report.append(f"  {record.get('type', 'N/A')}: {record.get('value', 'N/A')}")
        
        return report
    
    def _format_smartlist_section(self, smartlist_data: Dict[str, Any]) -> list:
        """Format SmartList recommendations section"""
        report = []
        report.append("\n" + "=" * 80)
        report.append("SMARTLIST WORDLIST RECOMMENDATIONS")
        report.append("=" * 80)
        
        summary = smartlist_data.get('summary', {})
        report.append(f"\nAnalysis Summary:")
        report.append(f"  Services Analyzed: {summary.get('total_services_analyzed', 0)}")
        report.append(f"  Total Wordlists: {summary.get('total_wordlists_recommended', 0)}")
        report.append(f"  High Confidence: {summary.get('high_confidence_services', 0)}")
        report.append(f"  Technologies: {', '.join(summary.get('detected_technologies', []))}")
        report.append(f"\nRecommendation: {summary.get('recommendation', 'None')}")
        
        # Wordlist recommendations by service
        recommendations = smartlist_data.get('wordlist_recommendations', [])
        if recommendations:
            report.append("\nWordlist Recommendations by Service:")
            for service_rec in recommendations:
                report.append(f"\n{service_rec['service']} ({service_rec['service_name']})")
                if service_rec.get('detected_technology'):
                    report.append(f"  Technology: {service_rec['detected_technology']}")
                report.append(f"  Confidence: {service_rec['confidence']} (Score: {service_rec['total_score']})")
                
                # Top wordlists
                report.append("  Top Wordlists:")
                for i, wl in enumerate(service_rec.get('top_wordlists', [])[:3], 1):
                    report.append(f"    {i}. {wl['wordlist']} (Score: {wl['score']})")
                    report.append(f"       Confidence: {wl['confidence']}")
                    report.append(f"       Reason: {wl['reason']}")
                    if wl.get('matched_rule'):
                        report.append(f"       Rule: {wl['matched_rule']}")
                    if wl.get('path'):
                        report.append(f"       Path: {wl['path']}")
                
                # Context information
                context = service_rec.get('context', {})
                if context.get('matched_rules'):
                    report.append(f"  Matched Rules: {', '.join(context['matched_rules'])}")
                if context.get('fallback_used'):
                    report.append("  ⚠ Generic fallback was used")
        
        return report
    
    def _format_mini_spider_section(self, mini_spider_data: Dict[str, Any]) -> list:
        """Format Mini Spider results section"""
        report = []
        report.append("\n" + "=" * 80)
        report.append("MINI SPIDER RESULTS")
        report.append("=" * 80)
        
        # Summary stats
        discovered_urls = mini_spider_data.get('discovered_urls', [])
        categorized_results = mini_spider_data.get('categorized_results', {})
        
        report.append(f"\nURLs Discovered: {len(discovered_urls)}")
        
        if categorized_results:
            report.append("\nURLs by Category:")
            for category, urls in categorized_results.items():
                category_name = category if isinstance(category, str) else str(category)
                report.append(f"  {category_name}: {len(urls)} URLs")
        
        # Show sample URLs from each category
        if categorized_results:
            report.append("\nSample URLs:")
            for category, urls in categorized_results.items():
                category_name = category if isinstance(category, str) else str(category)
                if urls:
                    report.append(f"\n  {category_name}:")
                    for url in urls[:5]:  # Show first 5 URLs
                        url_str = url if isinstance(url, str) else url.get('url', str(url))
                        report.append(f"    • {url_str}")
                    if len(urls) > 5:
                        report.append(f"    ... and {len(urls) - 5} more")
        
        return report