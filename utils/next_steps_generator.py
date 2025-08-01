#!/usr/bin/env python3
"""
Next Steps Generator for IPCrawler

Analyzes scan results and generates actionable next-steps commands
tailored to discovered services, technologies, and vulnerabilities.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CommandRecommendation:
    """Individual command recommendation"""
    category: str           # e.g., "Web Fuzzing", "Vulnerability Scanning"
    tool: str              # e.g., "feroxbuster", "nuclei"
    command: str           # Full command to execute
    description: str       # Human-readable description
    priority: int
    confidence: str
    reasoning: str
    prerequisites: List[str] = None
    estimated_time: str = "Unknown"
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []


class NextStepsGenerator:
    """Generates comprehensive next-steps commands based on IPCrawler results"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.scan_results = {}
        self.smartlist_results = {}
        self.http_results = {}
        self.port_database = None
        self.commands = []
        self.target = ""
        self.discovered_hostnames = []
        self.detected_technologies = set()
        self.open_ports = []
        self.high_value_services = []
        
    def load_scan_results(self) -> bool:
        """Load all available scan results from workspace"""
        try:
            results_file = self.workspace_path / "scan_results.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    self.scan_results = json.load(f)
                    self._extract_basic_info()
            
            if 'smartlist_04' in self.scan_results:
                self.smartlist_results = self.scan_results['smartlist_04']
                self._extract_smartlist_info()
            
            if 'http_03' in self.scan_results:
                self.http_results = self.scan_results['http_03']
                self._extract_http_info()
                self._extract_hostname_info()
                
            return True
            
        except Exception as e:
            print(f"Error loading scan results: {e}")
            return False
    
    def _extract_basic_info(self):
        """Extract basic target and port information"""
        # Try to extract target from SmartList data first
        if 'smartlist_04' in self.scan_results:
            smartlist_data = self.scan_results['smartlist_04']
            self.target = smartlist_data.get('target', '')
            
            # Extract services from SmartList recommendations
            recommendations = smartlist_data.get('wordlist_recommendations', [])
            for service_rec in recommendations:
                service_str = service_rec.get('service', '')
                if ':' in service_str:
                    try:
                        host, port_str = service_str.split(':', 1)
                        port = int(port_str)
                        
                        # Update target if not already set
                        if not self.target and host:
                            self.target = host
                        
                        port_data = {
                            'port': port,
                            'protocol': 'tcp',
                            'service': service_rec.get('service_name', 'unknown'),
                            'version': '',
                            'product': ''
                        }
                        self.open_ports.append(port_data)
                        
                        # Identify high-value services
                        if self._is_high_value_service(port_data):
                            self.high_value_services.append(port_data)
                    except ValueError:
                        # Skip malformed service strings
                        continue
        
        # Fallback to nmap data if available
        if 'nmap_02' in self.scan_results and not self.target:
            nmap_data = self.scan_results['nmap_02']
            hosts = nmap_data.get('hosts', [])
            
            if hosts:
                host = hosts[0]  # Primary target
                self.target = host.get('ip', '')
                
                # Extract open ports and services
                for port_info in host.get('ports', []):
                    if port_info.get('state') == 'open':
                        port_data = {
                            'port': port_info.get('port'),
                            'protocol': port_info.get('protocol', 'tcp'),
                            'service': port_info.get('service', 'unknown'),
                            'version': port_info.get('version', ''),
                            'product': port_info.get('product', '')
                        }
                        self.open_ports.append(port_data)
                        
                        # Identify high-value services
                        if self._is_high_value_service(port_data):
                            self.high_value_services.append(port_data)
    
    def _extract_smartlist_info(self):
        """Extract SmartList recommendations and technologies"""
        recommendations = self.smartlist_results.get('wordlist_recommendations', [])
        
        for service_rec in recommendations:
            tech = service_rec.get('detected_technology')
            if tech and tech != 'Unknown' and tech.lower() != 'none':
                self.detected_technologies.add(tech.lower())
            
            # Also extract from service name
            service_name = service_rec.get('service_name', '')
            if service_name and service_name.lower() not in ['unknown', 'none']:
                self.detected_technologies.add(service_name.lower())
    
    def _extract_http_info(self):
        """Extract HTTP service information and technologies"""
        services = self.http_results.get('services', [])
        
        for service in services:
            technologies = service.get('technologies', [])
            for tech in technologies:
                if tech:
                    self.detected_technologies.add(tech.lower())
                    
    def _extract_hostname_info(self):
        """Extract discovered hostnames from HTTP scan results"""
        tested_hostnames = self.http_results.get('tested_hostnames', [])
        
        for hostname in tested_hostnames:
            if (hostname and 
                not hostname.replace('.', '').isdigit() and
                '.' in hostname and
                hostname != self.target):
                self.discovered_hostnames.append(hostname)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_hostnames = []
        for hostname in self.discovered_hostnames:
            if hostname not in seen:
                seen.add(hostname)
                unique_hostnames.append(hostname)
        self.discovered_hostnames = unique_hostnames[:5]
    
    def _is_high_value_service(self, port_data: Dict) -> bool:
        """Determine if a service is high-value for penetration testing"""
        high_value_ports = {
            21: 'ftp',
            22: 'ssh', 
            23: 'telnet',
            25: 'smtp',
            53: 'dns',
            80: 'http',
            110: 'pop3',
            135: 'msrpc',
            139: 'netbios',
            143: 'imap',
            389: 'ldap',
            443: 'https',
            445: 'smb',
            993: 'imaps',
            995: 'pop3s',
            88: 'kerberos',
            135: 'msrpc',
            389: 'ldap',
            636: 'ldaps',
            1433: 'mssql',
            1521: 'oracle',
            3268: 'globalcatalog',
            3269: 'globalcatalog-ssl',
            3306: 'mysql',
            3389: 'rdp',
            5432: 'postgresql',
            5985: 'winrm',
            5986: 'winrm-ssl',
            6379: 'redis',
            8080: 'http-alt',
            8443: 'https-alt',
            27017: 'mongodb'
        }
        
        port = port_data.get('port')
        service = port_data.get('service', '').lower()
        
        return (port in high_value_ports or 
                'http' in service or 
                'sql' in service or
                'ssh' in service or
                'ftp' in service or
                'smb' in service or
                'ldap' in service or
                'kerberos' in service or
                'ntlm' in service or
                'winrm' in service or
                'globalcatalog' in service)
    
    def generate_commands(self) -> List[CommandRecommendation]:
        """Generate all next-step commands"""
        self.commands = []
        
        # Generate commands based on available data
        self._generate_web_commands()
        self._generate_windows_domain_commands()
        self._generate_service_enumeration_commands()
        self._generate_vulnerability_commands()
        self._generate_exploitation_commands()
        
        # Sort by priority and confidence
        self.commands.sort(key=lambda x: (x.priority, 
                                        0 if x.confidence == 'HIGH' else 
                                        1 if x.confidence == 'MEDIUM' else 2))
        
        return self.commands
    
    def _generate_web_commands(self):
        """Generate web application testing commands"""
        web_ports = [p for p in self.open_ports if 
                    p['port'] in [80, 443, 8080, 8443] or 
                    'http' in p['service'].lower()]
        
        if not web_ports:
            return
            
        wordlists = self._get_smartlist_wordlists()
        
        for port_data in web_ports:
            port = port_data['port']
            scheme = 'https' if port in [443, 8443] else 'http'
            
            if self.discovered_hostnames:
                target_host = self.discovered_hostnames[0]
            else:
                target_host = self.target
            
            # Build URL with proper port handling
            if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
                url = f"{scheme}://{target_host}"
            else:
                url = f"{scheme}://{target_host}:{port}"
            
            # Directory fuzzing with SmartList wordlists
            if wordlists:
                for wordlist_info in wordlists[:3]:  # Top 3 wordlists
                    wordlist_path = wordlist_info.get('path', '')
                    confidence = wordlist_info.get('confidence', 'MEDIUM')
                    reason = wordlist_info.get('reason', 'SmartList recommendation')
                    
                    if wordlist_path:
                        self.commands.append(CommandRecommendation(
                            category="Web Fuzzing",
                            tool="feroxbuster",
                            command=f"feroxbuster --url {url} --wordlist \"{wordlist_path}\" -x php,html,txt,js,asp,aspx,jsp -t 50 --depth 3 -o ferox_{wordlist_info['wordlist']}_results.txt",
                            description=f"Smart directory fuzzing on {url}",
                            priority=1,
                            confidence=confidence,
                            reasoning=f"SmartList recommendation: {reason}",
                            prerequisites=["feroxbuster"],
                            estimated_time="2-10 minutes"
                        ))
            
            # Technology-specific commands
            self._add_tech_specific_commands(url, port_data)
            
            # General web enumeration
            self.commands.append(CommandRecommendation(
                category="Web Enumeration",
                tool="nuclei",
                command=f"nuclei -u {url} -t ~/nuclei-templates/http/technologies/ -t ~/nuclei-templates/http/misconfiguration/",
                description=f"Technology detection and misconfiguration scan on {url}",
                priority=2,
                confidence="HIGH",
                reasoning="Standard web application assessment",
                prerequisites=["nuclei", "nuclei-templates"],
                estimated_time="1-3 minutes"
            ))
            
            # HTTP header analysis
            self.commands.append(CommandRecommendation(
                category="Web Enumeration", 
                tool="curl",
                command=f"curl -I {url} && curl -X OPTIONS {url} && curl -X TRACE {url}",
                description=f"HTTP header analysis and method enumeration on {url}",
                priority=3,
                confidence="MEDIUM",
                reasoning="Identify HTTP methods and headers for security assessment",
                prerequisites=["curl"],
                estimated_time="< 1 minute"
            ))
    
    def _add_tech_specific_commands(self, url: str, port_data: Dict):
        """Add technology-specific testing commands"""
        
        # WordPress detection and enumeration
        if 'wordpress' in self.detected_technologies or 'wp' in str(self.detected_technologies):
            self.commands.append(CommandRecommendation(
                category="CMS Testing",
                tool="wpscan",
                command=f"wpscan --url {url} --enumerate ap,at,cb,dbe --plugins-detection aggressive",
                description=f"WordPress vulnerability scan on {url}",
                priority=1,
                confidence="HIGH",
                reasoning="WordPress detected - comprehensive security assessment needed",
                prerequisites=["wpscan"],
                estimated_time="5-15 minutes"
            ))
        
        # PHP-specific testing
        if 'php' in self.detected_technologies:
            self.commands.append(CommandRecommendation(
                category="Web Fuzzing",
                tool="gobuster",
                command=f"gobuster dir -u {url} -w /usr/share/seclists/Discovery/Web-Content/PHP.fuzz.txt -x php -b 301,302,403 -o gobuster_php_results.txt",
                description=f"PHP-specific path and file fuzzing on {url}",
                priority=2,
                confidence="HIGH", 
                reasoning="PHP technology detected - look for PHP-specific vulnerabilities",
                prerequisites=["gobuster", "seclists"],
                estimated_time="3-8 minutes"
            ))
        
        # JavaScript/Node.js testing
        if any(tech in self.detected_technologies for tech in ['javascript', 'node', 'express', 'react', 'angular']):
            self.commands.append(CommandRecommendation(
                category="Web Fuzzing",
                tool="feroxbuster",
                command=f"feroxbuster --url {url} -x js,json -w /usr/share/seclists/Discovery/Web-Content/api/api-endpoints.txt -o ferox_api_results.txt",
                description=f"JavaScript/API endpoint discovery on {url}",
                priority=2,
                confidence="HIGH",
                reasoning="JavaScript framework detected - look for API endpoints and JS files",
                prerequisites=["feroxbuster", "seclists"],
                estimated_time="2-5 minutes"
            ))
    
    def _generate_windows_domain_commands(self):
        """Generate Windows domain enumeration commands"""
        
        # Identify Windows domain services
        domain_ports = []
        has_kerberos = False
        has_ldap = False
        has_smb = False
        has_gc = False
        
        for port_data in self.open_ports:
            port = port_data['port']
            service = port_data['service'].lower()
            
            if port == 88 or 'kerberos' in service:
                domain_ports.append(port_data)
                has_kerberos = True
            elif port in [389, 636] or 'ldap' in service:
                domain_ports.append(port_data)
                has_ldap = True
            elif port in [139, 445] or 'smb' in service or 'netbios' in service:
                domain_ports.append(port_data)
                has_smb = True
            elif port in [3268, 3269] or 'globalcatalog' in service:
                domain_ports.append(port_data)
                has_gc = True
        
        # Only generate Windows domain commands if we have relevant services
        if not domain_ports:
            return
        
        # Kerberos enumeration commands
        if has_kerberos:
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="kerbrute",
                command=f"kerbrute userenum --dc {self.target} /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt",
                description=f"Kerberos user enumeration on {self.target}",
                priority=1,
                confidence="HIGH",
                reasoning="Kerberos service detected - enumerate valid domain users",
                prerequisites=["kerbrute", "seclists"],
                estimated_time="5-15 minutes"
            ))
            
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="GetNPUsers.py",
                command=f"python3 /opt/impacket/examples/GetNPUsers.py {self.target}/ -usersfile users.txt -format hashcat -outputfile asrep_hashes.txt -dc-ip {self.target}",
                description=f"ASREPRoast attack against {self.target}",
                priority=2,
                confidence="MEDIUM",
                reasoning="Kerberos detected - attempt ASREPRoast for users without Kerberos pre-authentication",
                prerequisites=["impacket", "users.txt"],
                estimated_time="2-10 minutes"
            ))
        
        # LDAP enumeration commands
        if has_ldap:
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="ldapsearch",
                command=f"ldapsearch -x -h {self.target} -s base namingcontexts",
                description=f"LDAP anonymous bind test on {self.target}",
                priority=1,
                confidence="HIGH",
                reasoning="LDAP service detected - test for anonymous bind and enumerate naming contexts",
                prerequisites=["ldap-utils"],
                estimated_time="1-2 minutes"
            ))
            
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="ldapdomaindump",
                command=f"ldapdomaindump -u 'guest' -p '' {self.target}",
                description=f"LDAP domain dump from {self.target}",
                priority=2,
                confidence="MEDIUM",
                reasoning="LDAP detected - attempt to dump domain information using guest account",
                prerequisites=["ldapdomaindump"],
                estimated_time="3-10 minutes"
            ))
        
        # Global Catalog enumeration
        if has_gc:
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="ldapsearch",
                command=f"ldapsearch -x -h {self.target} -p 3268 -s base '(objectClass=*)' namingcontexts",
                description=f"Global Catalog enumeration on {self.target}:3268",
                priority=2,
                confidence="HIGH",
                reasoning="Global Catalog service detected - enumerate forest-wide directory information",
                prerequisites=["ldap-utils"],
                estimated_time="2-5 minutes"
            ))
        
        # SMB/NetBIOS enumeration for domain context
        if has_smb and (has_kerberos or has_ldap):
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="crackmapexec",
                command=f"crackmapexec smb {self.target} --shares",
                description=f"SMB share enumeration on domain controller {self.target}",
                priority=1,
                confidence="HIGH",
                reasoning="SMB and domain services detected - enumerate domain controller shares",
                prerequisites=["crackmapexec"],
                estimated_time="1-3 minutes"
            ))
            
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="smbclient",
                command=f"smbclient -L {self.target} -N",
                description=f"List SMB shares on domain controller {self.target}",
                priority=1,
                confidence="HIGH",
                reasoning="Domain controller detected - check for SYSVOL, NETLOGON and other domain shares",
                prerequisites=["smbclient"],
                estimated_time="1-2 minutes"
            ))
        
        # Comprehensive domain enumeration if multiple services detected
        if sum([has_kerberos, has_ldap, has_smb, has_gc]) >= 2:
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="enum4linux",
                command=f"enum4linux -a {self.target}",
                description=f"Comprehensive domain enumeration on {self.target}",
                priority=1,
                confidence="HIGH",
                reasoning="Multiple domain services detected - perform comprehensive Active Directory enumeration",
                prerequisites=["enum4linux"],
                estimated_time="5-15 minutes"
            ))
            
            self.commands.append(CommandRecommendation(
                category="Windows Domain Enumeration",
                tool="bloodhound",
                command=f"python3 /opt/BloodHound.py/bloodhound.py -d domain.local -u guest -p '' -gc {self.target} -c all",
                description=f"BloodHound data collection from {self.target}",
                priority=2,
                confidence="MEDIUM",
                reasoning="Domain controller detected - collect BloodHound data for privilege escalation paths",
                prerequisites=["bloodhound.py"],
                estimated_time="10-30 minutes"
            ))
    
    def _generate_service_enumeration_commands(self):
        """Generate service-specific enumeration commands"""
        
        for port_data in self.high_value_services:
            port = port_data['port']
            service = port_data['service'].lower()
            
            # SSH enumeration
            if port == 22 or 'ssh' in service:
                self.commands.append(CommandRecommendation(
                    category="Service Enumeration",
                    tool="nmap",
                    command=f"nmap -p22 --script ssh-auth-methods,ssh-hostkey,ssh-run {self.target}",
                    description=f"SSH service enumeration on {self.target}:22",
                    priority=2,
                    confidence="HIGH",
                    reasoning="SSH service detected - enumerate auth methods and host keys",
                    prerequisites=["nmap"],
                    estimated_time="1-2 minutes"
                ))
            
            # SMB enumeration
            if port in [139, 445] or 'smb' in service or 'netbios' in service:
                self.commands.append(CommandRecommendation(
                    category="Service Enumeration", 
                    tool="enum4linux",
                    command=f"enum4linux -a {self.target}",
                    description=f"SMB/NetBIOS enumeration on {self.target}",
                    priority=1,
                    confidence="HIGH",
                    reasoning="SMB service detected - enumerate shares, users, and system info",
                    prerequisites=["enum4linux"],
                    estimated_time="2-5 minutes"
                ))
                
                self.commands.append(CommandRecommendation(
                    category="Service Enumeration",
                    tool="smbclient",
                    command=f"smbclient -L {self.target} -N && smbmap -H {self.target}",
                    description=f"SMB share enumeration on {self.target}",
                    priority=1,
                    confidence="HIGH",
                    reasoning="SMB service detected - list and map accessible shares",
                    prerequisites=["smbclient", "smbmap"],
                    estimated_time="1-3 minutes"
                ))
            
            # Database enumeration
            if any(db in service for db in ['mysql', 'postgresql', 'mssql', 'oracle', 'mongodb']):
                self._add_database_commands(port_data)
            
            # FTP enumeration
            if port == 21 or 'ftp' in service:
                self.commands.append(CommandRecommendation(
                    category="Service Enumeration",
                    tool="nmap",
                    command=f"nmap -p21 --script ftp-anon,ftp-bounce,ftp-libopie,ftp-proftpd-backdoor,ftp-vsftpd-backdoor {self.target}",
                    description=f"FTP service enumeration on {self.target}:21",
                    priority=2,
                    confidence="HIGH",
                    reasoning="FTP service detected - check for anonymous access and vulnerabilities",
                    prerequisites=["nmap"],
                    estimated_time="1-2 minutes"
                ))
    
    def _add_database_commands(self, port_data: Dict):
        """Add database-specific enumeration commands"""
        port = port_data['port']
        service = port_data['service'].lower()
        
        if 'mysql' in service or port == 3306:
            self.commands.append(CommandRecommendation(
                category="Database Enumeration",
                tool="nmap",
                command=f"nmap -p3306 --script mysql-audit,mysql-databases,mysql-dump-hashes,mysql-empty-password,mysql-enum,mysql-info,mysql-query,mysql-users,mysql-variables,mysql-vuln-cve2012-2122 {self.target}",
                description=f"MySQL enumeration and vulnerability scan on {self.target}:3306",
                priority=1,
                confidence="HIGH",
                reasoning="MySQL service detected - comprehensive database assessment",
                prerequisites=["nmap"],
                estimated_time="2-5 minutes"
            ))
        
        elif 'postgresql' in service or port == 5432:
            self.commands.append(CommandRecommendation(
                category="Database Enumeration",
                tool="nmap",
                command=f"nmap -p5432 --script pgsql-brute {self.target}",
                description=f"PostgreSQL enumeration on {self.target}:5432",
                priority=1,
                confidence="HIGH",
                reasoning="PostgreSQL service detected - database security assessment",
                prerequisites=["nmap"],
                estimated_time="1-3 minutes"
            ))
        
        elif 'mongodb' in service or port == 27017:
            self.commands.append(CommandRecommendation(
                category="Database Enumeration",
                tool="nmap",
                command=f"nmap -p27017 --script mongodb-databases,mongodb-info {self.target}",
                description=f"MongoDB enumeration on {self.target}:27017",
                priority=1,
                confidence="HIGH",
                reasoning="MongoDB service detected - check for unauthorized access",
                prerequisites=["nmap"],
                estimated_time="1-2 minutes"
            ))
    
    def _generate_vulnerability_commands(self):
        """Generate vulnerability assessment commands"""
        
        # Always add general vulnerability scans even if no specific ports found
        if self.open_ports:
            port_list = ",".join([str(p['port']) for p in self.open_ports])
        else:
            port_list = "80,443,22,21,25,53,110,143,993,995,587,465"
        
        target = self.target if self.target else "TARGET"
        
        self.commands.append(CommandRecommendation(
            category="Vulnerability Assessment",
            tool="nuclei",
            command=f"nuclei -u {target} -p {port_list} -t ~/nuclei-templates/cves/ -severity critical,high,medium",
            description=f"CVE-based vulnerability scan on {target}",
            priority=1,
            confidence="HIGH",
            reasoning="Comprehensive vulnerability assessment for discovered services",
            prerequisites=["nuclei", "nuclei-templates"],
            estimated_time="5-15 minutes"
        ))
        
        # Service-specific vulnerability scans
        self.commands.append(CommandRecommendation(
            category="Vulnerability Assessment",
            tool="nmap",
            command=f"nmap -p{port_list} --script vuln {target}",
            description=f"Nmap vulnerability scripts on discovered ports",
            priority=2,
            confidence="HIGH",
            reasoning="Use nmap's vulnerability detection scripts on open ports",
            prerequisites=["nmap"],
            estimated_time="3-10 minutes"
        ))
    
    def _generate_exploitation_commands(self):
        """Generate exploitation and post-exploitation commands"""
        
        # Only add exploitation commands for high-value services
        if not self.high_value_services:
            return
            
        # Metasploit search suggestions
        for port_data in self.high_value_services[:3]:  # Top 3 services
            service = port_data['service']
            version = port_data.get('version', '')
            product = port_data.get('product', '')
            
            search_term = f"{service} {product} {version}".strip()
            
            self.commands.append(CommandRecommendation(
                category="Exploitation Research",
                tool="msfconsole",
                command=f"msfconsole -q -x 'search {search_term}; exit'",
                description=f"Search Metasploit modules for {service} service",
                priority=4,
                confidence="MEDIUM",
                reasoning=f"Look for known exploits for {service} service",
                prerequisites=["metasploit-framework"],
                estimated_time="< 1 minute"
            ))
        
        # Searchsploit suggestions
        if any('apache' in tech or 'nginx' in tech for tech in self.detected_technologies):
            self.commands.append(CommandRecommendation(
                category="Exploitation Research",
                tool="searchsploit",
                command=f"searchsploit apache nginx | grep -E '(Remote|Local|Buffer|SQL|XSS)'",
                description="Search for web server exploits",
                priority=4,
                confidence="MEDIUM", 
                reasoning="Web server detected - search for known exploits",
                prerequisites=["exploitdb"],
                estimated_time="< 1 minute"
            ))
    
    def _get_smartlist_wordlists(self) -> List[Dict]:
        """Extract wordlist recommendations from SmartList results"""
        wordlists = []
        
        recommendations = self.smartlist_results.get('wordlist_recommendations', [])
        for service_rec in recommendations:
            top_wordlists = service_rec.get('top_wordlists', [])
            for wl in top_wordlists:
                if wl.get('path'):  # Only include wordlists with full paths
                    wordlists.append(wl)
        
        # Sort by confidence and score
        def sort_key(wl):
            conf_score = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}.get(wl.get('confidence', 'LOW'), 1)
            return (conf_score, wl.get('score', 0))
        
        wordlists.sort(key=sort_key, reverse=True)
        return wordlists
    
    def _check_tool_availability(self, tool: str) -> bool:
        """Check if a tool is available on the system"""
        return shutil.which(tool) is not None
    
    def save_next_steps(self) -> Path:
        """Save next-steps commands to a file"""
        output_file = self.workspace_path / "next-steps.txt"
        
        try:
            with open(output_file, 'w') as f:
                f.write("# IPCrawler Next Steps\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Target: {self.target}\n")
                if self.discovered_hostnames:
                    f.write(f"# Discovered Hostnames: {', '.join(self.discovered_hostnames)}\n")
                    f.write(f"# Using hostname-based commands for better enumeration\n")
                f.write(f"# Open Ports: {len(self.open_ports)}\n")
                f.write(f"# Detected Technologies: {', '.join(sorted(self.detected_technologies)) if self.detected_technologies else 'None'}\n")
                f.write("\n# Copy and paste these commands for your next testing phase\n")
                f.write("# Commands are ordered by priority and confidence\n\n")
                
                current_category = ""
                priority_labels = {1: "🔥 CRITICAL", 2: "⚡ HIGH", 3: "📊 MEDIUM", 4: "🔍 LOW", 5: "💡 OPTIONAL"}
                
                for i, cmd in enumerate(self.commands, 1):
                    # Add category header
                    if cmd.category != current_category:
                        current_category = cmd.category
                        f.write(f"\n{'='*60}\n")
                        f.write(f"# {current_category.upper()}\n")
                        f.write(f"{'='*60}\n\n")
                    
                    # Add command details
                    priority_label = priority_labels.get(cmd.priority, "❓ UNKNOWN")
                    f.write(f"# {i}. {cmd.description}\n")
                    f.write(f"# Priority: {priority_label} | Confidence: {cmd.confidence} | Tool: {cmd.tool}\n")
                    f.write(f"# Reasoning: {cmd.reasoning}\n")
                    f.write(f"# Estimated Time: {cmd.estimated_time}\n")
                    
                    # Check tool availability
                    missing_tools = [tool for tool in cmd.prerequisites if not self._check_tool_availability(tool)]
                    if missing_tools:
                        f.write(f"# ⚠️  Missing Tools: {', '.join(missing_tools)}\n")
                        f.write(f"# Install with: apt install {' '.join(missing_tools)} (or brew/yum)\n")
                    
                    f.write(f"\n{cmd.command}\n\n")
                
                # Add general recommendations
                f.write(f"\n{'='*60}\n")
                f.write("# GENERAL RECOMMENDATIONS\n")
                f.write(f"{'='*60}\n\n")
                
                f.write("# 1. Always verify scope and authorization before testing\n")
                f.write("# 2. Take screenshots and notes of all findings\n")
                f.write("# 3. Test during approved timeframes\n")
                f.write("# 4. Use rate limiting to avoid DoS\n")
                f.write("# 5. Keep detailed logs for reporting\n\n")
                
                f.write("# For more advanced techniques, check:\n")
                f.write("# - OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/\n")
                f.write("# - HackTricks: https://book.hacktricks.xyz/\n")
                f.write("# - PayloadsAllTheThings: https://github.com/swisskyrepo/PayloadsAllTheThings\n")
            
            return output_file
            
        except Exception as e:
            print(f"Error saving next-steps file: {e}")
            return None


def generate_next_steps(workspace_path: Path) -> Optional[Path]:
    """Main function to generate next-steps.txt file"""
    generator = NextStepsGenerator(workspace_path)
    
    if not generator.load_scan_results():
        return None
    
    generator.generate_commands()
    return generator.save_next_steps()