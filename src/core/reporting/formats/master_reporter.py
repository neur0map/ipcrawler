"""Master report generator for IPCrawler

"""




    """Generates comprehensive master TXT report combining all workflows"""
    
    def __init__(self, output_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize master text reporter
        
        """
        self.theme = theme
        self.template_engine = get_template_engine(theme)
    
        """Get the report format name"""
    
        """Generate comprehensive master TXT report
        
            **kwargs: Additional options (target, timestamp)
            
        """
        
        # Prepare comprehensive context
        context = self._prepare_master_context(data, **kwargs)
        
        target = kwargs.get('target', data.get('target', 'unknown'))
        filename = f"master_report_{self._sanitize_filename(target)}.txt"
        output_path = self.output_dir / filename
        
            # Render comprehensive template
            txt_content = self.template_engine.render_template(
                'workflows/comprehensive_report.txt.j2', 
            )
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
            
            console.success(f"Generated master TXT report: {output_path}", internal=True)
            
            console.error(f"Failed to generate master TXT report: {e}", internal=True)
            # Fallback to simple master report
    
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
            'template': 'comprehensive_report.txt.j2',
            'timestamp': datetime.now(),
            'target': target,
            'workflows_included': self._get_included_workflows(data)
        }
        
        # Add theme info for template
        context['theme'] = {
            'name': self.theme
        }
        
    
        """Process and enhance host data for comprehensive reporting"""
        processed_hosts = []
        
            processed_host = host.copy()
            
            # Normalize host data structure
                processed_host['ip'] = host['address']
                processed_host['ip'] = host['host']
            
            # Categorize ports for better display
                ports = host['ports']
                processed_host['open_ports'] = [p for p in ports if p.get('state') == 'open']
                processed_host['closed_ports'] = [p for p in ports if p.get('state') == 'closed']
                processed_host['filtered_ports'] = [p for p in ports if p.get('state') == 'filtered']
                
                services = {}
                    service = port.get('service', 'unknown')
                        services[service] = []
                
                service_lines = []
                processed_host['service_summary_text'] = '; '.join(service_lines)
            
        
    
        """Process and enhance HTTP scan data for comprehensive reporting"""
        
        processed = http_scan.copy()
        
            vuln_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
            
                severity = vuln.get('severity', 'info').lower()
                    vuln_counts[severity] += 1
            
            processed['vulnerability_summary'] = vuln_counts
            processed['total_vulnerabilities'] = sum(vuln_counts.values())
        
                        service['tech_list'] = ', '.join(service['technologies'])
                        service['tech_list'] = str(service['technologies'])
                    service['tech_list'] = 'None detected'
        
    
        """Process and enhance Mini Spider data for comprehensive reporting"""
        
        processed = mini_spider.copy()
        
        # Calculate URL statistics
            category_stats = {}
            total_urls = 0
            
                category_name = category if isinstance(category, str) else str(category)
                url_count = len(urls) if isinstance(urls, list) else 0
                category_stats[category_name] = url_count
                total_urls += url_count
            
            processed['category_stats'] = category_stats
            processed['total_discovered_urls'] = total_urls
        
            processed['total_discovered_urls'] = len(mini_spider['discovered_urls'])
        
    
        """Process and enhance SmartList data for comprehensive reporting"""
        
        processed = smartlist.copy()
        
        # Add recommendation statistics
            total_wordlists = 0
            confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
            ports_with_recommendations = set()
            
                # Extract port from service identifier
                service_id = service_rec.get('service', '')
                    port = service_id.split(':')[1]
                
                    total_wordlists += len(service_rec['top_wordlists'])
                    
                    # Ensure path information is available for each wordlist
                            # Add fallback path information
                            wordlist_name = wordlist['wordlist']
                            # Try to infer common SecLists path structure
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                                wordlist['path'] = f"/usr/share/seclists/Discovery/Web-Content/{wordlist_name}"
                
                confidence = service_rec.get('confidence', 'low').lower()
                    confidence_counts[confidence] += 1
            
            processed['stats'] = {
                'total_wordlists': total_wordlists,
                'confidence_counts': confidence_counts,
                'services_analyzed': len(smartlist['wordlist_recommendations']),
                'ports_analyzed': len(ports_with_recommendations),
                'port_list': sorted(list(ports_with_recommendations))
            }
        
        # Enhance summary with port-based organization hints
            port_count = processed['stats']['ports_analyzed']
                processed['summary']['organization_note'] = f"Recommendations organized by {port_count} different ports/services"
        
    
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
            hosts = data['hosts']
            summary['total_hosts'] = len(hosts)
            
                if host.get('status') == 'up':
                    summary['up_hosts'] += 1
                    summary['down_hosts'] += 1
                
                ports = host.get('ports', [])
                summary['total_ports'] += len(ports)
                open_ports = [p for p in ports if p.get('state') == 'open']
                summary['open_ports'] += len(open_ports)
                summary['services_detected'] += len([p for p in open_ports if p.get('service')])
        
        # Add HTTP scan data
            http_data = data['http_scan']
            summary['http_services'] = len(http_data.get('services', []))
            summary['vulnerabilities'] += len(http_data.get('vulnerabilities', []))
        
        # Add Mini Spider data
            spider_data = data['mini_spider']
            summary['discovered_urls'] = len(spider_data.get('discovered_urls', []))
        
        # Add SmartList data
            smartlist_data = data['smartlist']
            summary['wordlist_recommendations'] = len(smartlist_data.get('wordlist_recommendations', []))
        
    
        """Get list of workflows included in the data"""
        workflows = []
        
            
    
        """Sanitize filename for filesystem compatibility, preserving dots for IPs"""
        # Replace only truly invalid filesystem characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    
        """Generate simple master TXT report as fallback"""
        target = kwargs.get('target', data.get('target', 'unknown'))
        summary = self._build_comprehensive_summary(data)
        
        txt_content = f"""{'=' * 80}
{'=' * 80}

{'-' * 80}

"""

        # Add hosts section
            txt_content += f"""{'=' * 80}
{'=' * 80}


"""
                host_ip = host.get('address', host.get('ip', 'Unknown'))
                hostname = host.get('hostname', '')
                status = host.get('status', 'unknown')
                
                txt_content += f"{'-' * 80}\n"
                txt_content += f"Host: {host_ip}\n"
                    txt_content += f"Hostname: {hostname}\n"
                txt_content += f"Status: {status.upper()}\n"
                
                # Add ports
                ports = host.get('ports', [])
                open_ports = [p for p in ports if p.get('state') == 'open']
                    txt_content += f"\nOpen Ports ({len(open_ports)}):\n"
                        port_num = port.get('port', 'N/A')
                        service = port.get('service', 'unknown')
                        protocol = port.get('protocol', 'tcp')
                        txt_content += f"  {port_num}/{protocol} - {service}\n"
                        
                            txt_content += f"    Version: {port['version']}\n"
                            txt_content += f"    Product: {port['product']}\n"
                    
                        txt_content += f"  ... and {len(open_ports) - 20} more ports\n"
                    txt_content += "\nNo open ports detected on this host.\n"
                
                txt_content += "\n"

        # Add HTTP scan results
            http_data = data['http_scan']
            txt_content += f"""{'=' * 80}
{'=' * 80}

"""
            
                txt_content += f"HTTP Services Analyzed: {len(http_data['services'])}\n\n"
                
                    txt_content += f"{'-' * 40}\n"
                    txt_content += f"URL: {service.get('url', 'N/A')}\n"
                    txt_content += f"Status Code: {service.get('status_code', 'N/A')}\n"
                    txt_content += f"Server: {service.get('server', 'Unknown')}\n"
                    
                    # Add technologies
                        tech_list = service['technologies'] if isinstance(service['technologies'], str) else ', '.join(service.get('technologies', []))
                        txt_content += f"Technologies: {tech_list or 'None detected'}\n"
                    
                    # Add discovered paths (limited)
                        paths = service['discovered_paths'][:10]
                        txt_content += f"Discovered Paths: {len(service['discovered_paths'])} found\n"
                            txt_content += f"  • {path}\n"
                            txt_content += f"  ... and {len(service['discovered_paths']) - 10} more paths\n"
                    
                    txt_content += "\n"
            
            # Add vulnerability summary
                vuln_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
                    severity = vuln.get('severity', 'info').lower()
                        vuln_counts[severity] += 1
                
                txt_content += f"\nSecurity Vulnerabilities Summary:\n"
                        txt_content += f"  {severity.upper()}: {count}\n"

        # Add Mini Spider results
            spider_data = data['mini_spider']
            txt_content += f"""\n{'=' * 80}
{'=' * 80}

"""
            
                txt_content += f"Total URLs Discovered: {len(spider_data['discovered_urls'])}\n\n"
                
                # Show first 20 URLs
                        txt_content += f"  • {url.get('url', str(url))}\n"
                        txt_content += f"  • {url}\n"
                
                    txt_content += f"  ... and {len(spider_data['discovered_urls']) - 20} more URLs\n"

        # Add SmartList results with enhanced port-based organization
            smartlist_data = data['smartlist']
            txt_content += f"""\n{'=' * 80}
{'=' * 80}

"""
            
                # Group recommendations by port
                port_groups = {}
                    service_id = service_rec.get('service', 'unknown:unknown')
                        port = service_id.split(':')[1]
                        service_name = service_rec.get('service_name', 'unknown')
                        port_key = f"{port}/{service_name}"
                        
                            port_groups[port_key] = []
                
                txt_content += f"Total Services Analyzed: {len(smartlist_data['wordlist_recommendations'])}\n"
                txt_content += f"Ports with Recommendations: {len(port_groups)}\n\n"
                
                # Display recommendations grouped by port
                    port_num, service_name = port_key.split('/', 1)
                    txt_content += f"{'=' * 60}\n"
                    txt_content += f"PORT {port_num}/tcp - {service_name.title()} Service\n"
                    txt_content += f"{'=' * 60}\n\n"
                    
                        txt_content += f"Target: {service_rec.get('service', 'Unknown')}\n"
                            txt_content += f"Technology: {service_rec['detected_technology']}\n"
                        txt_content += f"Overall Confidence: {service_rec.get('confidence', 'Unknown').upper()}\n\n"
                        
                            txt_content += f"PRIORITY WORDLIST RECOMMENDATIONS:\n"
                            txt_content += f"{'-' * 50}\n\n"
                            
                            # Sort wordlists by score (highest first)
                            wordlists = sorted(service_rec['top_wordlists'], 
                                             key=lambda x: x.get('score', 0), reverse=True)
                            
                                score = wl.get('score', 0)
                                confidence = wl.get('confidence', 'low')
                                
                                # Determine priority level
                                if score >= 80 or confidence == 'high':
                                    priority = "CRITICAL"
                                elif score >= 60:
                                    priority = "HIGH"
                                elif score >= 40:
                                    priority = "MEDIUM"
                                    priority = "LOW"
                                
                                txt_content += f"{priority}: {wl.get('wordlist', 'N/A')} (Score: {score})\n"
                                
                                # Add path information
                                    txt_content += f"  📁 Path: {wl['path']}\n"
                                    txt_content += f"  📁 Path: [Check /usr/share/seclists/ for {wl.get('wordlist', 'file')}]\n"
                                
                                    txt_content += f"  🎯 Reason: {wl['reason']}\n"
                                
                                if wl.get('category') and wl['category'] != 'none':
                                    txt_content += f"  📂 Category: {wl['category']}\n"
                                
                                txt_content += "\n"
                            
                            # Add usage notes for this service
                                txt_content += "⚠️  WARNING: Generic fallback was used - consider manual verification\n\n"
                            txt_content += "No specific wordlist recommendations available for this service.\n\n"
                    
                    txt_content += "\n"
                
                # Add overall usage notes
                txt_content += f"{'-' * 80}\n"
                txt_content += "💡 USAGE NOTES:\n"
                txt_content += "• Use CRITICAL and HIGH priority wordlists first for maximum efficiency\n"
                txt_content += "• Paths shown are for SecLists installation - adjust for your environment\n"
                txt_content += "• Combine multiple wordlists for comprehensive coverage\n"
                txt_content += "• Consider service-specific context when selecting wordlists\n\n"

        txt_content += f"""\n{'=' * 80}
{'=' * 80}


{'=' * 80}
"""
        
            with open(output_path, 'w', encoding='utf-8') as f:
            console.success(f"Generated simple master TXT report: {output_path}", internal=True)
            console.error(f"Failed to generate simple master TXT report: {e}", internal=True)
