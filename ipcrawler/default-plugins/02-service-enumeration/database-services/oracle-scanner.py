from ipcrawler.plugins import ServiceScan
from shutil import which


class OracleScanner(ServiceScan):

    def __init__(self):
        super().__init__()
        self.name = "Oracle Scanner"
        self.tags = ['default', 'safe', 'databases']

    def configure(self):
        self.match_service_name('^oracle')

    def check(self):
        import platform
        is_macos = platform.system() == 'Darwin'

        if which('oscanner') is None:
            if is_macos:
                self.warn('oscanner not available on macOS. '
                          'Using nmap Oracle scripts as alternative.')
                return True
            else:
                self.error('The oscanner program could not be found. '
                           'Make sure it is installed. '
                           '(On Kali, run: sudo apt install oscanner)')
                return False
        return True

    async def run(self, service):
        from shutil import which
        import platform
        is_macos = platform.system() == 'Darwin'

        if which('oscanner') is not None:
            await service.execute(
                'oscanner -v -s {address} -P {port} 2>&1',
                outfile='{protocol}_{port}_oracle_scanner.txt')
        elif is_macos:
            # macOS-compatible Oracle enumeration using nmap scripts
            await service.execute(
                'nmap -T5 --min-rate=5000 --max-rate=10000 -p {port} --script '
                'oracle-enum-users,oracle-sid-brute,oracle-tns-version '
                '{address} 2>&1',
                outfile='{protocol}_{port}_oracle_nmap.txt')
            # Additional Oracle checks
            await service.execute(
                'nmap -T5 --min-rate=5000 --max-rate=10000 -p {port} --script oracle-* {address} 2>&1',
                outfile='{protocol}_{port}_oracle_full.txt')
