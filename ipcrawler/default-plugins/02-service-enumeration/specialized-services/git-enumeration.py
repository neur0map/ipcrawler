from ipcrawler.plugins import ServiceScan
from ipcrawler.targets import Service
import os
import re
import json
from datetime import datetime
from shutil import which


class GitEnumeration(ServiceScan):

    def __init__(self):
        super().__init__()
        self.name = "Advanced Git Security Enumeration"
        self.slug = 'git-enumeration'
        self.description = "Comprehensive Git security assessment covering all attack vectors and misconfigurations"
        self.priority = 5  # Run after basic enumeration to check for Git indicators
        self.tags = ['default', 'safe', 'git', 'ctf', 'source-disclosure', 'secrets', 'advanced']
        
        # Add option to force Git enumeration on all HTTP/SSH services
        self.add_true_option('force-git-scan', help='Force Git enumeration on all HTTP/SSH services regardless of indicators')

    def configure(self):
        # === RESTRICTED SERVICE MATCHING ===
        
        # Only match Git daemon protocol (guaranteed Git service)
        self.match_port('tcp', 9418)
        
        # Only match known Git web interface ports
        self.match_port('tcp', 3000)  # Gitea default
        self.match_port('tcp', 8080)  # GitLab/Jenkins common
        self.match_port('tcp', 8443)  # Git web interfaces
        self.match_port('tcp', 9000)  # Gogs default
        
        # Only match confirmed Git-related services
        self.match_service_name(['git', 'git-daemon', 'gitiles', 'gitlab', 'github', 'gitea', 'gogs'])
        self.match_service_name(['cgit', 'gitweb', 'git-http-backend'])
        
        # Match SSH and HTTP services but filter them through _should_scan_service()
        self.match_service_name('ssh')
        self.match_service_name('^http')
        self.match_service_name('^nacn_http$', negative_match=True)
        
        # Add common HTTP/SSH ports that might have Git services
        self.match_port('tcp', 22)    # SSH
        self.match_port('tcp', 80)    # HTTP
        self.match_port('tcp', 443)   # HTTPS
        
        # === COMPREHENSIVE GIT SECURITY PATTERNS ===
        
        # .git directory exposure (critical vulnerability)
        self.add_pattern(r'(?i)\.git/HEAD', description='CRITICAL: Git repository HEAD file exposed - full source code disclosure')
        self.add_pattern(r'(?i)\.git/config', description='CRITICAL: Git config file exposed - may contain credentials/URLs/emails')
        self.add_pattern(r'(?i)\.git/index', description='CRITICAL: Git index file exposed - file structure and staging area disclosure')
        self.add_pattern(r'(?i)\.git/logs/HEAD', description='WARNING: Git commit logs exposed - development history and author info visible')
        self.add_pattern(r'(?i)\.git/refs/heads/', description='WARNING: Git branch references exposed - reveals branch structure')
        self.add_pattern(r'(?i)\.git/objects/', description='CRITICAL: Git objects directory exposed - complete repository reconstruction possible')
        self.add_pattern(r'(?i)\.git/packed-refs', description='WARNING: Git packed references exposed - branch/tag information')
        self.add_pattern(r'(?i)\.git/description', description='INFO: Git repository description file found')
        self.add_pattern(r'(?i)\.git/hooks/', description='WARNING: Git hooks directory exposed - may contain custom scripts')
        
        # Git configuration and credential files
        self.add_pattern(r'(?i)\.gitignore', description='INFO: .gitignore file found - may reveal sensitive file patterns and project structure')
        self.add_pattern(r'(?i)\.gitmodules', description='INFO: Git submodules configuration found - external repository dependencies')
        self.add_pattern(r'(?i)\.git-credentials', description='CRITICAL: Git credentials file exposed - contains plaintext authentication data')
        self.add_pattern(r'(?i)\.gitconfig', description='WARNING: Git user configuration exposed - user identity and settings')
        self.add_pattern(r'(?i)\.gitattributes', description='INFO: Git attributes file found - file handling rules')
        self.add_pattern(r'(?i)\.git/info/exclude', description='INFO: Git exclude patterns found - local ignore rules')
        
        # Git hosting platforms and remotes
        self.add_pattern(r'(?i)github\.com|gitlab\.com|bitbucket\.org|gitea\.io', description='INFO: Git hosting platform URL detected')
        self.add_pattern(r'(?i)git@github\.com|git@gitlab\.com|git@bitbucket\.org', description='INFO: SSH Git URL detected')
        self.add_pattern(r'(?i)https://.*\.git|http://.*\.git', description='WARNING: Git repository URL detected in HTTP traffic')
        
        # Sensitive information in Git commits/content
        self.add_pattern(r'(?i)password["\s]*[:=]["\s]*[^\s"]{3,}', description='CRITICAL: Password detected in Git content')
        self.add_pattern(r'(?i)api[_\s]*key["\s]*[:=]["\s]*[^\s"]{10,}', description='CRITICAL: API key detected in Git content')
        self.add_pattern(r'(?i)secret[_\s]*key["\s]*[:=]["\s]*[^\s"]{10,}', description='CRITICAL: Secret key detected in Git content')
        self.add_pattern(r'(?i)access[_\s]*token["\s]*[:=]["\s]*[^\s"]{10,}', description='CRITICAL: Access token detected in Git content')
        self.add_pattern(r'(?i)private[_\s]*key|-----BEGIN.*PRIVATE.*KEY-----', description='CRITICAL: Private key detected in Git content')
        self.add_pattern(r'(?i)aws[_\s]*access[_\s]*key|AKIA[0-9A-Z]{16}', description='CRITICAL: AWS access key detected in Git content')
        self.add_pattern(r'(?i)database[_\s]*url|db[_\s]*connection', description='WARNING: Database connection string detected in Git content')
        
        # Git web interfaces and tools
        self.add_pattern(r'(?i)gitweb|cgit|gitiles|gitlab|gitea|gogs', description='INFO: Git web interface detected')
        self.add_pattern(r'(?i)git-http-backend|git-receive-pack|git-upload-pack', description='INFO: Git HTTP backend service detected')
        self.add_pattern(r'(?i)GitLab.*version|Gitea.*version|Gogs.*version', description='INFO: Git platform version information detected')
        
        # Git-related error messages and debug info
        self.add_pattern(r'(?i)fatal:.*git|error:.*git|warning:.*git', description='INFO: Git error message detected - may reveal repository structure')
        self.add_pattern(r'(?i)not a git repository|No such file or directory.*\.git', description='INFO: Git repository check failed')
        self.add_pattern(r'(?i)permission denied.*git|access denied.*git', description='WARNING: Git access restriction detected')
        self.add_pattern(r'(?i)git.*clone.*failed|git.*fetch.*failed', description='INFO: Git operation failure detected')
        
        # Development/staging environment indicators
        self.add_pattern(r'(?i)dev\.git|staging\.git|test\.git|demo\.git', description='WARNING: Development/staging Git repository detected')
        self.add_pattern(r'(?i)backup\.git|old\.git|\.git\.bak|\.git\.old', description='WARNING: Backup Git repository detected')
        self.add_pattern(r'(?i)tmp\.git|temp\.git|cache\.git', description='WARNING: Temporary Git repository detected')
        
        # Git workflow and CI/CD indicators
        self.add_pattern(r'(?i)\.github/workflows|\.gitlab-ci\.yml|jenkins.*git', description='INFO: CI/CD Git integration detected')
        self.add_pattern(r'(?i)git.*hook|pre-commit|post-commit|pre-push', description='INFO: Git hooks detected - automated workflow scripts')
        self.add_pattern(r'(?i)git.*lfs|\.gitlfs|lfs\.github\.com', description='INFO: Git Large File Storage detected')
        
        # Git security and compliance patterns
        self.add_pattern(r'(?i)git.*signing|gpg.*git|signed.*commit', description='INFO: Git commit signing detected - enhanced security')
        self.add_pattern(r'(?i)git.*crypt|git.*secret|git.*vault', description='INFO: Git encryption/secret management tool detected')
        
        # Advanced Git attack vectors
        self.add_pattern(r'(?i)\.git/shallow|\.git/info/refs', description='WARNING: Git shallow clone or refs info exposed')
        self.add_pattern(r'(?i)\.git/FETCH_HEAD|\.git/ORIG_HEAD', description='INFO: Git operation metadata exposed')
        self.add_pattern(r'(?i)\.git/COMMIT_EDITMSG|\.git/MERGE_MSG', description='INFO: Git commit message files exposed')
        
        # Container and cloud Git patterns
        self.add_pattern(r'(?i)dockerfile.*git|docker.*git.*clone', description='INFO: Docker container using Git detected')
        self.add_pattern(r'(?i)kubernetes.*git|k8s.*git|helm.*git', description='INFO: Kubernetes Git integration detected')
        self.add_pattern(r'(?i)terraform.*git|ansible.*git|puppet.*git', description='INFO: Infrastructure-as-Code Git usage detected')

    def check(self):
        # Check for git command availability
        return which('git') is not None

    async def run(self, service):
        # Check if we should scan this service for Git content
        if not await self._should_scan_service(service):
            service.info(f"⏭️ Skipping Git enumeration for {service.target.address}:{service.port} - no Git indicators found")
            return
        
        service.info(f"🔍 Starting advanced Git security enumeration for {service.target.address}:{service.port}")
        
        # Initialize git findings tracking for reporting
        git_findings = {
            'repositories_found': [],
            'exposed_files': [],
            'secrets_detected': [],
            'web_interfaces': [],
            'ssh_access': [],
            'vulnerabilities': []
        }
        
        # Store git findings in service for reporting
        if not hasattr(service, 'git_findings'):
            service.git_findings = git_findings
        
        # Determine enumeration strategy based on service type
        if service.port == 9418:
            # Git daemon protocol enumeration
            await self._enumerate_git_daemon(service)
        elif service.name in ['http', 'https'] or service.port in [80, 443, 8080, 8443]:
            # HTTP-based Git detection and exploitation
            await self._enumerate_http_git(service)
        elif service.name == 'ssh' or service.port == 22:
            # SSH Git enumeration
            await self._enumerate_ssh_git(service)
        elif service.port in [3000, 9000] or any(name in str(service.name).lower() for name in ['gitea', 'gogs', 'gitlab']):
            # Git web interface enumeration
            await self._enumerate_git_web_interface(service)
        else:
            # Generic Git service detection
            await self._enumerate_generic_git(service)
        
        # Always perform secret scanning if any Git content is found
        await self._perform_secret_analysis(service)
        
        # Generate comprehensive Git report
        await self._generate_git_report(service)

    async def _should_scan_service(self, service):
        """Determine if we should scan this service for Git content based on indicators"""
        
        # Check if user forced Git scanning
        if self.get_option('force-git-scan'):
            service.info(f"✅ Git enumeration triggered: Force scan enabled")
            return True
        
        # Always scan known Git ports and services
        if (service.port == 9418 or 
            service.port in [3000, 8080, 8443, 9000] or
            any(name in str(service.name).lower() for name in ['git', 'gitea', 'gogs', 'gitlab', 'cgit', 'gitweb'])):
            service.info(f"✅ Git enumeration triggered: Known Git port/service detected")
            return True
        
        # For SSH services, check if Git is mentioned in service banner or version
        if service.name == 'ssh' or service.port == 22:
            if await self._check_ssh_git_indicators(service):
                service.info(f"✅ Git enumeration triggered: SSH Git indicators found")
                return True
        
        # For HTTP services, check for Git indicators in previous scan results
        if service.name in ['http', 'https'] or service.port in [80, 443]:
            if await self._check_http_git_indicators(service):
                service.info(f"✅ Git enumeration triggered: HTTP Git indicators found")
                return True
        
        # If no indicators found, skip Git enumeration
        service.info(f"🚫 No Git indicators found for {service.target.address}:{service.port}")
        return False
    
    async def _check_ssh_git_indicators(self, service):
        """Check SSH service for Git-related indicators"""
        try:
            # Look for SSH scan results that might indicate Git usage
            scan_dir = f"{service.target.scandir}/tcp{service.port}"
            
            if os.path.exists(scan_dir):
                # Check nmap SSH results for Git-related information
                for filename in os.listdir(scan_dir):
                    if 'ssh' in filename.lower() and filename.endswith('.txt'):
                        filepath = os.path.join(scan_dir, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read().lower()
                                # Look for Git-related keywords in SSH scan results
                                git_indicators = ['git', 'gitea', 'gitlab', 'gogs', 'repository', 'repo']
                                if any(indicator in content for indicator in git_indicators):
                                    return True
                        except:
                            continue
            
            return False
        except Exception:
            return False
    
    async def _check_http_git_indicators(self, service):
        """Check HTTP service for Git-related indicators from previous scans"""
        try:
            scan_dir = f"{service.target.scandir}/tcp{service.port}"
            
            if not os.path.exists(scan_dir):
                return False
            
            git_indicators_found = False
            
            # Check robots.txt for Git-related paths
            robots_files = [f for f in os.listdir(scan_dir) if 'robots' in f.lower() and f.endswith('.txt')]
            for robots_file in robots_files:
                filepath = os.path.join(scan_dir, robots_file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        # Look for Git-related paths in robots.txt
                        git_paths = ['.git', 'git/', 'repository', 'repo/', 'gitlab', 'gitea', 'cgit']
                        if any(path in content for path in git_paths):
                            service.info(f"🔍 Git indicator found in robots.txt: Git paths detected")
                            git_indicators_found = True
                            break
                except:
                    continue
            
            # Check directory busting results for Git-related findings
            dirbust_files = [f for f in os.listdir(scan_dir) if any(tool in f.lower() for tool in ['feroxbuster', 'dirb', 'gobuster', 'dirbuster']) and f.endswith('.txt')]
            for dirbust_file in dirbust_files:
                filepath = os.path.join(scan_dir, dirbust_file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        # Look for Git-related directories/files found by directory busting
                        git_findings = ['.git/', '/.git', 'git/', '/git', 'gitea', 'gitlab', 'cgit', 'repository', '/repo']
                        found_indicators = [indicator for indicator in git_findings if indicator in content]
                        if found_indicators:
                            service.info(f"🔍 Git indicator found in directory busting: {', '.join(found_indicators)}")
                            git_indicators_found = True
                            break
                except:
                    continue
            
            # Check curl/HTTP responses for Git-related headers or content
            http_files = [f for f in os.listdir(scan_dir) if 'curl' in f.lower() and (f.endswith('.html') or f.endswith('.txt'))]
            for http_file in http_files:
                filepath = os.path.join(scan_dir, http_file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        # Look for Git-related content in HTTP responses
                        git_content = ['x-git', 'git-', 'gitea', 'gitlab', 'cgit', 'gitweb', '.git', 'repository']
                        found_content = [indicator for indicator in git_content if indicator in content]
                        if found_content:
                            service.info(f"🔍 Git indicator found in HTTP response: {', '.join(found_content)}")
                            git_indicators_found = True
                            break
                except:
                    continue
            
            # Check service enumeration results for Git-related services
            enum_files = [f for f in os.listdir(scan_dir) if 'nmap' in f.lower() and f.endswith('.txt')]
            for enum_file in enum_files:
                filepath = os.path.join(scan_dir, enum_file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        # Look for Git-related services or technologies
                        git_services = ['git', 'gitea', 'gitlab', 'gogs', 'cgit', 'gitweb', 'git-http-backend']
                        if any(service_name in content for service_name in git_services):
                            service.info(f"🔍 Git indicator found in service enumeration: Git service detected")
                            git_indicators_found = True
                            break
                except:
                    continue
            
            return git_indicators_found
            
        except Exception:
            return False

    async def _enumerate_git_daemon(self, service):
        """Enumerate Git daemon protocol (port 9418)"""
        service.info("🚀 Enumerating Git daemon protocol (port 9418)")
        
        # Get best hostname for connection
        best_hostname = service.target.get_best_hostname()
        git_url = f"git://{best_hostname}:9418/"
        
        # List remote repositories and branches
        service.info("📋 Listing remote repositories and branches...")
        await service.execute(f'git ls-remote {git_url}', 
                             future_outfile='{protocol}_{port}_git-ls-remote.txt')
        
        # Try common repository names
        common_repos = [
            'repo', 'main', 'project', 'app', 'web', 'website', 'src', 'source',
            'dev', 'development', 'staging', 'prod', 'production', 'backup',
            'admin', 'config', 'infrastructure', 'deployment', 'scripts',
            'tools', 'utils', 'private', 'internal', 'test', 'demo'
        ]
        
        service.info("🔍 Testing common repository names...")
        for repo_name in common_repos:
            test_url = f"{git_url}{repo_name}"
            await service.execute(f'git ls-remote {test_url}', 
                                 future_outfile=f'{protocol}_{port}_git-ls-remote-{repo_name}.txt')
        
        # Try to discover repositories by testing different paths
        service.info("🕵️ Attempting repository discovery...")
        await service.execute(f'timeout 30 git ls-remote {git_url}* 2>/dev/null || true',
                             future_outfile='{protocol}_{port}_git-discovery.txt')
        
        # Manual commands for repository cloning and analysis
        service.add_manual_command(f'git clone {git_url} git-repo-{service.target.address}')
        service.add_manual_command(f'git clone {git_url}repo git-repo-main-{service.target.address}')
        service.add_manual_command(f'git clone {git_url}infrastructure git-infrastructure-{service.target.address}')
        service.add_manual_command(f'git clone {git_url}dev git-dev-{service.target.address}')
        
        # Add comprehensive user-based repository patterns
        common_users = ['admin', 'user', 'dev', 'developer', 'root', 'git', 'web', 'app', 'jenkins', 'gitlab-runner', 'github-actions']
        common_repos = ['infrastructure', 'config', 'scripts', 'deployment', 'backup', 'private', 'internal', 'secrets', 'keys', 'passwords']
        
        for user in common_users:
            for repo in common_repos:
                service.add_manual_command(f'git clone {git_url}{user}/{repo} git-{user}-{repo}-{service.target.address}')
        
        # Advanced Git daemon enumeration
        service.add_manual_command(f'git ls-remote {git_url}* | grep -E "(infrastructure|config|secret|private|internal|backup)"')
        service.add_manual_command(f'timeout 60 bash -c "for repo in {{repo,main,dev,prod,test,staging,backup,config,src,app,web,api,admin,private,internal,secrets}}; do echo \\"Testing $repo:\\"; git ls-remote {git_url}$repo 2>/dev/null && echo \\"Found: $repo\\"; done"')

    async def _enumerate_http_git(self, service):
        """Enumerate Git repositories over HTTP/HTTPS"""
        service.info("🌐 Enumerating Git repositories over HTTP")
        
        # Get best hostname for HTTP requests
        best_hostname = service.target.get_best_hostname()
        hostname_label = best_hostname.replace('.', '_').replace(':', '_')
        
        scan_hostname = best_hostname
        if ':' in best_hostname and not best_hostname.startswith('['):
            scan_hostname = f'[{best_hostname}]'
        
        base_url = f"{service.target.scheme}://{scan_hostname}:{service.port}"
        
        # Check for .git directory exposure
        service.info("🔍 Checking for exposed .git directory...")
        
        # Test critical Git files
        git_files = [
            '.git/HEAD',
            '.git/config', 
            '.git/index',
            '.git/logs/HEAD',
            '.git/refs/heads/master',
            '.git/refs/heads/main',
            '.git/refs/heads/dev',
            '.git/refs/heads/development',
            '.git/objects/',
            '.git/COMMIT_EDITMSG',
            '.gitignore',
            '.gitmodules',
            '.git-credentials'
        ]
        
        for git_file in git_files:
            await service.execute(f'curl -sSikf {base_url}/{git_file}',
                                 future_outfile=f'{protocol}_{port}_{service.target.scheme}_git-{git_file.replace("/", "_").replace(".", "dot")}-{hostname_label}.txt')
        
        # Test common Git subdirectories
        git_subdirs = [
            'git',
            '.git',
            'repo',
            'repository',
            'source',
            'src',
            'code',
            'project',
            'dev',
            'backup'
        ]
        
        service.info("📁 Testing common Git subdirectories...")
        for subdir in git_subdirs:
            await service.execute(f'curl -sSikf {base_url}/{subdir}/.git/HEAD',
                                 future_outfile=f'{protocol}_{port}_{service.target.scheme}_git-subdir-{subdir}-{hostname_label}.txt')
        
        # Comprehensive .git exploitation toolkit
        service.add_manual_command(f'git-dumper {base_url}/.git/ git-dump-{hostname_label}/')
        service.add_manual_command(f'GitTools/Dumper/gitdumper.sh {base_url}/.git/ git-dump-{hostname_label}/')
        service.add_manual_command(f'python3 -m pip install git-dumper && git-dumper {base_url}/.git/ git-dump-{hostname_label}/')
        service.add_manual_command(f'wget -r -np -nH --cut-dirs=1 -R "index.html*" {base_url}/.git/')
        service.add_manual_command(f'curl -s {base_url}/.git/HEAD && echo "Git HEAD found - repository accessible!"')
        
        # Advanced Git content analysis
        service.add_manual_command(f'curl -s {base_url}/.git/logs/HEAD | head -20  # Check recent commit history')
        service.add_manual_command(f'curl -s {base_url}/.git/config | grep -E "(url|remote|user|email)"  # Extract configuration')
        service.add_manual_command(f'curl -s {base_url}/.git/refs/heads/master 2>/dev/null || curl -s {base_url}/.git/refs/heads/main  # Get latest commit')
        service.add_manual_command(f'curl -s {base_url}/.git/index | strings | head -50  # Extract file names from index')
        
        # Git repository reconstruction and analysis
        service.add_manual_command(f'cd git-dump-{hostname_label}/ && git log --oneline --all  # View commit history')
        service.add_manual_command(f'cd git-dump-{hostname_label}/ && git branch -a  # List all branches')
        service.add_manual_command(f'cd git-dump-{hostname_label}/ && git show --name-only  # Show latest commit files')
        service.add_manual_command(f'cd git-dump-{hostname_label}/ && git log --grep="password\\|secret\\|key\\|credential" --all  # Search for sensitive commits')
        service.add_manual_command(f'cd git-dump-{hostname_label}/ && git log --all --full-history -- "*.env" "*.config" "*secret*" "*key*"  # Track sensitive files')
        
        # Secret scanning in Git content
        service.add_manual_command(f'cd git-dump-{hostname_label}/ && grep -r -i "password\\|secret\\|api_key\\|private_key" . || true  # Basic secret scan')
        service.add_manual_command(f'cd git-dump-{hostname_label}/ && git log --all -p | grep -E "(password|secret|key|token|credential)" || true  # Scan commit diffs')
        service.add_manual_command(f'cd git-dump-{hostname_label}/ && truffleHog --regex --entropy=False . || true  # Advanced secret scanning')

    async def _enumerate_ssh_git(self, service):
        """Enumerate Git over SSH"""
        service.info("🔐 Enumerating Git over SSH")
        
        best_hostname = service.target.get_best_hostname()
        
        # Test SSH Git access patterns
        service.info("🧪 Testing SSH Git access patterns...")
        
        # Common Git SSH usernames
        git_users = ['git', 'gitlab', 'gitea', 'gogs', 'github', 'repo', 'admin']
        
        for user in git_users:
            # Test Git SSH connectivity (without authentication)
            await service.execute(f'timeout 10 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {user}@{best_hostname} "echo SSH Git test" 2>&1 || true',
                                 future_outfile=f'{protocol}_{port}_ssh-git-{user}.txt')
        
        # Manual commands for SSH Git enumeration
        for user in git_users:
            service.add_manual_command(f'ssh -o StrictHostKeyChecking=no {user}@{best_hostname} "git --version" # Test Git SSH access')
            service.add_manual_command(f'ssh -o StrictHostKeyChecking=no {user}@{best_hostname} "find / -name \"*.git\" 2>/dev/null" # Find Git repos')
            service.add_manual_command(f'git clone ssh://{user}@{best_hostname}/repo.git ssh-git-repo-{best_hostname}')
            service.add_manual_command(f'git clone {user}@{best_hostname}:repo.git ssh-git-repo-{best_hostname}')

    async def _enumerate_git_web_interface(self, service):
        """Enumerate Git web interfaces (GitLab, Gitea, Gogs, etc.)"""
        service.info("🌐 Enumerating Git web interface")
        
        best_hostname = service.target.get_best_hostname()
        hostname_label = best_hostname.replace('.', '_').replace(':', '_')
        
        scan_hostname = best_hostname
        if ':' in best_hostname and not best_hostname.startswith('['):
            scan_hostname = f'[{best_hostname}]'
        
        base_url = f"http://{scan_hostname}:{service.port}"
        https_url = f"https://{scan_hostname}:{service.port}"
        
        # Test common Git web interface endpoints
        git_endpoints = [
            '/',
            '/api/v1/version',  # Gitea/Gogs API
            '/api/v4/version',  # GitLab API
            '/api/version',     # Generic API
            '/explore',         # Public repositories
            '/admin',           # Admin interface
            '/user/sign_up',    # Registration
            '/user/login',      # Login
            '/install',         # Installation page
            '/.well-known/security.txt',
            '/robots.txt'
        ]
        
        service.info("🔍 Testing Git web interface endpoints...")
        for endpoint in git_endpoints:
            await service.execute(f'curl -sSikL {base_url}{endpoint}',
                                 future_outfile=f'{protocol}_{port}_git-web-{endpoint.replace("/", "_").replace(".", "dot")}-{hostname_label}.txt')
        
        # Test HTTPS if HTTP fails
        await service.execute(f'curl -sSikL {https_url}/',
                             future_outfile=f'{protocol}_{port}_git-web-https-{hostname_label}.txt')
        
        # Advanced Git interface enumeration
        service.add_manual_command(f'curl -s {base_url}/api/v1/version | jq .  # Gitea/Gogs version info')
        service.add_manual_command(f'curl -s {base_url}/api/v4/version | jq .  # GitLab version info')
        service.add_manual_command(f'curl -s {base_url}/explore/repos | grep -o "href=\\"[^\\"]*/[^\\"]*.git\\"" | head -20  # Discover public repos')
        service.add_manual_command(f'ffuf -u {base_url}/FUZZ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -fc 404  # Directory fuzzing')

    async def _enumerate_generic_git(self, service):
        """Generic Git service enumeration"""
        service.info("⚙️ Generic Git service enumeration")
        
        # Try to identify Git service version
        await service.execute('git --version', future_outfile='{protocol}_{port}_git-version.txt')
        
        # Check if service responds to Git protocol
        best_hostname = service.target.get_best_hostname()
        await service.execute(f'timeout 10 git ls-remote git://{best_hostname}:{service.port}/ 2>&1 || true',
                             future_outfile='{protocol}_{port}_git-protocol-test.txt')
        
        # Banner grabbing for unknown Git services
        await service.execute(f'timeout 10 nc -nv {best_hostname} {service.port} </dev/null 2>&1 || true',
                             future_outfile='{protocol}_{port}_git-banner.txt')

    async def _perform_secret_analysis(self, service):
        """Perform secret and credential analysis on discovered Git content"""
        service.info("🔍 Performing secret analysis on Git content")
        
        # This method would analyze any Git content found during enumeration
        # It runs last to catch secrets from all previous enumeration steps
        
        best_hostname = service.target.get_best_hostname()
        hostname_label = best_hostname.replace('.', '_').replace(':', '_')
        
        # Manual commands for comprehensive secret scanning
        service.add_manual_command(f'find results/ -name "*git*" -type f -exec grep -l "password\\|secret\\|key\\|token" {{}} \\; | head -10  # Find files with secrets')
        service.add_manual_command(f'grep -r -E "(password|secret|api_key|private_key|token)\\s*[=:]\\s*[\\w.-]+" results/*git* | head -20 || true  # Extract potential secrets')
        service.add_manual_command(f'git secrets --scan results/ || echo "git-secrets not installed"  # Advanced secret detection')
        service.add_manual_command(f'gitleaks detect --source results/ || echo "gitleaks not installed"  # Gitleaks secret scanner')

    def check_git_tools(self):
        """Check for Git exploitation tools availability"""
        essential_tools = {
            'git': 'Git command line tool (REQUIRED)',
            'curl': 'HTTP client for web enumeration',
            'wget': 'Web content retriever',
            'nc': 'Netcat for banner grabbing'
        }
        
        advanced_tools = {
            'git-dumper': 'GitTools dumper for .git exploitation',
            'truffleHog': 'Secret scanner for Git repositories',
            'gitleaks': 'Advanced Git secret detection',
            'git-secrets': 'AWS Git secret prevention',
            'ffuf': 'Fast web fuzzer for Git interfaces',
            'jq': 'JSON processor for API responses'
        }
        
        available_essential = []
        missing_essential = []
        available_advanced = []
        missing_advanced = []
        
        for tool, description in essential_tools.items():
            if which(tool):
                available_essential.append(f"✅ {tool}: {description}")
            else:
                missing_essential.append(f"❌ {tool}: {description}")
        
        for tool, description in advanced_tools.items():
            if which(tool):
                available_advanced.append(f"✅ {tool}: {description}")
            else:
                missing_advanced.append(f"⚠️  {tool}: {description}")
        
        return {
            'essential': {'available': available_essential, 'missing': missing_essential},
            'advanced': {'available': available_advanced, 'missing': missing_advanced}
        }

    async def _generate_git_report(self, service):
        """Generate comprehensive Git security report for Jinja2 integration"""
        service.info("📊 Generating Git security report")
        
        best_hostname = service.target.get_best_hostname()
        hostname_label = best_hostname.replace('.', '_').replace(':', '_')
        
        # Create comprehensive Git security report
        git_report = {
            'scan_type': 'Git Security Assessment',
            'target': {
                'address': service.target.address,
                'hostname': best_hostname,
                'port': service.port,
                'service': service.name
            },
            'timestamp': datetime.now().isoformat(),
            'findings': service.git_findings if hasattr(service, 'git_findings') else {},
            'tools_status': self.check_git_tools(),
            'security_summary': {
                'critical_issues': 0,
                'warnings': 0,
                'info_items': 0,
                'total_repositories': 0,
                'exposed_secrets': 0
            }
        }
        
        # Analyze scan results and count findings
        if hasattr(service, 'git_findings'):
            findings = service.git_findings
            git_report['security_summary'].update({
                'total_repositories': len(findings.get('repositories_found', [])),
                'exposed_secrets': len(findings.get('secrets_detected', [])),
                'critical_issues': len([f for f in findings.get('vulnerabilities', []) if 'CRITICAL' in str(f)]),
                'warnings': len([f for f in findings.get('vulnerabilities', []) if 'WARNING' in str(f)]),
                'info_items': len([f for f in findings.get('vulnerabilities', []) if 'INFO' in str(f)])
            })
        
        # Save report as JSON for Jinja2 template consumption
        report_file = f'{protocol}_{service.port}_git-security-report_{hostname_label}.json'
        await service.execute(f'echo \'{json.dumps(git_report, indent=2)}\' > {{scandir}}/{report_file}',
                             outfile=report_file)
        
        # Create human-readable summary report
        summary_lines = [
            "=== GIT SECURITY ASSESSMENT SUMMARY ===",
            f"Target: {best_hostname}:{service.port}",
            f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "🔍 FINDINGS OVERVIEW:",
            f"  • Repositories Found: {git_report['security_summary']['total_repositories']}",
            f"  • Critical Issues: {git_report['security_summary']['critical_issues']}",
            f"  • Warnings: {git_report['security_summary']['warnings']}",
            f"  • Information Items: {git_report['security_summary']['info_items']}",
            f"  • Exposed Secrets: {git_report['security_summary']['exposed_secrets']}",
            "",
            "🛠️ EXPLOITATION TOOLS STATUS:",
        ]
        
        # Add tool status to summary
        tools_info = self.check_git_tools()
        for tool in tools_info['essential']['available']:
            summary_lines.append(f"  {tool}")
        for tool in tools_info['essential']['missing']:
            summary_lines.append(f"  {tool}")
        
        summary_lines.extend([
            "",
            "📋 NEXT STEPS:",
            "  1. Review manual commands in _manual_commands.txt",
            "  2. Clone any discovered repositories for analysis",
            "  3. Scan cloned repositories for secrets using truffleHog/gitleaks",
            "  4. Check commit history for sensitive information",
            "  5. Verify all .git exposures have been secured",
            "",
            "For detailed technical findings, see the JSON report file.",
            "=" * 50
        ])
        
        # Save human-readable summary
        summary_file = f'{protocol}_{service.port}_git-summary-report_{hostname_label}.txt'
        summary_content = '\n'.join(summary_lines)
        await service.execute(f'echo "{summary_content}" > {{scandir}}/{summary_file}',
                             outfile=summary_file)
        
        # Add summary to service attributes for Jinja2 template access
        service.git_security_summary = git_report['security_summary']
        service.git_scan_timestamp = git_report['timestamp']
        
        service.info(f"✅ Git security report saved: {report_file}")
        service.info(f"📄 Human-readable summary: {summary_file}")