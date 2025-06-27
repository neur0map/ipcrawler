from ipcrawler.plugins import ServiceScan
from shutil import which


class OracleTNScmd(ServiceScan):

    def __init__(self):
        super().__init__()
        self.name = "Oracle TNScmd"
        self.tags = ['default', 'safe', 'databases']

    def configure(self):
        self.match_service_name('^oracle')

    def check(self):
        import platform
        is_macos = platform.system() == 'Darwin'

        if which('tnscmd10g') is None:
            if is_macos:
                self.warn('tnscmd10g not available on macOS. '
                          'Using nmap Oracle TNS scripts as alternative.')
                return True
            else:
                self.error('The tnscmd10g program could not be found. '
                           'Make sure it is installed. '
                           '(On Kali, run: sudo apt install tnscmd10g)')
                return False
        return True

    async def run(self, service):
        if service.target.ipversion == 'IPv4':
            from shutil import which
            import platform
            is_macos = platform.system() == 'Darwin'

            if which('tnscmd10g') is not None:
                await service.execute(
                    'tnscmd10g ping -h {address} -p {port} 2>&1',
                    outfile='{protocol}_{port}_oracle_tnscmd_ping.txt')
                await service.execute(
                    'tnscmd10g version -h {address} -p {port} 2>&1',
                    outfile='{protocol}_{port}_oracle_tnscmd_version.txt')
            elif is_macos:
                # macOS-compatible Oracle TNS enumeration using nmap scripts
                await service.execute(
                    'nmap -T5 --min-rate=5000 --max-rate=10000 -p {port} --script '
                    'oracle-tns-version,oracle-sid-brute {address} 2>&1',
                    outfile='{protocol}_{port}_oracle_tns_nmap.txt')
                # Basic connectivity test
                await service.execute(
                    'nmap -T5 --min-rate=5000 --max-rate=10000 -p {port} -sV {address} 2>&1',
                    outfile='{protocol}_{port}_oracle_version.txt')
