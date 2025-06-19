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

# Complete installation
install:
	@echo "🚀 Installing IPCrawler..."
	@# Detect OS and install tools
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "📱 Installing for macOS..."; \
		brew install python3 pipx nmap curl feroxbuster 2>/dev/null || true; \
	elif [ -f /etc/debian_version ]; then \
		echo "🐧 Installing for Debian/Ubuntu..."; \
		sudo apt update && sudo apt install -y python3 python3-pip python3-venv curl nmap seclists feroxbuster gobuster nikto smbclient; \
		python3 -m pip install --user pipx && python3 -m pipx ensurepath; \
	elif [ -f /etc/arch-release ]; then \
		echo "🐧 Installing for Arch Linux..."; \
		sudo pacman -S --noconfirm python python-pip python-pipx nmap curl; \
	fi
	@# Install ipcrawler globally
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

# System diagnostics
debug:
	@echo "🔬 System Diagnostics"
	@echo "===================="
	@echo "OS: $$(uname -s)"
	@echo "Python: $$(python3 --version 2>/dev/null || echo 'Not found')"
	@echo "Pipx: $$(pipx --version 2>/dev/null || echo 'Not found')"
	@echo "IPCrawler: $$(ipcrawler --version 2>/dev/null || echo 'Not installed')"
	@echo "IPCrawler location: $$(which ipcrawler 2>/dev/null || echo 'Not in PATH')"
	@echo ""
	@echo "Required tools:"
	@for tool in nmap curl; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool"; \
		else \
			echo "❌ $$tool"; \
		fi \
	done
	@echo ""
	@echo "Optional tools:"
	@for tool in feroxbuster gobuster nikto smbclient; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool"; \
		else \
			echo "⚠️  $$tool"; \
		fi \
	done