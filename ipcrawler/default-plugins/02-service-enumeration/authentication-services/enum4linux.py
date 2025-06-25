from ipcrawler.plugins import ServiceScan
from shutil import which


class Enum4Linux(ServiceScan):

    def __init__(self):
        super().__init__()
        self.name = "Enum4Linux"
        self.description = "SMB/CIFS enumeration for Windows and Linux systems"
        self.tags = ['default', 'safe', 'active-directory']

    def configure(self):
        default_tool = ('enum4linux-ng' if which('enum4linux-ng')
                        else 'enum4linux')
        self.add_choice_option(
            'tool', default=default_tool,
            choices=['enum4linux-ng', 'enum4linux'],
            help='The tool to use for doing Windows and Samba enumeration. '
                 'Default: %(default)s')
        self.match_service_name([r'^ldap', r'^smb', r'^microsoft\-ds',
                                 r'^netbios'])
        self.match_port('tcp', [139, 389, 445])
        self.match_port('udp', 137)
        self.run_once(True)

    def check(self):
        tool = self.get_option('tool')

        # macOS compatibility - use nmap scripts as fallback
        import platform
        is_macos = platform.system() == 'Darwin'

        if tool == 'enum4linux' and which('enum4linux') is None:
            if is_macos:
                self.warn('enum4linux not available on macOS. '
                          'Using nmap SMB scripts as alternative.')
                # Don't add duplicate option - just update the internal state
                # The option was already added in configure()
                return True
            else:
                self.error('The enum4linux program could not be found. '
                           'Make sure it is installed. '
                           '(On Kali, run: sudo apt install enum4linux)')
                return False
        elif tool == 'enum4linux-ng' and which('enum4linux-ng') is None:
            if is_macos:
                self.warn('enum4linux-ng not available on macOS. '
                          'Using nmap SMB scripts as alternative.')
                # Don't add duplicate option - just update the internal state
                # The option was already added in configure()
                return True
            else:
                self.error('The enum4linux-ng program could not be found. '
                           'Make sure it is installed. '
                           '(https://github.com/cddmp/enum4linux-ng)')
                return False

        return True

    async def run(self, service):
        if service.target.ipversion == 'IPv4':
            tool = self.get_option('tool')
            if tool is not None:
                if tool == 'enum4linux':
                    await service.execute(
                        'enum4linux -a -M -l -d {address} 2>&1',
                        outfile='enum4linux.txt')
                elif tool == 'enum4linux-ng':
                    await service.execute(
                        'enum4linux-ng -A -d -v {address} 2>&1',
                        outfile='enum4linux-ng.txt')
                elif tool == 'nmap-smb':
                    # macOS-compatible SMB enumeration using nmap scripts
                    await service.execute(
                        'nmap -sS -O -p {port} --script '
                        'smb-enum-users,smb-enum-shares,smb-os-discovery,'
                        'smb-security-mode {address} 2>&1',
                        outfile='nmap_smb_enum.txt')
                    # Additional SMB vulnerability checks
                    await service.execute(
                        'nmap -p {port} --script smb-vuln-* {address} 2>&1',
                        outfile='nmap_smb_vulns.txt')
                    # NetBIOS enumeration if port 137/139
                    if service.port in [137, 139]:
                        await service.execute(
                            'nmap -sU -p 137 --script nbstat {address} 2>&1',
                            outfile='nmap_netbios.txt')
