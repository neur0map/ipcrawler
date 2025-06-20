# IPCrawler Makefile - Simple installation and management

.PHONY: install clean clean-all update debug help

# Default target
help:
	@echo "IPCrawler Management"
	@echo "==================="
	@echo "  make install   - Install ipcrawler and all tools"
	@echo "  make update    - Update to latest version"
	@echo "  make clean     - Remove ipcrawler only (keeps tools & results)"
	@echo "  make clean-all - Remove everything including tools (keeps results)"
	@echo "  make debug     - Show system diagnostics"
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
	elif [ -f /etc/debian_version ]; then \
		echo "🐧 Debian/Ubuntu detected - Installing complete penetration testing suite..."; \
		sudo apt update; \
		echo "  📦 Installing base tools..."; \
		sudo apt install -y python3 python3-pip python3-venv curl nmap; \
		python3 -m pip install --user pipx && python3 -m pipx ensurepath; \
		echo "  🔧 Installing core penetration testing tools..."; \
		sudo apt install -y seclists dnsrecon enum4linux feroxbuster gobuster; \
		sudo apt install -y impacket-scripts nbtscan nikto onesixtyone oscanner; \
		sudo apt install -y redis-tools smbclient smbmap snmp sslscan sipvicious; \
		sudo apt install -y tnscmd10g whatweb masscan dirb dirsearch; \
		sudo apt install -y john hashcat hydra medusa ncrack sqlmap; \
		sudo apt install -y wfuzz wpscan sublist3r amass fierce dnsutils; \
		echo "  📦 Installing additional tools..."; \
		sudo snap install ffuf 2>/dev/null || echo "  ⚠️  ffuf not available via snap"; \
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
	@echo "🚀 Installing IPCrawler from GitHub..."
	@pipx install --force git+https://github.com/neur0map/ipcrawler.git
	@pipx ensurepath
	@echo "📝 Setting up wordlist configuration..."
	@python3 -c "import os, toml, platformdirs; \
	config_dir = platformdirs.user_config_dir('IPCrawler'); \
	os.makedirs(config_dir, exist_ok=True); \
	wordlists_config = { \
		'mode': {'type': 'auto', 'auto_update': True, 'last_detection': None}, \
		'detected_paths': {'seclists_base': None, 'comment': 'Auto-generated paths - do not edit manually'}, \
		'custom_paths': {'comment': 'Add your custom wordlist paths here', 'examples': {'# usernames': '/path/to/custom/usernames.txt', '# passwords': '/path/to/custom/passwords.txt', '# web_directories': '/path/to/custom/web-dirs.txt'}}, \
		'builtin_paths': {'comment': 'Built-in wordlists shipped with ipcrawler', 'data_dir': None} \
	}; \
	with open(os.path.join(config_dir, 'wordlists.toml'), 'w') as f: toml.dump(wordlists_config, f)" 2>/dev/null || echo "  ⚠️  Could not create wordlists.toml (will be auto-generated on first run)"
	@echo "✅ Installation complete! Run 'ipcrawler --version' to test."

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
		sudo apt remove --purge -y seclists dnsrecon enum4linux feroxbuster gobuster 2>/dev/null || true; \
		sudo apt remove --purge -y impacket-scripts nbtscan nikto onesixtyone oscanner 2>/dev/null || true; \
		sudo apt remove --purge -y redis-tools smbmap sipvicious tnscmd10g whatweb 2>/dev/null || true; \
		sudo apt remove --purge -y masscan dirb dirsearch john hashcat hydra medusa 2>/dev/null || true; \
		sudo apt remove --purge -y ncrack sqlmap wfuzz wpscan sublist3r amass fierce 2>/dev/null || true; \
		sudo snap remove ffuf 2>/dev/null || true; \
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
	@for tool in dnsrecon enum4linux feroxbuster gobuster nikto smbclient masscan; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool"; \
		else \
			echo "⚠️  $$tool"; \
		fi \
	done
	@echo ""
	@echo "Additional tools:"
	@for tool in impacket-scripts nbtscan onesixtyone oscanner redis-tools smbmap snmpwalk sslscan tnscmd10g whatweb ffuf dirb dirsearch; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool"; \
		else \
			echo "⚠️  $$tool"; \
		fi \
	done