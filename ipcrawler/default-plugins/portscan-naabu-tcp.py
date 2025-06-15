from ipcrawler.plugins import PortScan
from ipcrawler.config import config
import requests
import asyncio
import json
import tempfile
import os


class NaabuTCPPortScan(PortScan):
    def __init__(self):
        super().__init__()
        self.name = "Naabu TCP Ports"
        self.description = "Fast TCP port scanning using Naabu, followed by Nmap service detection on open ports."
        self.type = "tcp"
        self.tags = ["default", "default-port-scan", "safe", "quick", "naabu"]
        self.priority = 0

    def configure(self):
        self.add_option(
            "rate",
            default="1000",
            help="Packets per second rate for Naabu. Default: %(default)s"
        )
        self.add_option(
            "timeout",
            default="10",
            help="Timeout in seconds for Naabu port scan. Default: %(default)s"
        )
        self.add_true_option(
            "top-ports",
            help="Scan only top 1000 ports instead of full range. Default: %(default)s"
        )
        self.add_true_option(
            "skip-nmap",
            help="Skip Nmap service detection and only do port discovery. Default: %(default)s"
        )

    async def run(self, target):
        if target.ports:  # Don't run this plugin if there are custom ports.
            return []

        # Check if naabu is available
        if not await self._check_naabu_available(target):
            target.error("❌ Naabu not found. Please install naabu: go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest")
            return []

        # Step 1: Fast port discovery with Naabu
        open_ports = await self._run_naabu_scan(target)
        
        if not open_ports:
            target.info("🔍 No open ports found by Naabu")
            return []

        target.info(f"🎯 Naabu found {len(open_ports)} open ports: {', '.join(map(str, open_ports))}")

        # Step 2: Service detection with Nmap (unless skipped)
        if self.get_option("skip-nmap"):
            target.info("⏭️ Skipping Nmap service detection as requested")
            # Create basic service objects for open ports
            services = []
            for port in open_ports:
                from ipcrawler.targets import Service
                service = Service()
                service.address = target.address
                service.port = port
                service.protocol = "tcp"
                service.name = "unknown"
                service.secure = port in [443, 993, 995, 8443, 9443]
                services.append(service)
            return services
        else:
            return await self._run_nmap_service_detection(target, open_ports)

    async def _check_naabu_available(self, target):
        """Check if naabu is installed and available"""
        try:
            process, stdout, stderr = await target.execute("which naabu", blocking=False)
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def _run_naabu_scan(self, target):
        """Run Naabu for fast port discovery"""
        target.info("🚀 Starting fast port discovery with Naabu...")
        
        # Build Naabu command
        rate = self.get_option("rate")
        timeout = self.get_option("timeout")
        
        # Create temporary file for JSON output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Build command
            cmd_parts = [
                "naabu",
                f"-host {target.address}",
                f"-rate {rate}",
                f"-timeout {timeout}",
                "-json",
                f"-o {temp_path}",
                "-silent"
            ]

            # Add port range
            if self.get_option("top-ports"):
                cmd_parts.append("-top-ports 1000")
            else:
                cmd_parts.append("-p 1-65535")

            # Add proxy support if configured
            if config.get("proxychains"):
                cmd_parts.insert(0, "proxychains")

            naabu_cmd = " ".join(cmd_parts)
            target.info(f"🔧 Running: {naabu_cmd}")

            # Execute Naabu
            process, stdout, stderr = await target.execute(naabu_cmd, blocking=False)
            await process.wait()

            # Parse results
            open_ports = []
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                with open(temp_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                result = json.loads(line)
                                if 'port' in result:
                                    open_ports.append(int(result['port']))
                            except json.JSONDecodeError:
                                # Handle non-JSON lines
                                continue

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

            # Sort ports
            open_ports.sort()
            return open_ports

        except Exception as e:
            target.error(f"❌ Naabu scan failed: {e}")
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            return []

    async def _run_nmap_service_detection(self, target, open_ports):
        """Run Nmap service detection on discovered open ports"""
        if not open_ports:
            return []

        target.info(f"🔍 Running Nmap service detection on {len(open_ports)} open ports...")

        # Convert ports to comma-separated string
        port_list = ",".join(map(str, open_ports))

        # Build Nmap command for service detection
        if config["proxychains"]:
            traceroute_os = ""
        else:
            traceroute_os = " -A --osscan-guess"

        # Use faster timeouts since we already know ports are open
        timeout_options = " --host-timeout 5m --max-scan-delay 10s"

        # Execute Nmap service detection
        process, stdout, stderr = await target.execute(
            f"timeout 900 nmap {{nmap_extra}} -sV -sC --version-all"
            + traceroute_os
            + timeout_options
            + f' -p {port_list}'
            + ' -oN "{scandir}/_naabu_nmap_services.txt" -oX "{scandir}/xml/_naabu_nmap_services.xml" {address}',
            blocking=False,
        )

        services = await target.extract_services(stdout)
        await self._check_winrm_services(services, target)
        await process.wait()

        target.info(f"✅ Service detection complete - identified {len(services)} services")
        return services

    async def _check_winrm_services(self, services, target):
        """Check if HTTP services are actually WinRM"""
        for service in services:
            if service.name == "http" and service.port in [5985, 5986]:
                try:
                    wsman = requests.get(
                        ("https" if service.secure else "http") + "://" + target.address + ":" + str(service.port) + "/wsman",
                        verify=False,
                        timeout=10,
                    )
                    if wsman.status_code == 405:
                        service.name = "wsman"
                        wsman = requests.post(
                            ("https" if service.secure else "http") + "://" + target.address + ":" + str(service.port) + "/wsman",
                            verify=False,
                            timeout=10,
                        )
                    else:
                        if wsman.status_code == 401:
                            service.name = "wsman"
                except requests.exceptions.RequestException:
                    # If WinRM check fails, just continue with http service
                    pass 