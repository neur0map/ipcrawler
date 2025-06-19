# IPCrawler Makefile - Simple installation and management

.PHONY: install clean update debug help

# Default target
help:
	@echo "IPCrawler Management"
	@echo "==================="
	@echo "  make install  - Install ipcrawler and all tools"
	@echo "  make update   - Update to latest version"
	@echo "  make clean    - Remove everything (keeps results)"
	@echo "  make debug    - Show system diagnostics"
	@echo ""

# Complete installation with tool detection
install:
	@echo "🚀 Installing IPCrawler..."
	@echo "🔍 Detecting system and missing tools..."
	@# Detect OS and install basic tools + pipx
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "📱 macOS detected - Installing base tools..."; \
		brew install python3 pipx nmap curl 2>/dev/null || true; \
		echo "🔧 Checking and installing missing penetration testing tools..."; \
		for tool in feroxbuster gobuster nikto smbclient dnsrecon enum4linux masscan; do \
			if ! command -v $$tool >/dev/null 2>&1; then \
				echo "  Installing $$tool..."; \
				brew install $$tool 2>/dev/null || echo "  ⚠️  $$tool not available via brew"; \
			fi; \
		done; \
	elif [ -f /etc/debian_version ]; then \
		echo "🐧 Debian/Ubuntu detected - Installing base tools..."; \
		sudo apt update; \
		sudo apt install -y python3 python3-pip python3-venv curl nmap; \
		python3 -m pip install --user pipx && python3 -m pipx ensurepath; \
		echo "🔧 Installing penetration testing tools..."; \
		sudo apt install -y seclists dnsrecon enum4linux feroxbuster gobuster; \
		sudo apt install -y impacket-scripts nbtscan nikto onesixtyone oscanner; \
		sudo apt install -y redis-tools smbclient smbmap snmp sslscan sipvicious; \
		sudo apt install -y tnscmd10g whatweb masscan dirb dirsearch; \
		echo "📦 Installing additional tools via snap/other sources..."; \
		sudo snap install ffuf 2>/dev/null || echo "  ⚠️  ffuf not available via snap"; \
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
	@echo "✅ Installation complete! Run 'ipcrawler --version' to test."

# Update everything
update:
	@echo "🔄 Updating IPCrawler..."
	@git pull 2>/dev/null || true
	@pipx upgrade ipcrawler || pipx install --force git+https://github.com/neur0map/ipcrawler.git
	@echo "✅ Update complete!"

# Clean everything
clean:
	@echo "🧹 Cleaning up..."
	@pipx uninstall ipcrawler 2>/dev/null || true
	@rm -rf "$$HOME/.config/IPCrawler" "$$HOME/.local/share/IPCrawler" 2>/dev/null || true
	@rm -rf "$$HOME/Library/Application Support/IPCrawler" 2>/dev/null || true
	@echo "✅ Cleanup complete! (Results directory preserved)"

# System diagnostics with tool detection
debug:
	@echo "🔬 System Diagnostics"
	@echo "===================="
	@echo "OS: $$(uname -s) $$(uname -r)"
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