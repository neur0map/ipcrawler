# IPCrawler Makefile - Simple installation and management
# This Makefile no longer uses venv or modifies PATH.
# It installs a symlink in ~/.local/bin/ipcrawler and removes it on clean.

.PHONY: install clean clean-all update debug help dev-install fix-permissions test test-unit test-integration test-e2e coverage lint security-scan

# Default target
help:
	@echo "IPCrawler Management"
	@echo "==================="
	@echo "  make install         - Install ipcrawler and all tools"
	@echo "  make dev-install     - Install for development (live code updates)"
	@echo "  make update          - Update to latest version"
	@echo "  make clean           - Remove ipcrawler only (keeps tools & results)"
	@echo "  make clean-all       - Remove everything including tools (keeps results)"
	@echo "  make fix-permissions - Fix ownership of results directory files"
	@echo "  make debug           - Show system diagnostics"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make coverage        - Generate test coverage report"
	@echo "  make lint            - Run code quality checks"
	@echo ""

# Complete installation with tool detection
install:
	@echo "🚀 Installing IPCrawler..."
	@echo "🔍 Detecting system and missing tools..."
	@# Detect OS and install basic tools
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "📱 macOS detected - Installing base tools..."; \
		brew install python3 nmap curl 2>/dev/null || true; \
		echo "🔧 Installing available penetration testing tools..."; \
		available_tools="feroxbuster gobuster nikto smbclient masscan john hashcat"; \
		unavailable_tools="dnsrecon enum4linux impacket-scripts nbtscan onesixtyone oscanner smbmap tnscmd10g"; \
		for tool in $$available_tools; do \
			if ! command -v $$tool >/dev/null 2>&1; then \
				echo "  Installing $$tool..."; \
				brew install $$tool 2>/dev/null || echo "  ⚠️  $$tool failed to install"; \
			fi; \
		done; \
		echo "📝 Note: Some Linux-specific tools are not available on macOS:"; \
		echo "   Missing: $$unavailable_tools"; \
		echo "   ✅ ipcrawler automatically uses nmap script alternatives on macOS"; \
		echo "   💡 For complete tool coverage, use Linux (Kali/Ubuntu) instead"; \
		echo "🔧 Installing SecLists wordlists..."; \
		if [ ! -d "$$HOME/tools/wordlists/seclists" ] && [ ! -d "$$HOME/tools/SecLists" ] && [ ! -d "/opt/SecLists" ] && [ ! -d "/usr/local/share/seclists" ]; then \
			echo "  📦 Installing SecLists from GitHub..."; \
			mkdir -p ~/tools/wordlists 2>/dev/null; \
			if git clone --depth 1 https://github.com/danielmiessler/SecLists.git ~/tools/wordlists/seclists 2>/dev/null; then \
				echo "  ✅ SecLists installed to ~/tools/wordlists/seclists"; \
			else \
				echo "  ⚠️  SecLists installation failed"; \
			fi; \
		else \
			echo "  ✅ SecLists already installed"; \
		fi; \
		echo "  🏆 Installing Jhaddix All.txt..."; \
		mkdir -p ~/tools/wordlists/jhaddix 2>/dev/null; \
		if [ ! -f "$$HOME/tools/wordlists/jhaddix/jhaddix-all.txt" ]; then \
			if curl -s https://gist.githubusercontent.com/jhaddix/b80ea67d85c13206125806f0828f4d10/raw/c81a34fe84731430741e74c7ca0ee9b77c63e523/all.txt -o /tmp/jhaddix-all.txt 2>/dev/null; then \
				mv /tmp/jhaddix-all.txt ~/tools/wordlists/jhaddix/jhaddix-all.txt 2>/dev/null && \
				echo "  ✅ Jhaddix All.txt installed to ~/tools/wordlists/jhaddix/" || echo "  ⚠️  Jhaddix install failed"; \
			else \
				echo "  ⚠️  Jhaddix download failed"; \
			fi; \
		else \
			echo "  ✅ Jhaddix All.txt already installed"; \
		fi; \
		echo "  📚 Installing OneListForAll..."; \
		if [ ! -d "$$HOME/tools/wordlists/onelistforall" ] || [ ! -f "$$HOME/tools/wordlists/onelistforall/onelistforall.txt" ]; then \
			rm -rf ~/tools/wordlists/onelistforall 2>/dev/null; \
			if git clone --depth 1 https://github.com/six2dez/OneListForAll.git ~/tools/wordlists/onelistforall; then \
				if [ -f "$$HOME/tools/wordlists/onelistforall/onelistforall.txt" ]; then \
					echo "  ✅ OneListForAll installed to ~/tools/wordlists/onelistforall/"; \
				else \
					echo "  ⚠️  OneListForAll clone succeeded but wordlist files missing"; \
				fi; \
			else \
				echo "  ⚠️  OneListForAll clone failed"; \
			fi; \
		else \
			echo "  ✅ OneListForAll already installed"; \
		fi; \
	elif [ -f /etc/debian_version ]; then \
		echo "🐧 Debian/Ubuntu detected - Installing complete penetration testing suite..."; \
		echo "🔑 Fixing Kali GPG keys if needed..."; \
		if grep -q "kali" /etc/os-release 2>/dev/null; then \
			echo "  🔧 Kali Linux detected - updating GPG keys"; \
			sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys ED65462EC8D5E4C5 2>/dev/null || true; \
			wget -q -O - https://archive.kali.org/archive-key.asc | sudo apt-key add - 2>/dev/null || true; \
		fi; \
		sudo apt update; \
		echo "  📦 Checking and installing base tools..."; \
		base_tools="python3 python3-pip curl nmap"; \
		missing_base=""; \
		for tool in $$base_tools; do \
			if command -v $$tool >/dev/null 2>&1 || dpkg -l | grep -q "^ii.*$$tool"; then \
				echo "  ✅ $$tool already available"; \
			else \
				missing_base="$$missing_base $$tool"; \
			fi; \
		done; \
		if [ -n "$$missing_base" ]; then \
			echo "  📦 Installing missing base tools:$$missing_base"; \
			sudo apt install -y $$missing_base; \
		else \
			echo "  ✅ All base tools already installed"; \
		fi; \
		echo "  🔧 Checking and installing penetration testing tools..."; \
		core_tools="dnsrecon gobuster feroxbuster"; \
		missing_tools=""; \
		for tool in $$core_tools; do \
			if command -v $$tool >/dev/null 2>&1; then \
				echo "  ✅ $$tool already installed"; \
			else \
				missing_tools="$$missing_tools $$tool"; \
			fi; \
		done; \
		if [ -n "$$missing_tools" ]; then \
			echo "  📦 Installing missing tools:$$missing_tools"; \
			for tool in $$missing_tools; do \
				case $$tool in \
					dnsrecon) \
						sudo apt install -y dnsrecon 2>/dev/null && echo "  ✅ dnsrecon installed" || echo "  ⚠️  dnsrecon install failed"; \
						;; \
					gobuster) \
						if sudo apt install -y gobuster 2>/dev/null; then \
							echo "  ✅ gobuster installed via apt"; \
						else \
							echo "  📦 Installing gobuster from GitHub..."; \
							GOBUSTER_VERSION=$$(curl -s https://api.github.com/repos/OJ/gobuster/releases/latest | grep -o '"tag_name": "v[^"]*"' | cut -d'"' -f4 | sed 's/v//'); \
							if [ "$$GOBUSTER_VERSION" ]; then \
								ARCH=$$(dpkg --print-architecture 2>/dev/null || echo "amd64"); \
								if [ "$$ARCH" = "amd64" ]; then GOBUSTER_ARCH="Linux_x86_64"; \
								elif [ "$$ARCH" = "arm64" ]; then GOBUSTER_ARCH="Linux_arm64"; \
								else GOBUSTER_ARCH="Linux_x86_64"; fi; \
								wget -q "https://github.com/OJ/gobuster/releases/download/v$$GOBUSTER_VERSION/gobuster_$${GOBUSTER_VERSION}_$${GOBUSTER_ARCH}.tar.gz" -O /tmp/gobuster.tar.gz && \
								sudo tar -xzf /tmp/gobuster.tar.gz -C /usr/local/bin/ gobuster && \
								sudo chmod +x /usr/local/bin/gobuster && \
								rm -f /tmp/gobuster.tar.gz && \
								echo "  ✅ gobuster installed from GitHub"; \
							else \
								echo "  ⚠️  gobuster install failed"; \
							fi; \
						fi; \
						;; \
					feroxbuster) \
						if sudo apt install -y feroxbuster 2>/dev/null; then \
							echo "  ✅ feroxbuster installed via apt"; \
						else \
							echo "  📦 Installing feroxbuster from GitHub..."; \
							FEROX_VERSION=$$(curl -s https://api.github.com/repos/epi052/feroxbuster/releases/latest | grep -o '"tag_name": "v[^"]*"' | cut -d'"' -f4 | sed 's/v//'); \
							if [ "$$FEROX_VERSION" ]; then \
								ARCH=$$(dpkg --print-architecture 2>/dev/null || echo "amd64"); \
								if [ "$$ARCH" = "amd64" ]; then FEROX_ARCH="x86_64-linux"; \
								elif [ "$$ARCH" = "arm64" ]; then FEROX_ARCH="aarch64-linux"; \
								else FEROX_ARCH="x86_64-linux"; fi; \
								wget -q "https://github.com/epi052/feroxbuster/releases/download/v$$FEROX_VERSION/feroxbuster_$${FEROX_VERSION}_$${FEROX_ARCH}.zip" -O /tmp/feroxbuster.zip && \
								sudo unzip -j /tmp/feroxbuster.zip feroxbuster -d /usr/local/bin/ && \
								sudo chmod +x /usr/local/bin/feroxbuster && \
								rm -f /tmp/feroxbuster.zip && \
								echo "  ✅ feroxbuster installed from GitHub"; \
							else \
								echo "  ⚠️  feroxbuster install failed"; \
							fi; \
						fi; \
						;; \
				esac; \
			done; \
		else \
			echo "  ✅ All core tools already installed"; \
		fi; \
		echo "  🔧 Installing SecLists wordlists..."; \
		if [ ! -d "/usr/share/seclists" ]; then \
			echo "  📦 Installing SecLists from GitHub (this may take a few minutes)..."; \
			{ \
				sudo git clone --depth 1 https://github.com/danielmiessler/SecLists.git /usr/share/seclists 2>/dev/null; \
				echo $$? > /tmp/seclists_status; \
			} & \
			CLONE_PID=$$!; \
			spinner="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"; \
			i=0; \
			printf "  "; \
			while kill -0 $$CLONE_PID 2>/dev/null; do \
				case $$i in \
					0) printf "\b⠋";; \
					1) printf "\b⠙";; \
					2) printf "\b⠹";; \
					3) printf "\b⠸";; \
					4) printf "\b⠼";; \
					5) printf "\b⠴";; \
					6) printf "\b⠦";; \
					7) printf "\b⠧";; \
					8) printf "\b⠇";; \
					9) printf "\b⠏";; \
				esac; \
				i=$$(( (i+1) % 10 )); \
				sleep 0.1; \
			done; \
			wait $$CLONE_PID; \
			STATUS=$$(cat /tmp/seclists_status 2>/dev/null || echo "1"); \
			rm -f /tmp/seclists_status; \
			if [ "$$STATUS" = "0" ]; then \
				printf "\b✅ SecLists installed to /usr/share/seclists\n"; \
			else \
				printf "\b⚠️  SecLists installation failed, wordlists will be limited\n"; \
			fi; \
		else \
			echo "  ✅ SecLists already installed"; \
		fi; \
		echo "  🏆 Installing Jhaddix All.txt..."; \
		sudo mkdir -p /usr/share/wordlists/jhaddix 2>/dev/null; \
		if curl -s https://gist.githubusercontent.com/jhaddix/b80ea67d85c13206125806f0828f4d10/raw/c81a34fe84731430741e74c7ca0ee9b77c63e523/all.txt -o /tmp/jhaddix-all.txt 2>/dev/null; then \
			sudo mv /tmp/jhaddix-all.txt /usr/share/wordlists/jhaddix/jhaddix-all.txt 2>/dev/null && \
			echo "  ✅ Jhaddix All.txt installed" || echo "  ⚠️  Jhaddix install failed"; \
		else \
			echo "  ⚠️  Jhaddix download failed"; \
		fi; \
		echo "  📚 Installing OneListForAll..."; \
		if sudo git clone https://github.com/six2dez/OneListForAll.git /usr/share/wordlists/onelistforall >/dev/null 2>&1; then \
			echo "  ✅ OneListForAll installed"; \
		else \
			echo "  ⚠️  OneListForAll install failed"; \
		fi; \
		sudo apt install -y nbtscan nikto onesixtyone oscanner; \
		sudo apt install -y smbclient smbmap snmp sslscan sipvicious; \
		echo "  🔧 Installing redis-tools..."; \
		if ! command -v redis-cli >/dev/null 2>&1; then \
			sudo apt install -y redis-tools 2>/dev/null || \
			sudo apt install -y redis 2>/dev/null || \
			sudo apt install -y redis-server 2>/dev/null || \
			sudo apt install -y redis-cli 2>/dev/null || \
			{ echo "  📦 Installing redis-cli via pip..."; \
			  python3 -m pip install --user redis-py-cli 2>/dev/null || \
			  python3 -m pip install --user redis 2>/dev/null || \
			  echo "  ⚠️  Could not install redis-cli, redis enumeration will be limited. Install manually with: apt install redis-tools"; }; \
		else \
			echo "  ✅ redis-cli already available"; \
		fi; \
		echo "  🔧 Installing enum4linux and impacket tools..."; \
		sudo apt install -y enum4linux-ng || sudo apt install -y enum4linux || echo "  ⚠️  enum4linux not available, will try alternative installation"; \
		sudo apt install -y impacket-scripts || sudo apt install -y python3-impacket || echo "  ⚠️  impacket-scripts not available, installing via pip"; \
		if ! command -v enum4linux-ng >/dev/null 2>&1 && ! command -v enum4linux >/dev/null 2>&1; then \
			echo "  📦 Installing enum4linux-ng from GitHub..."; \
			sudo git clone https://github.com/cddmp/enum4linux-ng.git /opt/enum4linux-ng 2>/dev/null || true; \
			sudo ln -sf /opt/enum4linux-ng/enum4linux-ng.py /usr/local/bin/enum4linux-ng 2>/dev/null || true; \
		fi; \
		if ! command -v impacket-scripts >/dev/null 2>&1 && ! dpkg -l | grep -q python3-impacket; then \
			echo "  📦 Installing impacket via pip..."; \
			python3 -m pip install --user impacket || sudo python3 -m pip install impacket; \
		fi; \
		sudo apt install -y tnscmd10g whatweb masscan dirb dirsearch; \
		sudo apt install -y john hashcat hydra medusa ncrack sqlmap; \
		sudo apt install -y wfuzz wpscan sublist3r amass fierce dnsutils; \
		echo "  📦 Installing additional tools..."; \
		echo "  🔧 Installing ffuf..."; \
		if ! command -v ffuf >/dev/null 2>&1; then \
			sudo apt install -y ffuf 2>/dev/null || \
			sudo snap install ffuf 2>/dev/null || \
			{ echo "  📦 Installing ffuf from GitHub releases..."; \
			  FFUF_VERSION=$$(curl -s https://api.github.com/repos/ffuf/ffuf/releases/latest | grep -o '"tag_name": "v[^"]*"' | cut -d'"' -f4 | sed 's/v//'); \
			  if [ "$$FFUF_VERSION" ]; then \
				ARCH=$$(dpkg --print-architecture 2>/dev/null || echo "amd64"); \
				if [ "$$ARCH" = "amd64" ]; then FFUF_ARCH="linux_amd64"; \
				elif [ "$$ARCH" = "arm64" ]; then FFUF_ARCH="linux_arm64"; \
				else FFUF_ARCH="linux_amd64"; fi; \
				wget -q "https://github.com/ffuf/ffuf/releases/download/v$$FFUF_VERSION/ffuf_$${FFUF_VERSION}_$${FFUF_ARCH}.tar.gz" -O /tmp/ffuf.tar.gz && \
				sudo tar -xzf /tmp/ffuf.tar.gz -C /usr/local/bin/ ffuf && \
				sudo chmod +x /usr/local/bin/ffuf && \
				rm -f /tmp/ffuf.tar.gz && \
				echo "  ✅ ffuf installed from GitHub"; \
			  else \
				echo "  ⚠️  Could not determine ffuf version, skipping"; \
			  fi; }; \
		else \
			echo "  ✅ ffuf already installed"; \
		fi; \
		sudo apt install -y zaproxy burpsuite metasploit-framework 2>/dev/null || echo "  ⚠️  Some GUI tools may not be available"; \
		echo "✅ Complete penetration testing environment installed!"; \
	elif [ -f /etc/arch-release ]; then \
		echo "🐧 Arch Linux detected - Installing base tools..."; \
		sudo pacman -S --noconfirm python python-pip nmap curl; \
		echo "🔧 Installing penetration testing tools..."; \
		sudo pacman -S --noconfirm nmap masscan gobuster nikto smbclient; \
		echo "  ⚠️  Some tools may need to be installed from AUR"; \
	elif [ -f /etc/redhat-release ]; then \
		echo "🐧 RedHat/CentOS/Fedora detected - Installing base tools..."; \
		sudo dnf install -y python3 python3-pip nmap curl; \
 \
		echo "🔧 Installing available penetration testing tools..."; \
		sudo dnf install -y nmap smbclient; \
		echo "  ⚠️  Additional tools may need manual installation"; \
	else \
		echo "❓ Unknown OS - Installing basic requirements..."; \
		echo "  Please install manually: python3, pip, nmap, curl"; \
	fi
	@echo "🔍 Checking for remaining missing tools..."
	@missing_tools=""; \
	for tool in nmap curl dnsrecon enum4linux feroxbuster gobuster nikto smbclient; do \
		if ! command -v $$tool >/dev/null 2>&1; then \
			missing_tools="$$missing_tools $$tool"; \
		fi; \
	done; \
	if [ -n "$$missing_tools" ]; then \
		echo "⚠️  Missing tools:$$missing_tools"; \
		echo "💡 These tools are optional but recommended for full functionality"; \
	else \
		echo "✅ All essential tools are available"; \
	fi
	@echo "🚀 Installing IPCrawler..."
	@echo "📦 Installing Python dependencies..."
	@python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || \
	 python3 -m pip install -r requirements.txt 2>/dev/null || \
	 echo "⚠️  Failed to install dependencies. Please install manually: pip3 install -r requirements.txt"
	@echo "🔗 Creating user-local symlink..."
	@mkdir -p $(HOME)/.local/bin
	@chmod +x $(CURDIR)/ipcrawler.py
	@ln -fs $(CURDIR)/ipcrawler.py $(HOME)/.local/bin/ipcrawler
	@echo "✅ Installation complete!"
	@echo "🧪 Testing installation..."
	@$(HOME)/.local/bin/ipcrawler --version
	@echo "💡 Updates: Use 'git pull && make update' to get latest changes."

# Update everything
update:
	@echo "🔄 Updating IPCrawler..."
	@git pull
	@echo "✅ Update complete!"

# Clean ipcrawler only
clean:
	@echo "🧹 Cleaning ipcrawler..."
	@rm -f $(HOME)/.local/bin/ipcrawler
	@echo "🧹 Removing all IPCrawler system directories to ensure git-only operation..."
	@rm -rf "$$HOME/.config/IPCrawler" "$$HOME/.local/share/IPCrawler" 2>/dev/null || true
	@rm -rf "$$HOME/Library/Application Support/IPCrawler" 2>/dev/null || true
	@rm -rf "/root/.local/share/IPCrawler" 2>/dev/null || true
	@echo "🔧 Fixing results directory permissions..."
	@if [ -f "scripts/fix-permissions.sh" ]; then \
		bash scripts/fix-permissions.sh; \
	else \
		echo "⚠️  Permission fixing script not found, checking manually..."; \
		if [ -d "results" ]; then \
			ROOT_FILES=$$(find results -user root 2>/dev/null | wc -l | tr -d ' ' || echo "0"); \
			if [ "$$ROOT_FILES" -gt 0 ]; then \
				echo "⚠️  Found $$ROOT_FILES root-owned files in results directory"; \
				echo "💡 Run manually: sudo chown -R \$$USER:\$$(id -g) results/"; \
			fi; \
		fi; \
	fi
	@echo "✅ IPCrawler removed! (Tools and results preserved)"

# Clean everything including tools
clean-all: clean
	@echo "🧹 Complete cleanup - removing all installed tools..."
	@echo "⚠️  This will remove all penetration testing tools installed by this Makefile"
	@echo "📁 Results directory will be preserved"
	@echo "🧹 Removing all IPCrawler system directories to ensure git-only operation..."
	@rm -rf "$$HOME/.config/IPCrawler" "$$HOME/.local/share/IPCrawler" 2>/dev/null || true
	@rm -rf "$$HOME/Library/Application Support/IPCrawler" 2>/dev/null || true
	@rm -rf "/root/.local/share/IPCrawler" 2>/dev/null || true
	@# Remove tools based on platform
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "🍎 Removing macOS tools installed via Homebrew..."; \
		for tool in feroxbuster gobuster nikto masscan john hashcat; do \
			if brew list | grep -q "^$$tool$$"; then \
				echo "  Removing $$tool..."; \
				brew uninstall $$tool 2>/dev/null || true; \
			fi; \
		done; \
		echo "💡 Core tools (python3, pipx, nmap, curl) kept for system stability"; \
	elif [ -f /etc/debian_version ]; then \
		echo "🐧 Removing penetration testing tools on Debian/Ubuntu..."; \
		echo "  Note: This will only remove tools, not dependencies like python3/nmap"; \
		sudo apt remove --purge -y dnsrecon feroxbuster gobuster 2>/dev/null || true; \
		echo "  🗑️  Removing SecLists installation..."; \
		sudo rm -rf /usr/share/seclists 2>/dev/null || true; \
		sudo apt remove --purge -y enum4linux enum4linux-ng nbtscan nikto onesixtyone oscanner 2>/dev/null || true; \
		sudo apt remove --purge -y impacket-scripts python3-impacket 2>/dev/null || true; \
		sudo rm -rf /opt/enum4linux-ng 2>/dev/null || true; \
		sudo apt remove --purge -y redis-tools redis redis-server redis-cli smbmap sipvicious tnscmd10g whatweb 2>/dev/null || true; \
		sudo rm -f /usr/local/bin/redis-cli 2>/dev/null || true; \
		sudo apt remove --purge -y masscan dirb dirsearch john hashcat hydra medusa 2>/dev/null || true; \
		sudo apt remove --purge -y ncrack sqlmap wfuzz wpscan sublist3r amass fierce 2>/dev/null || true; \
		sudo apt remove --purge -y ffuf 2>/dev/null || true; \
		sudo snap remove ffuf 2>/dev/null || true; \
		sudo rm -f /usr/local/bin/ffuf 2>/dev/null || true; \
		sudo apt autoremove -y 2>/dev/null || true; \
		echo "💡 Core tools (python3, pipx, nmap, curl) kept for system stability"; \
	elif [ -f /etc/arch-release ]; then \
		echo "🐧 Removing tools on Arch Linux..."; \
		sudo pacman -R --noconfirm masscan gobuster nikto 2>/dev/null || true; \
		echo "💡 Core tools (python3, pipx, nmap, curl) kept for system stability"; \
	else \
		echo "❓ Unknown platform - manual tool removal may be required"; \
	fi
	@echo "🔧 Fixing results directory permissions..."
	@if [ -f "scripts/fix-permissions.sh" ]; then \
		bash scripts/fix-permissions.sh; \
	else \
		echo "⚠️  Permission fixing script not found, checking manually..."; \
		if [ -d "results" ]; then \
			ROOT_FILES=$$(find results -user root 2>/dev/null | wc -l | tr -d ' ' || echo "0"); \
			if [ "$$ROOT_FILES" -gt 0 ]; then \
				echo "⚠️  Found $$ROOT_FILES root-owned files in results directory"; \
				echo "💡 Run manually: sudo chown -R \$$USER:\$$(id -g) results/"; \
			fi; \
		fi; \
	fi
	@echo "📊 Checking results directory..."
	@if [ -d "results" ]; then \
		echo "✅ Results directory preserved with $$(find results -type f | wc -l) files"; \
	else \
		echo "ℹ️  No results directory found"; \
	fi
	@echo "🗑️  Complete cleanup finished! All tools removed, results preserved."

# Fix file permissions in results directory
fix-permissions:
	@echo "🔧 IPCrawler Permission Fixer"
	@echo "============================="
	@if [ -f "scripts/fix-permissions.sh" ]; then \
		bash scripts/fix-permissions.sh; \
	else \
		echo "❌ Permission fixing script not found at scripts/fix-permissions.sh"; \
		echo "💡 This script fixes ownership of results directory files created by root"; \
		echo "💡 Manual fix: sudo chown -R \$$USER:\$$(id -g) results/"; \
		exit 1; \
	fi

# System diagnostics with comprehensive tool detection and venv-free verification
debug:
	@echo "🔬 IPCrawler System Diagnostics"
	@echo "================================"
	@echo ""
	@echo "📋 System Information"
	@echo "OS: $$(uname -s) $$(uname -r)"
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "Platform: macOS (Limited tool availability via Homebrew)"; \
		echo "Package Manager: Homebrew"; \
	elif [ -f /etc/debian_version ]; then \
		if [ -f /etc/kali_version ]; then \
			echo "Platform: Kali Linux (Excellent penetration testing support)"; \
		else \
			echo "Platform: Debian/Ubuntu (Good penetration testing support)"; \
		fi; \
		echo "Package Manager: APT"; \
	elif [ -f /etc/arch-release ]; then \
		echo "Platform: Arch Linux (Manual tool installation required)"; \
		echo "Package Manager: Pacman"; \
	else \
		echo "Platform: $$(uname -s) (Unknown - manual setup required)"; \
	fi
	@echo "Shell: $$SHELL"
	@echo "User: $$(whoami)"
	@echo "Current Directory: $$(pwd)"
	@echo ""
	@echo "🐍 Python Environment"
	@echo "Python Version: $$(python3 --version 2>/dev/null || echo 'Not found')"
	@echo "Python Binary: $$(which python3 2>/dev/null || echo 'Not in PATH')"
	@echo "Pip Version: $$(python3 -m pip --version 2>/dev/null || echo 'Not found')"
	@echo "Python Module Path:"
	@python3 -c "import sys; print('  ' + '\\n  '.join(sys.path[:3]))" 2>/dev/null || echo "  ❌ Cannot access Python"
	@echo ""
	@echo "🕷️  IPCrawler Installation & Configuration"
	@echo "IPCrawler Binary: $$(which ipcrawler 2>/dev/null || echo 'Not in PATH')"
	@if [ -L "$$(which ipcrawler 2>/dev/null)" ]; then \
		echo "Installation Type: Symlink (✅ venv-free)"; \
		echo "Symlink Target: $$(readlink $$(which ipcrawler))"; \
		if [ -f "$$(readlink $$(which ipcrawler))" ]; then \
			echo "Target Status: ✅ Valid"; \
		else \
			echo "Target Status: ❌ Broken symlink"; \
		fi; \
	elif command -v ipcrawler >/dev/null 2>&1; then \
		echo "Installation Type: ⚠️  Other (may use venv)"; \
	else \
		echo "Installation Type: ❌ Not installed"; \
	fi
	@echo "IPCrawler Script: $$(ls -la $(CURDIR)/ipcrawler.py 2>/dev/null || echo 'ipcrawler.py not found')"
	@if [ -f "$(CURDIR)/ipcrawler.py" ]; then \
		echo "Script Executable: $$([ -x $(CURDIR)/ipcrawler.py ] && echo '✅ Yes' || echo '❌ No')"; \
		shebang=$$(head -1 $(CURDIR)/ipcrawler.py); \
		if [ "$$shebang" = "#!/usr/bin/env python3" ]; then \
			echo "Shebang: ✅ Correct ($$shebang)"; \
		else \
			echo "Shebang: ⚠️  $$shebang"; \
		fi; \
	fi
	@echo ""
	@echo "🔧 IPCrawler Functionality Test"
	@if command -v ipcrawler >/dev/null 2>&1; then \
		echo "Version Check:"; \
		if ipcrawler --version >/dev/null 2>&1; then \
			echo "  ✅ IPCrawler runs successfully"; \
			if ipcrawler --tools-check >/dev/null 2>&1; then \
				echo "  ✅ Tool validation passes"; \
			else \
				echo "  ⚠️  Tool validation issues detected"; \
			fi; \
		else \
			echo "  ❌ IPCrawler fails to run"; \
		fi; \
	else \
		echo "❌ IPCrawler command not available"; \
		echo "   💡 Run 'make install' to install"; \
	fi
	@echo ""
	@echo "📚 Wordlists & Security Lists"
	@echo "SecLists Detection:"
	@seclists_found=0; \
	for path in "$$HOME/tools/wordlists/seclists" "$$HOME/tools/wordlists/SecLists" "$$HOME/tools/SecLists" "/usr/share/seclists" "/usr/share/SecLists" "/opt/SecLists" "$$HOME/SecLists"; do \
		if [ -d "$$path" ]; then \
			echo "  ✅ SecLists: $$path"; \
			seclists_found=1; \
			if [ -f "$$path/Discovery/Web-Content/common.txt" ]; then \
				echo "    └─ Web Content: ✅"; \
			fi; \
			if [ -f "$$path/Discovery/DNS/subdomains-top1million-110000.txt" ]; then \
				echo "    └─ DNS/Subdomains: ✅"; \
			fi; \
			if [ -f "$$path/Usernames/top-usernames-shortlist.txt" ]; then \
				echo "    └─ Usernames: ✅"; \
			fi; \
			if [ -f "$$path/Passwords/Common-Credentials/darkweb2017_top-100.txt" ]; then \
				echo "    └─ Passwords: ✅"; \
			elif [ -f "$$path/Passwords/darkweb2017-top100.txt" ]; then \
				echo "    └─ Passwords: ✅ (alt structure)"; \
			fi; \
			break; \
		fi; \
	done; \
	if [ $$seclists_found -eq 0 ]; then \
		echo "  ❌ SecLists not found"; \
	fi
	@echo "Additional Wordlists:"
	@if [ -d "$$HOME/tools/wordlists/jhaddix" ]; then \
		echo "  ✅ Jhaddix All.txt: $$HOME/tools/wordlists/jhaddix/"; \
		if [ -f "$$HOME/tools/wordlists/jhaddix/jhaddix-all.txt" ]; then \
			file_size=$$(du -h "$$HOME/tools/wordlists/jhaddix/jhaddix-all.txt" 2>/dev/null | cut -f1 || echo "unknown"); \
			echo "    └─ File present: ✅ ($$file_size)"; \
		else \
			echo "    └─ File missing: ❌"; \
		fi; \
	else \
		echo "  ❌ Jhaddix All.txt not found"; \
	fi
	@if [ -d "$$HOME/tools/wordlists/onelistforall" ]; then \
		echo "  ✅ OneListForAll: $$HOME/tools/wordlists/onelistforall/"; \
		if [ -f "$$HOME/tools/wordlists/onelistforall/onelistforall.txt" ]; then \
			file_size=$$(du -h "$$HOME/tools/wordlists/onelistforall/onelistforall.txt" 2>/dev/null | cut -f1 || echo "unknown"); \
			echo "    └─ Main wordlist: ✅ ($$file_size)"; \
		elif [ -f "$$HOME/tools/wordlists/onelistforall/onelistforallshort.txt" ]; then \
			file_size=$$(du -h "$$HOME/tools/wordlists/onelistforall/onelistforallshort.txt" 2>/dev/null | cut -f1 || echo "unknown"); \
			echo "    └─ Short wordlist: ✅ ($$file_size)"; \
		elif [ -f "$$HOME/tools/wordlists/onelistforall/onelistforallmicro.txt" ]; then \
			file_size=$$(du -h "$$HOME/tools/wordlists/onelistforall/onelistforallmicro.txt" 2>/dev/null | cut -f1 || echo "unknown"); \
			echo "    └─ Micro wordlist: ✅ ($$file_size)"; \
		else \
			echo "    └─ Main wordlists: ❌ (archived in 7z)"; \
		fi; \
		txt_files=$$(find "$$HOME/tools/wordlists/onelistforall/" -name "*.txt" 2>/dev/null | wc -l | tr -d ' '); \
		if [ "$$txt_files" -gt 0 ]; then \
			echo "    └─ Total wordlist files: $$txt_files"; \
		else \
			echo "    └─ No wordlist files found: ❌"; \
		fi; \
	else \
		echo "  ❌ OneListForAll not found"; \
	fi
	@echo ""
	@echo "🔧 Core Tools (Essential)"
	@core_tools="python3 pip nmap curl git"; \
	core_missing=0; \
	for tool in $$core_tools; do \
		if command -v $$tool >/dev/null 2>&1; then \
			version=$$($$tool --version 2>/dev/null | head -1 | cut -d' ' -f2- || echo 'unknown'); \
			echo "  ✅ $$tool: $$version"; \
			echo "    └─ Path: $$(which $$tool)"; \
		else \
			echo "  ❌ $$tool: Not found"; \
			core_missing=$$((core_missing + 1)); \
		fi; \
	done
	@echo ""
	@echo "🎯 Directory Busting Tools"
	@dirb_tools="feroxbuster gobuster ffuf dirsearch dirb"; \
	dirb_found=0; \
	for tool in $$dirb_tools; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "  ✅ $$tool: $$(which $$tool)"; \
			dirb_found=$$((dirb_found + 1)); \
		else \
			echo "  ⚠️  $$tool: Not available"; \
		fi; \
	done; \
	echo "  📊 Available: $$dirb_found/5 tools"
	@echo ""
	@echo "🌐 Network Enumeration Tools"
	@net_tools="dnsrecon nikto smbclient masscan whatweb sslscan"; \
	net_found=0; \
	for tool in $$net_tools; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "  ✅ $$tool: $$(which $$tool)"; \
			net_found=$$((net_found + 1)); \
		else \
			echo "  ⚠️  $$tool: Not available"; \
		fi; \
	done; \
	echo "  📊 Available: $$net_found/7 tools"
	@echo ""
	@echo "🔍 Specialized Security Tools"
	@# Enhanced impacket detection
	@if python3 -c "import impacket" 2>/dev/null; then \
		echo "  ✅ impacket: Python module available"; \
		if command -v impacket-scripts >/dev/null 2>&1; then \
			echo "    └─ Scripts: $$(which impacket-scripts)"; \
		elif ls /usr/share/doc/python3-impacket/examples/ 2>/dev/null | head -1 >/dev/null; then \
			echo "    └─ Scripts: /usr/share/doc/python3-impacket/examples/"; \
		fi; \
	else \
		echo "  ⚠️  impacket: Not available"; \
	fi
	@# Enhanced enum4linux detection
	@if command -v enum4linux-ng >/dev/null 2>&1; then \
		echo "  ✅ enum4linux-ng: $$(which enum4linux-ng)"; \
	elif command -v enum4linux >/dev/null 2>&1; then \
		echo "  ✅ enum4linux: $$(which enum4linux)"; \
	else \
		echo "  ⚠️  enum4linux: Not available"; \
	fi
	@# Additional specialized tools
	@spec_tools="nbtscan onesixtyone oscanner smbmap snmpwalk hydra sqlmap john hashcat"; \
	spec_found=0; \
	for tool in $$spec_tools; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "  ✅ $$tool: $$(which $$tool)"; \
			spec_found=$$((spec_found + 1)); \
		else \
			echo "  ⚠️  $$tool: Not available"; \
		fi; \
	done; \
	echo "  📊 Available: $$spec_found/10 tools"
	@echo ""
	@echo "🔍 Path Independence Verification"
	@echo "Current PATH:"
	@echo "$$PATH" | tr ':' '\n' | head -10 | sed 's/^/  /'
	@if echo "$$PATH" | grep -q ".venv"; then \
		echo "  ⚠️  Virtual environment detected in PATH"; \
	else \
		echo "  ✅ No virtual environment in PATH"; \
	fi
	@if [ -f "$(CURDIR)/.venv/bin/python" ]; then \
		echo "  ⚠️  Virtual environment exists in project"; \
	else \
		echo "  ✅ No virtual environment in project"; \
	fi
	@echo ""
	@echo "📊 System Readiness Summary"
	@core_missing=0; \
	for tool in python3 pip nmap curl git; do \
		if ! command -v $$tool >/dev/null 2>&1; then \
			core_missing=$$((core_missing + 1)); \
		fi; \
	done; \
	dirb_available=0; \
	for tool in feroxbuster gobuster ffuf dirsearch dirb; do \
		if command -v $$tool >/dev/null 2>&1; then \
			dirb_available=1; \
			break; \
		fi; \
	done; \
	seclists_available=0; \
	for path in "/usr/share/seclists" "/usr/share/SecLists" "/opt/SecLists" "$$HOME/tools/SecLists" "$$HOME/SecLists"; do \
		if [ -d "$$path" ]; then \
			seclists_available=1; \
			break; \
		fi; \
	done; \
	ipcrawler_working=0; \
	if command -v ipcrawler >/dev/null 2>&1 && ipcrawler --version >/dev/null 2>&1; then \
		ipcrawler_working=1; \
	fi; \
	if [ $$core_missing -eq 0 ] && [ $$dirb_available -eq 1 ] && [ $$seclists_available -eq 1 ] && [ $$ipcrawler_working -eq 1 ]; then \
		echo "✅ System fully ready for IPCrawler!"; \
		echo "   • All core tools present"; \
		echo "   • Directory busting tools available"; \
		echo "   • Wordlists installed"; \
		echo "   • IPCrawler operational"; \
	elif [ $$core_missing -gt 0 ]; then \
		echo "❌ Missing $$core_missing essential tools"; \
		echo "   💡 Run 'make install' to install required tools"; \
	elif [ $$ipcrawler_working -eq 0 ]; then \
		echo "❌ IPCrawler not working properly"; \
		echo "   💡 Run 'make install' to fix installation"; \
	else \
		echo "⚠️  System partially ready"; \
		echo "   💡 Run 'make install' to install missing components"; \
	fi

# Development installation - same as install but explicit
dev-install: install
	@echo "💡 'make install' now automatically sets up live updates when run from git repo"

# Testing targets
test: test-unit test-integration test-e2e

test-unit:
	@echo "🧪 Running unit tests..."
	@python3 -m pytest tests/test_config.py tests/test_yaml_plugins_simple.py -v

test-integration:
	@echo "🔗 Running integration tests..."
	@python3 tests/test_targets_simple.py

test-e2e:
	@echo "🌐 Running end-to-end tests..."
	@python3 ipcrawler.py --version
	@echo "✅ E2E: Version check passed"

coverage:
	@echo "📊 Generating coverage report..."
	@python3 -m pytest tests/test_config.py tests/test_yaml_plugins_simple.py --cov=ipcrawler --cov-report=html --cov-report=term-missing
	@echo "📈 Coverage report generated in htmlcov/"

lint:
	@echo "🔍 Running code quality checks..."
	@command -v flake8 >/dev/null 2>&1 && flake8 ipcrawler/ --count --select=E9,F63,F7,F82 --show-source --statistics || echo "⚠️ flake8 not installed"
	@command -v black >/dev/null 2>&1 && black --check ipcrawler/ || echo "⚠️ black not installed"
	@command -v isort >/dev/null 2>&1 && isort --check-only ipcrawler/ || echo "⚠️ isort not installed"

security-scan:
	@echo "🔒 Running security scans..."
	@command -v bandit >/dev/null 2>&1 && bandit -r ipcrawler/ || echo "⚠️ bandit not installed"
	@command -v safety >/dev/null 2>&1 && safety check || echo "⚠️ safety not installed"

# Clean test artifacts
clean-test:
	@echo "🧹 Cleaning test artifacts..."
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -f .coverage
	@rm -f coverage.xml
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -delete