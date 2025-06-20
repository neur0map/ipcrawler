# IPCrawler Makefile - Simple installation and management

.PHONY: install clean clean-all update debug help dev-install

# Default target
help:
	@echo "IPCrawler Management"
	@echo "==================="
	@echo "  make install     - Install ipcrawler and all tools"
	@echo "  make dev-install - Install for development (live code updates)"
	@echo "  make update      - Update to latest version"
	@echo "  make clean       - Remove ipcrawler only (keeps tools & results)"
	@echo "  make clean-all   - Remove everything including tools (keeps results)"
	@echo "  make debug       - Show system diagnostics"
	@echo ""

# Complete installation with tool detection
install:
	@echo "🚀 Installing IPCrawler..."
	@echo "🔍 Detecting system and missing tools..."
	@# Detect OS and install basic tools + pipx
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "📱 macOS detected - Installing base tools..."; \
		brew install python3 pipx nmap curl 2>/dev/null || true; \
		echo "🔧 Installing available penetration testing tools..."; \
		available_tools="feroxbuster gobuster nikto smbclient masscan john hashcat"; \
		unavailable_tools="dnsrecon enum4linux impacket-scripts nbtscan onesixtyone oscanner smbmap tnscmd10g"; \
		for tool in $$available_tools; do \
			if ! command -v $$tool >/dev/null 2>&1; then \
				echo "  Installing $$tool..."; \
				brew install $$tool 2>/dev/null || echo "  ⚠️  $$tool failed to install"; \
			fi; \
		done; \
		echo "📝 Note: Some tools are not available on macOS via Homebrew:"; \
		echo "   Missing: $$unavailable_tools"; \
		echo "   💡 For complete tool coverage, use Linux (Kali/Ubuntu) instead"; \
		echo "🔧 Installing SecLists wordlists..."; \
		if [ ! -d "/usr/local/share/seclists" ] && [ ! -d "/opt/SecLists" ]; then \
			echo "  📦 Installing SecLists from GitHub..."; \
			sudo mkdir -p /opt 2>/dev/null || mkdir -p ~/tools 2>/dev/null; \
			if [ -w /opt ]; then \
				git clone --depth 1 https://github.com/danielmiessler/SecLists.git /opt/SecLists 2>/dev/null && \
				sudo ln -sf /opt/SecLists /usr/local/share/seclists 2>/dev/null || \
				echo "  ✅ SecLists installed to /opt/SecLists"; \
			else \
				git clone --depth 1 https://github.com/danielmiessler/SecLists.git ~/tools/SecLists 2>/dev/null && \
				echo "  ✅ SecLists installed to ~/tools/SecLists"; \
			fi; \
		else \
			echo "  ✅ SecLists already installed"; \
		fi; \
	elif [ -f /etc/debian_version ]; then \
		echo "🐧 Debian/Ubuntu detected - Installing complete penetration testing suite..."; \
		sudo apt update; \
		echo "  📦 Installing base tools..."; \
		sudo apt install -y python3 python3-pip python3-venv curl nmap; \
		python3 -m pip install --user pipx && python3 -m pipx ensurepath; \
		echo "  🔧 Installing core penetration testing tools..."; \
		sudo apt install -y seclists dnsrecon gobuster; \
		echo "  🔧 Installing feroxbuster..."; \
		if ! command -v feroxbuster >/dev/null 2>&1; then \
			sudo apt install -y feroxbuster 2>/dev/null || \
			{ echo "  📦 Installing feroxbuster from GitHub releases..."; \
			  FEROX_VERSION=$$(curl -s https://api.github.com/repos/epi052/feroxbuster/releases/latest | grep -o '"tag_name": "v[^"]*"' | cut -d'"' -f4 | sed 's/v//'); \
			  if [ "$$FEROX_VERSION" ]; then \
				ARCH=$$(dpkg --print-architecture 2>/dev/null || echo "amd64"); \
				if [ "$$ARCH" = "amd64" ]; then FEROX_ARCH="x86_64-linux"; \
				elif [ "$$ARCH" = "arm64" ]; then FEROX_ARCH="aarch64-linux"; \
				else FEROX_ARCH="x86_64-linux"; fi; \
				wget -q "https://github.com/epi052/feroxbuster/releases/download/v$$FEROX_VERSION/feroxbuster_$${FEROX_ARCH}.zip" -O /tmp/feroxbuster.zip && \
				sudo unzip -j /tmp/feroxbuster.zip feroxbuster -d /usr/local/bin/ && \
				sudo chmod +x /usr/local/bin/feroxbuster && \
				rm -f /tmp/feroxbuster.zip && \
				echo "  ✅ feroxbuster installed from GitHub"; \
			  else \
				echo "  ⚠️  Could not install feroxbuster automatically. Install manually with: apt install feroxbuster"; \
			  fi; }; \
		else \
			echo "  ✅ feroxbuster already installed"; \
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
		sudo pacman -S --noconfirm python python-pip python-pipx nmap curl; \
		echo "🔧 Installing penetration testing tools..."; \
		sudo pacman -S --noconfirm nmap masscan gobuster nikto smbclient; \
		echo "  ⚠️  Some tools may need to be installed from AUR"; \
	elif [ -f /etc/redhat-release ]; then \
		echo "🐧 RedHat/CentOS/Fedora detected - Installing base tools..."; \
		sudo dnf install -y python3 python3-pip nmap curl; \
		python3 -m pip install --user pipx && python3 -m pipx ensurepath; \
		echo "🔧 Installing available penetration testing tools..."; \
		sudo dnf install -y nmap smbclient; \
		echo "  ⚠️  Additional tools may need manual installation"; \
	else \
		echo "❓ Unknown OS - Installing basic requirements..."; \
		echo "  Please install manually: python3, pip, pipx, nmap, curl"; \
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
	@if [ -f "pyproject.toml" ] && [ -f "ipcrawler.py" ]; then \
		echo "📦 Local development environment detected, installing with live updates..."; \
		pipx uninstall ipcrawler 2>/dev/null || true; \
		if pipx install --editable . --force 2>/dev/null; then \
			echo "✅ Editable install successful! Code changes will take effect immediately."; \
		else \
			echo "⚠️  Editable install failed, using regular install..."; \
			pipx install . --force; \
			echo "💡 Run 'make install' again after code changes to update."; \
		fi; \
	else \
		echo "📦 Installing from GitHub repository..."; \
		pipx install --force git+https://github.com/neur0map/ipcrawler.git; \
	fi
	@pipx ensurepath
	@echo "✅ Installation complete! Run 'ipcrawler --version' to test."
	@echo "💡 Wordlist configuration will be auto-generated on first run."

# Update everything
update:
	@echo "🔄 Updating IPCrawler..."
	@git pull 2>/dev/null || true
	@pipx upgrade ipcrawler || pipx install --force git+https://github.com/neur0map/ipcrawler.git
	@echo "✅ Update complete!"

# Clean ipcrawler only
clean:
	@echo "🧹 Cleaning ipcrawler..."
	@pipx uninstall ipcrawler 2>/dev/null || true
	@rm -rf "$$HOME/.config/IPCrawler" "$$HOME/.local/share/IPCrawler" 2>/dev/null || true
	@rm -rf "$$HOME/Library/Application Support/IPCrawler" 2>/dev/null || true
	@echo "✅ IPCrawler removed! (Tools and results preserved)"

# Clean everything including tools
clean-all:
	@echo "🧹 Complete cleanup - removing all installed tools..."
	@echo "⚠️  This will remove all penetration testing tools installed by this Makefile"
	@echo "📁 Results directory will be preserved"
	@# Remove ipcrawler first
	@pipx uninstall ipcrawler 2>/dev/null || true
	@rm -rf "$$HOME/.config/IPCrawler" "$$HOME/.local/share/IPCrawler" 2>/dev/null || true
	@rm -rf "$$HOME/Library/Application Support/IPCrawler" 2>/dev/null || true
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
		sudo apt remove --purge -y seclists dnsrecon feroxbuster gobuster 2>/dev/null || true; \
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
	@echo "📊 Checking results directory..."
	@if [ -d "results" ]; then \
		echo "✅ Results directory preserved with $$(find results -type f | wc -l) files"; \
	else \
		echo "ℹ️  No results directory found"; \
	fi
	@echo "🗑️  Complete cleanup finished! All tools removed, results preserved."

# System diagnostics with tool detection
debug:
	@echo "🔬 System Diagnostics"
	@echo "===================="
	@echo "OS: $$(uname -s) $$(uname -r)"
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "Platform: macOS (Limited penetration testing tool availability)"; \
	elif [ -f /etc/debian_version ]; then \
		echo "Platform: Debian/Ubuntu (Excellent penetration testing tool support)"; \
	else \
		echo "Platform: $$(uname -s)"; \
	fi
	@echo "Python: $$(python3 --version 2>/dev/null || echo 'Not found')"
	@echo "Pipx: $$(pipx --version 2>/dev/null || echo 'Not found')"
	@echo "IPCrawler: $$(ipcrawler --version 2>/dev/null || echo 'Not installed')"
	@echo "IPCrawler location: $$(which ipcrawler 2>/dev/null || echo 'Not in PATH')"
	@echo ""
	@echo "Essential tools:"
	@for tool in python3 pipx nmap curl; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool ($$($$tool --version 2>/dev/null | head -1 || echo 'version unknown'))"; \
		else \
			echo "❌ $$tool"; \
		fi \
	done
	@echo ""
	@echo "Penetration testing tools:"
	@for tool in dnsrecon feroxbuster gobuster nikto smbclient masscan; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool"; \
		else \
			echo "⚠️  $$tool"; \
		fi \
	done
	@# Check enum4linux variants
	@if command -v enum4linux-ng >/dev/null 2>&1; then \
		echo "✅ enum4linux-ng"; \
	elif command -v enum4linux >/dev/null 2>&1; then \
		echo "✅ enum4linux"; \
	else \
		echo "⚠️  enum4linux (neither enum4linux nor enum4linux-ng found)"; \
	fi
	@echo ""
	@echo "Additional tools:"
	@for tool in nbtscan onesixtyone oscanner redis-tools smbmap snmpwalk sslscan tnscmd10g whatweb ffuf dirb dirsearch; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool"; \
		else \
			echo "⚠️  $$tool"; \
		fi \
	done
	@# Check impacket variants
	@if command -v impacket-scripts >/dev/null 2>&1; then \
		echo "✅ impacket-scripts"; \
	elif dpkg -l 2>/dev/null | grep -q python3-impacket; then \
		echo "✅ python3-impacket (package installed)"; \
	elif python3 -c "import impacket" 2>/dev/null; then \
		echo "✅ impacket (python module)"; \
	else \
		echo "⚠️  impacket-scripts (no impacket installation found)"; \
	fi

# Development installation - same as install but explicit
dev-install: install
	@echo "💡 'make install' now automatically sets up live updates when run from git repo"