import asyncio
import os
import time
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Tuple

from workflows.core.base import BaseWorkflow, WorkflowResult
from workflows.core.output_cleaner import OutputCleaner
from workflows.nmap_02.models import NmapScanResult, NmapHost, NmapPort
from config import config


class NmapScanner(BaseWorkflow):
    """Nmap scanner workflow implementation"""
    
    def __init__(self, batch_size: int = 10, ports_per_batch: int = 6553):
        super().__init__("nmap")
        self.batch_size = batch_size  # Number of concurrent nmap processes
        self.ports_per_batch = ports_per_batch  # Ports per batch (~10% of 65535)
    
    def validate_input(self, target: str, **kwargs) -> bool:
        """Validate input parameters"""
        if not target or not target.strip():
            return False
        return True
    
    def _is_root(self) -> bool:
        """Check if running with root privileges"""
        return os.geteuid() == 0
    
    def _build_nmap_command(self, is_root: bool, port_spec: str, flags: Optional[List[str]] = None) -> List[str]:
        """Build nmap command based on privileges and port specification"""
        if is_root:
            cmd = [
                "nmap",
                "-sS",     # SYN scan (requires root)
                "-sV",     # Version detection
                "-sC",     # Default scripts
                "-A",      # Aggressive scan
                "-T4",     # Aggressive timing
                f"-p{port_spec}",  # Port specification
                "--script=vuln,exploit,discovery,auth,brute",
                "-oX", "-" # Output XML to stdout
            ]
        else:
            cmd = [
                "nmap",
                "-sT",     # TCP connect scan
                "-sV",     # Version detection
                "-sC",     # Default scripts
                "-T4",     # Aggressive timing
                f"-p{port_spec}",  # Port specification
                "--script=discovery,safe",
                "-oX", "-" # Output XML to stdout
            ]
        
        if flags:
            cmd.extend(flags)
        
        return cmd
    
    def _create_port_ranges(self, total_ports: int = 65535) -> List[Tuple[int, int]]:
        """Create port ranges for parallel scanning"""
        ranges = []
        for start in range(1, total_ports + 1, self.ports_per_batch):
            end = min(start + self.ports_per_batch - 1, total_ports)
            ranges.append((start, end))
        return ranges
    
    
    async def execute(self, target: str, flags: Optional[List[str]] = None, progress_queue: Optional[asyncio.Queue] = None, ports: Optional[List[int]] = None, **kwargs) -> WorkflowResult:
        """Execute nmap scan on target"""
        start_time = time.time()
        
        if not self.validate_input(target):
            return WorkflowResult(
                success=False,
                error="Invalid target provided",
                execution_time=time.time() - start_time
            )
        
        try:
            is_root = self._is_root()
            
            # If specific ports are provided, choose scan method based on real-time setting
            if ports:
                # Use batched scanning for real-time results, single scan otherwise
                if len(ports) > 5:
                    return await self._batched_port_scan(target, ports, is_root, flags, progress_queue, start_time)
                else:
                    return await self._single_scan(target, ports, is_root, flags, start_time, progress_queue)
            else:
                # Parallel batch scanning for all ports
                return await self._parallel_scan(target, is_root, flags, progress_queue, start_time)
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                error=f"Nmap execution failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _single_scan(self, target: str, ports: List[int], is_root: bool, 
                          flags: Optional[List[str]], start_time: float,
                          progress_queue: Optional[asyncio.Queue] = None) -> WorkflowResult:
        """Execute a single nmap scan on ONLY the specific discovered ports"""
        try:
            # Create port specification from discovered ports ONLY
            port_spec = ','.join(map(str, ports))
            
            # Build nmap command
            cmd = self._build_nmap_command(is_root, port_spec, flags)
            cmd.append(target)
            
            # Execute nmap
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return WorkflowResult(
                    success=False,
                    error=f"Nmap failed: {stderr.decode()}",
                    execution_time=time.time() - start_time
                )
            
            # Parse XML output
            xml_output = stdout.decode()
            scan_result = self._parse_xml_output(xml_output, " ".join(cmd))
            
            # Add scan mode info
            scan_result_dict = scan_result.model_dump()
            scan_result_dict['scan_mode'] = '[bold green]privileged[/bold green]' if is_root else '[bold orange1]unprivileged[/bold orange1]'
            scan_result_dict['scan_type'] = 'targeted'
            
            # Send progress notification
            if progress_queue:
                await progress_queue.put("batch_complete")
            
            return WorkflowResult(
                success=True,
                data=scan_result_dict,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                error=f"Single scan failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _parallel_scan(self, target: str, is_root: bool, flags: Optional[List[str]], 
                            progress_queue: Optional[asyncio.Queue], start_time: float) -> WorkflowResult:
        """Execute parallel batch scanning for all ports"""
        try:
            # Create port ranges for all ports
            port_ranges = self._create_port_ranges()
            
            # Create semaphore to limit concurrent processes
            semaphore = asyncio.Semaphore(self.batch_size)
            
            # Create tasks for all port ranges
            tasks = []
            for start_port, end_port in port_ranges:
                task = self._scan_port_range_with_semaphore(
                    target, start_port, end_port, is_root, flags, semaphore, progress_queue
                )
                tasks.append(task)
            
            # Execute all tasks and gather results
            scan_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out errors and merge results
            successful_scans = []
            errors = []
            
            for i, result in enumerate(scan_results):
                if isinstance(result, Exception):
                    errors.append(f"Range {port_ranges[i]}: {str(result)}")
                elif result is not None:
                    successful_scans.append(result)
            
            if not successful_scans:
                return WorkflowResult(
                    success=False,
                    error=f"All scans failed. Errors: {'; '.join(errors)}",
                    execution_time=time.time() - start_time
                )
            
            # Merge all scan results
            merged_result = self._merge_scan_results(successful_scans, target, is_root)
            
            # Add scan mode info
            merged_result_dict = merged_result.model_dump()
            merged_result_dict['scan_mode'] = '[bold green]privileged[/bold green]' if is_root else '[bold orange1]unprivileged[/bold orange1]'
            merged_result_dict['parallel_scans'] = len(successful_scans)
            merged_result_dict['batch_size'] = self.batch_size
            
            return WorkflowResult(
                success=True,
                data=merged_result_dict,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                error=f"Parallel scan failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _batched_port_scan(self, target: str, ports: List[int], is_root: bool, 
                                flags: Optional[List[str]], progress_queue: Optional[asyncio.Queue], 
                                start_time: float) -> WorkflowResult:
        """Execute batched scan on specific discovered ports for real-time results"""
        try:
            # Split ports into small batches (5 ports per batch for frequent updates)
            batch_size = 5
            port_batches = []
            for i in range(0, len(ports), batch_size):
                batch = ports[i:i + batch_size]
                port_batches.append(batch)
            
            # Create semaphore to limit concurrent processes
            semaphore = asyncio.Semaphore(min(3, len(port_batches)))  # Max 3 concurrent batches
            
            # Create tasks for all port batches
            tasks = []
            for batch in port_batches:
                task = self._scan_port_batch_with_semaphore(
                    target, batch, is_root, flags, semaphore, progress_queue
                )
                tasks.append(task)
            
            # Execute all tasks and gather results
            scan_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out errors and merge results
            successful_scans = []
            errors = []
            
            for i, result in enumerate(scan_results):
                if isinstance(result, Exception):
                    errors.append(f"Batch {port_batches[i]}: {str(result)}")
                elif result is not None:
                    successful_scans.append(result)
            
            if not successful_scans:
                return WorkflowResult(
                    success=False,
                    error=f"All port scans failed. Errors: {'; '.join(errors)}",
                    execution_time=time.time() - start_time
                )
            
            # Merge all scan results
            merged_result = self._merge_scan_results(successful_scans, target, is_root)
            
            # Add scan mode info
            merged_result_dict = merged_result.model_dump()
            merged_result_dict['scan_mode'] = '[bold green]privileged[/bold green]' if is_root else '[bold orange1]unprivileged[/bold orange1]'
            merged_result_dict['scan_type'] = 'targeted_batched'
            merged_result_dict['port_batches'] = len(port_batches)
            
            return WorkflowResult(
                success=True,
                data=merged_result_dict,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                error=f"Batched port scan failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _scan_port_range_with_semaphore(
        self, target: str, start_port: int, end_port: int, 
        is_root: bool, flags: Optional[List[str]], semaphore: asyncio.Semaphore,
        progress_queue: Optional[asyncio.Queue] = None
    ) -> Optional[NmapScanResult]:
        """Scan a specific port range with semaphore control"""
        async with semaphore:
            result = await self._scan_port_range(target, start_port, end_port, is_root, flags)
            if progress_queue:
                # Send batch completion notification
                await progress_queue.put("batch_complete")
            return result
    
    async def _scan_port_batch_with_semaphore(
        self, target: str, port_batch: List[int], 
        is_root: bool, flags: Optional[List[str]], semaphore: asyncio.Semaphore,
        progress_queue: Optional[asyncio.Queue] = None
    ) -> Optional[NmapScanResult]:
        """Scan a batch of specific ports with semaphore control"""
        async with semaphore:
            result = await self._scan_specific_ports(target, port_batch, is_root, flags)
            if progress_queue:
                # Send batch completion notification
                await progress_queue.put("batch_complete")
            return result
    
    async def _scan_specific_ports(
        self, target: str, ports: List[int], 
        is_root: bool, flags: Optional[List[str]] = None
    ) -> Optional[NmapScanResult]:
        """Execute nmap scan for specific ports"""
        try:
            # Create port specification
            port_spec = ','.join(map(str, ports))
            
            # Build command for these specific ports
            cmd = self._build_nmap_command(is_root, port_spec, flags)
            cmd.append(target)
            
            # Execute nmap
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Nmap failed: {stderr.decode()}")
            
            # Parse XML output
            xml_output = stdout.decode()
            return self._parse_xml_output(xml_output, " ".join(cmd))
            
        except Exception:
            # Don't fail the entire scan if one batch fails
            return None
    
    async def _scan_port_range(
        self, target: str, start_port: int, end_port: int,
        is_root: bool, flags: Optional[List[str]] = None
    ) -> Optional[NmapScanResult]:
        """Execute nmap scan for a specific port range"""
        try:
            # Build command for this port range
            port_spec = f"{start_port}-{end_port}"
            cmd = self._build_nmap_command(is_root, port_spec, flags)
            cmd.append(target)
            
            # Execute nmap
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Nmap failed: {stderr.decode()}")
            
            # Parse XML output
            xml_output = stdout.decode()
            return self._parse_xml_output(xml_output, " ".join(cmd))
            
        except Exception:
            # Don't fail the entire scan if one range fails
            return None
    
    def _merge_scan_results(self, results: List[NmapScanResult], target: str, is_root: bool) -> NmapScanResult:
        """Merge multiple scan results into one comprehensive result"""
        # Initialize merged result
        merged_hosts: Dict[str, NmapHost] = {}
        total_duration = 0.0
        all_warnings = []
        
        # Merge results from each scan
        for result in results:
            total_duration += result.duration
            all_warnings.extend(result.warnings)
            
            # Merge hosts
            for host in result.hosts:
                if host.ip not in merged_hosts:
                    merged_hosts[host.ip] = host
                else:
                    # Merge ports from this host
                    existing_host = merged_hosts[host.ip]
                    existing_ports = {p.port: p for p in existing_host.ports}
                    
                    for port in host.ports:
                        if port.port not in existing_ports:
                            existing_host.ports.append(port)
                        else:
                            # Update with more detailed info if available
                            existing_port = existing_ports[port.port]
                            if not existing_port.service and port.service:
                                existing_port.service = port.service
                            if not existing_port.version and port.version:
                                existing_port.version = port.version
                            if port.scripts:
                                existing_port.scripts.extend(port.scripts)
                    
                    # Update OS info if better accuracy
                    if host.os and (not existing_host.os or 
                                   (host.os_accuracy or 0) > (existing_host.os_accuracy or 0)):
                        existing_host.os = host.os
                        existing_host.os_accuracy = host.os_accuracy
                        existing_host.os_details = host.os_details
        
        # Sort ports for each host
        for host in merged_hosts.values():
            host.ports.sort(key=lambda p: p.port)
        
        # Create merged result
        scan_type = "syn" if is_root else "connect"
        command = f"nmap -s{scan_type.upper()[0]} -sV -sC -T4 -p- {target} (parallel batch scan)"
        
        hosts_list = list(merged_hosts.values())
        up_hosts = sum(1 for h in hosts_list if h.state == "up")
        
        return NmapScanResult(
            command=command,
            scan_type=scan_type,
            start_time=results[0].start_time if results else "",
            end_time=results[-1].end_time if results else "",
            duration=total_duration,
            hosts=hosts_list,
            total_hosts=len(hosts_list),
            up_hosts=up_hosts,
            down_hosts=len(hosts_list) - up_hosts,
            warnings=all_warnings,
            scan_stats={"parallel_scans": len(results)}
        )
    
    def _parse_xml_output(self, xml_output: str, command: str) -> NmapScanResult:
        """Parse nmap XML output into structured data"""
        try:
            root = ET.fromstring(xml_output)
            
            # Extract scan info
            scan_info = root.find("scaninfo")
            scan_type = scan_info.get("type", "unknown") if scan_info is not None else "unknown"
            
            # Extract timing info
            start_time = root.get("startstr", "")
            nmap_version = root.get("version", "")
            scan_args = root.get("args", "")
            
            # Find runstats for end time and duration
            runstats = root.find("runstats")
            end_time = ""
            duration = 0.0
            scan_stats = {}
            
            if runstats is not None:
                finished = runstats.find("finished")
                if finished is not None:
                    end_time = finished.get("timestr", "")
                    duration = float(finished.get("elapsed", "0"))
                
                # Parse additional scan stats
                hosts_elem = runstats.find("hosts")
                if hosts_elem is not None:
                    scan_stats = {
                        "hosts_up": int(hosts_elem.get("up", "0")),
                        "hosts_down": int(hosts_elem.get("down", "0")),
                        "hosts_total": int(hosts_elem.get("total", "0"))
                    }
            
            # Parse warnings
            warnings = []
            for warning_elem in root.findall(".//warning"):
                if warning_elem.text:
                    warnings.append(warning_elem.text.strip())
            
            # Parse hosts
            hosts = []
            total_hosts = 0
            up_hosts = 0
            down_hosts = 0
            
            for host_elem in root.findall("host"):
                host = self._parse_host(host_elem)
                hosts.append(host)
                total_hosts += 1
                
                if host.state == "up":
                    up_hosts += 1
                else:
                    down_hosts += 1
            
            return NmapScanResult(
                command=command,
                scan_type=scan_type,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                hosts=hosts,
                total_hosts=total_hosts,
                up_hosts=up_hosts,
                down_hosts=down_hosts,
                nmap_version=nmap_version,
                scan_args=scan_args,
                warnings=warnings,
                scan_stats=scan_stats,
                raw_output=xml_output
            )
            
        except ET.ParseError:
            # Return minimal result if XML parsing fails
            return NmapScanResult(
                command=command,
                scan_type="unknown",
                start_time="",
                end_time="",
                duration=0.0,
                raw_output=xml_output
            )
    
    def _parse_host(self, host_elem: ET.Element) -> NmapHost:
        """Parse individual host element"""
        # Get IP address
        address_elem = host_elem.find("address[@addrtype='ipv4']")
        if address_elem is None:
            address_elem = host_elem.find("address[@addrtype='ipv6']")
        
        ip = address_elem.get("addr", "") if address_elem is not None else ""
        
        # Get hostname
        hostname = None
        hostnames = host_elem.find("hostnames")
        if hostnames is not None:
            hostname_elem = hostnames.find("hostname")
            if hostname_elem is not None:
                hostname = hostname_elem.get("name")
        
        # Get host state
        status = host_elem.find("status")
        state = status.get("state", "unknown") if status is not None else "unknown"
        
        # Get MAC address and vendor
        mac_address = None
        mac_vendor = None
        mac_elem = host_elem.find("address[@addrtype='mac']")
        if mac_elem is not None:
            mac_address = mac_elem.get("addr")
            mac_vendor = mac_elem.get("vendor")
        
        # Get OS info (enhanced)
        os_info = None
        os_accuracy = None
        os_details = []
        os_elem = host_elem.find("os")
        if os_elem is not None:
            osmatch = os_elem.find("osmatch")
            if osmatch is not None:
                os_info = osmatch.get("name")
                os_accuracy = int(osmatch.get("accuracy", "0"))
            
            # Parse all OS matches for detailed info
            for osmatch in os_elem.findall("osmatch"):
                os_details.append({
                    "name": osmatch.get("name", ""),
                    "accuracy": int(osmatch.get("accuracy", "0")),
                    "line": osmatch.get("line", ""),
                    "osclasses": [
                        {
                            "type": osclass.get("type", ""),
                            "vendor": osclass.get("vendor", ""),
                            "osfamily": osclass.get("osfamily", ""),
                            "osgen": osclass.get("osgen", ""),
                            "accuracy": int(osclass.get("accuracy", "0"))
                        }
                        for osclass in osmatch.findall("osclass")
                    ]
                })
        
        # Parse uptime
        uptime = None
        uptime_elem = host_elem.find("uptime")
        if uptime_elem is not None:
            uptime = f"{uptime_elem.get('seconds', '0')} seconds"
        
        # Parse distance
        distance = None
        distance_elem = host_elem.find("distance")
        if distance_elem is not None:
            distance = int(distance_elem.get("value", "0"))
        
        # Parse host scripts
        scripts = []
        hostscript = host_elem.find("hostscript")
        if hostscript is not None:
            for script in hostscript.findall("script"):
                script_data = {
                    "id": script.get("id", ""),
                    "output": script.get("output", ""),
                    "elements": [
                        {elem.get("key", ""): elem.text or ""} 
                        for elem in script.findall("elem")
                    ]
                }
                # Clean script output only if needed
                if config.raw_output:
                    scripts.append(script_data)
                else:
                    cleaned_script = OutputCleaner.clean_script_output(script_data, config.raw_output)
                    scripts.append(cleaned_script)
        
        # Parse traceroute
        traceroute = []
        trace = host_elem.find("trace")
        if trace is not None:
            for hop in trace.findall("hop"):
                traceroute.append({
                    "ttl": int(hop.get("ttl", "0")),
                    "ipaddr": hop.get("ipaddr", ""),
                    "rtt": hop.get("rtt", ""),
                    "host": hop.get("host", "")
                })
        
        # Parse ports
        ports = []
        ports_elem = host_elem.find("ports")
        if ports_elem is not None:
            for port_elem in ports_elem.findall("port"):
                port = self._parse_port(port_elem)
                ports.append(port)
        
        return NmapHost(
            ip=ip,
            hostname=hostname,
            state=state,
            ports=ports,
            os=os_info,
            os_accuracy=os_accuracy,
            os_details=os_details,
            mac_address=mac_address,
            mac_vendor=mac_vendor,
            scripts=scripts,
            traceroute=traceroute,
            uptime=uptime,
            distance=distance
        )
    
    def _parse_port(self, port_elem: ET.Element) -> NmapPort:
        """Parse individual port element"""
        port_num = int(port_elem.get("portid", "0"))
        protocol = port_elem.get("protocol", "tcp")
        
        # Get port state
        state_elem = port_elem.find("state")
        state = state_elem.get("state", "unknown") if state_elem is not None else "unknown"
        
        # Get service info (enhanced)
        service = None
        version = None
        product = None
        extra_info = None
        cpe = []
        
        service_elem = port_elem.find("service")
        if service_elem is not None:
            service = service_elem.get("name")
            version = service_elem.get("version")
            product = service_elem.get("product")
            extra_info = service_elem.get("extrainfo")
            
            # Parse CPE (Common Platform Enumeration) identifiers
            for cpe_elem in service_elem.findall("cpe"):
                if cpe_elem.text:
                    cpe.append(cpe_elem.text)
        
        # Parse port scripts
        scripts = []
        for script in port_elem.findall("script"):
            script_data = {
                "id": script.get("id", ""),
                "output": script.get("output", ""),
                "elements": [
                    {elem.get("key", ""): elem.text or ""} 
                    for elem in script.findall("elem")
                ]
            }
            # Clean script output only if needed
            if config.raw_output:
                scripts.append(script_data)
            else:
                cleaned_script = OutputCleaner.clean_script_output(script_data, config.raw_output)
                scripts.append(cleaned_script)
        
        return NmapPort(
            port=port_num,
            protocol=protocol,
            state=state,
            service=service,
            version=version,
            product=product,
            extra_info=extra_info,
            scripts=scripts,
            cpe=cpe
        )