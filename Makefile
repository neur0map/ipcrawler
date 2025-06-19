# IPCrawler Makefile
# Handles installation, updates, cleaning, and debugging across different operating systems

.PHONY: install clean update debug help detect-os install-tools setup-ipcrawler detergent test-installation

# Default target
help:
	@echo "IPCrawler Setup and Management"
	@echo "=============================="
	@echo "Available commands:"
	@echo "  make install  - Complete installation (OS detection, tools, ipcrawler setup)"
	@echo "  make clean    - Complete cleanup (removes tools and ipcrawler records except results)"
	@echo "  make update   - Update ipcrawler and clear cache (preserves functionality)"
	@echo "  make debug    - Run comprehensive tests and diagnostics"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "Note: ipcrawler will be installed globally without local code copies."
	@echo "Updates are immediate via git pull or 'make update'."

# Main installation command
install: detect-os install-tools setup-ipcrawler test-installation
	@echo "✅ Installation complete! You can now run 'ipcrawler' from anywhere."

# OS Detection
detect-os:
	@echo "🔍 Detecting operating system..."
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "📱 macOS detected"; \
		echo "MACOS" > .os_detected; \
	elif [ "$$(uname)" = "Linux" ]; then \
		if [ -f /etc/debian_version ]; then \
			echo "🐧 Debian/Ubuntu Linux detected"; \
			echo "DEBIAN" > .os_detected; \
		elif [ -f /etc/redhat-release ]; then \
			echo "🐧 RedHat/CentOS/Fedora Linux detected"; \
			echo "REDHAT" > .os_detected; \
		elif [ -f /etc/arch-release ]; then \
			echo "🐧 Arch Linux detected"; \
			echo "ARCH" > .os_detected; \
		else \
			echo "🐧 Generic Linux detected"; \
			echo "LINUX" > .os_detected; \
		fi \
	else \
		echo "❓ Unknown OS detected"; \
		echo "UNKNOWN" > .os_detected; \
	fi

# Tool installation based on OS
install-tools: detect-os
	@echo "🔧 Installing required tools..."
	@OS=$$(cat .os_detected); \
	if [ "$$OS" = "MACOS" ]; then \
		echo "Installing tools for macOS..."; \
		if ! command -v brew >/dev/null 2>&1; then \
			echo "❌ Homebrew not found. Installing Homebrew..."; \
			/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
		fi; \
		brew install python3 pipx nmap curl; \
		brew install --cask --quiet feroxbuster 2>/dev/null || brew install feroxbuster; \
	elif [ "$$OS" = "DEBIAN" ]; then \
		echo "Installing tools for Debian/Ubuntu..."; \
		sudo apt update; \
		sudo apt install -y python3 python3-pip python3-venv curl nmap; \
		sudo apt install -y seclists dnsrecon enum4linux feroxbuster gobuster; \
		sudo apt install -y impacket-scripts nbtscan nikto onesixtyone oscanner; \
		sudo apt install -y redis-tools smbclient smbmap snmp sslscan sipvicious; \
		sudo apt install -y tnscmd10g whatweb; \
		if ! command -v pipx >/dev/null 2>&1; then \
			python3 -m pip install --user pipx; \
			python3 -m pipx ensurepath; \
		fi; \
	elif [ "$$OS" = "ARCH" ]; then \
		echo "Installing tools for Arch Linux..."; \
		sudo pacman -Sy --noconfirm python python-pip python-pipx; \
		sudo pacman -S --noconfirm nmap curl; \
		echo "⚠️  Some tools may need to be installed from AUR"; \
	else \
		echo "⚠️  Please install Python 3, pip, pipx, and nmap manually for your OS"; \
	fi; \
	rm -f .os_detected

# IPCrawler setup
setup-ipcrawler:
	@echo "🚀 Setting up IPCrawler..."
	@if ! command -v pipx >/dev/null 2>&1; then \
		echo "❌ pipx not found. Please ensure pipx is installed and in PATH."; \
		echo "💡 You may need to restart your terminal or run: source ~/.bashrc"; \
		exit 1; \
	fi
	@echo "📦 Installing IPCrawler from GitHub repository..."
	@pipx install --force git+https://github.com/neur0map/ipcrawler.git
	@echo "🔗 Setting up global command access..."
	@pipx ensurepath
	@if ! command -v ipcrawler >/dev/null 2>&1; then \
		echo "⚠️  'ipcrawler' command not found in PATH."; \
		echo "🤔 Would you like to modify your PATH to make 'ipcrawler' globally accessible? (y/n)"; \
		read -r response; \
		if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
			echo "📝 Adding pipx binary directory to PATH..."; \
			echo 'export PATH="$$HOME/.local/bin:$$PATH"' >> ~/.bashrc; \
			echo 'export PATH="$$HOME/.local/bin:$$PATH"' >> ~/.zshrc 2>/dev/null || true; \
			echo "✅ PATH updated. Please restart your terminal or run: source ~/.bashrc"; \
		else \
			echo "ℹ️  You can run IPCrawler using: python3 -m ipcrawler or ~/.local/bin/ipcrawler"; \
		fi \
	fi

# Test installation
test-installation:
	@echo "🧪 Testing installation..."
	@if command -v ipcrawler >/dev/null 2>&1; then \
		echo "✅ ipcrawler command is available globally"; \
		ipcrawler --version; \
	else \
		echo "⚠️  ipcrawler command not in PATH, testing direct execution..."; \
		if [ -f ~/.local/bin/ipcrawler ]; then \
			~/.local/bin/ipcrawler --version; \
			echo "✅ ipcrawler works via direct path"; \
		else \
			echo "❌ ipcrawler installation failed"; \
			exit 1; \
		fi \
	fi

# Complete cleanup
clean: detect-os detergent
	@echo "🧹 Complete cleanup finished!"

# Detergent - thorough cleanup
detergent: detect-os
	@echo "🧽 Performing thorough cleanup..."
	@OS=$$(cat .os_detected); \
	echo "🗑️  Removing IPCrawler installation..."; \
	pipx uninstall ipcrawler 2>/dev/null || true; \
	echo "📁 Removing IPCrawler configuration and cache directories..."; \
	rm -rf "$$HOME/.local/share/IPCrawler" 2>/dev/null || true; \
	rm -rf "$$HOME/.config/IPCrawler" 2>/dev/null || true; \
	rm -rf "$$HOME/Library/Application Support/IPCrawler" 2>/dev/null || true; \
	rm -rf "$$HOME/.cache/ipcrawler" 2>/dev/null || true; \
	if [ "$$OS" = "MACOS" ]; then \
		echo "🍎 Cleaning macOS specific locations..."; \
		rm -rf "$$HOME/Library/Caches/ipcrawler" 2>/dev/null || true; \
		rm -rf "$$HOME/Library/Preferences/ipcrawler" 2>/dev/null || true; \
	elif [ "$$OS" = "DEBIAN" ] || [ "$$OS" = "LINUX" ]; then \
		echo "🐧 Cleaning Linux specific locations..."; \
		rm -rf "$$HOME/.local/share/ipcrawler" 2>/dev/null || true; \
	fi; \
	echo "🐍 Clearing Python cache..."; \
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; \
	find . -name "*.pyc" -delete 2>/dev/null || true; \
	echo "📊 Preserving results directory..."; \
	if [ -d "results" ]; then \
		echo "✅ Results directory preserved"; \
	fi; \
	rm -f .os_detected; \
	echo "✨ Cleanup complete! Results directory preserved."

# Update IPCrawler
update:
	@echo "🔄 Updating IPCrawler..."
	@if [ -d ".git" ]; then \
		echo "📡 Pulling latest changes from repository..."; \
		git pull origin main; \
		echo "🔄 Updating IPCrawler installation..."; \
		pipx upgrade ipcrawler || pipx install --force git+https://github.com/neur0map/ipcrawler.git; \
	else \
		echo "🔄 Updating IPCrawler installation..."; \
		pipx upgrade ipcrawler || pipx install --force git+https://github.com/neur0map/ipcrawler.git; \
	fi
	@echo "🧹 Clearing safe cache (preserving functionality)..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Update complete!"

# Debug and diagnostics
debug: detect-os
	@echo "🔬 Running comprehensive diagnostics..."
	@OS=$$(cat .os_detected); \
	echo ""; \
	echo "=== SYSTEM INFORMATION ==="; \
	echo "OS: $$OS"; \
	echo "Python version: $$(python3 --version 2>/dev/null || echo 'Not found')"; \
	echo "Pip version: $$(pip3 --version 2>/dev/null || echo 'Not found')"; \
	echo "Pipx version: $$(pipx --version 2>/dev/null || echo 'Not found')"; \
	echo ""; \
	echo "=== PATH ANALYSIS ==="; \
	echo "Current PATH: $$PATH"; \
	echo "IPCrawler location: $$(which ipcrawler 2>/dev/null || echo 'Not in PATH')"; \
	echo "Home bin directory: $$(ls -la $$HOME/.local/bin/ipcrawler 2>/dev/null || echo 'Not found')"; \
	echo ""; \
	echo "=== IPCRAWLER TESTING ==="; \
	if command -v ipcrawler >/dev/null 2>&1; then \
		echo "✅ IPCrawler command available"; \
		echo "Version: $$(ipcrawler --version 2>/dev/null || echo 'Failed to get version')"; \
		echo "Plugin count: $$(ipcrawler --list 2>/dev/null | wc -l || echo 'Failed to list plugins')"; \
		echo "Config directory: $$(ls -la "$$HOME/.config/IPCrawler" 2>/dev/null || ls -la "$$HOME/Library/Application Support/IPCrawler" 2>/dev/null || echo 'Not found')"; \
	else \
		echo "❌ IPCrawler command not available in PATH"; \
		if [ -f "$$HOME/.local/bin/ipcrawler" ]; then \
			echo "🔍 Found at: $$HOME/.local/bin/ipcrawler"; \
			echo "Version: $$($$HOME/.local/bin/ipcrawler --version 2>/dev/null || echo 'Failed')"; \
		fi \
	fi; \
	echo ""; \
	echo "=== REQUIRED TOOLS CHECK ==="; \
	for tool in nmap curl python3 pip3 pipx; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool: $$(which $$tool)"; \
		else \
			echo "❌ $$tool: Not found"; \
		fi \
	done; \
	echo ""; \
	echo "=== OPTIONAL TOOLS CHECK ==="; \
	for tool in feroxbuster gobuster enum4linux nikto smbclient; do \
		if command -v $$tool >/dev/null 2>&1; then \
			echo "✅ $$tool: $$(which $$tool)"; \
		else \
			echo "⚠️  $$tool: Not found (optional)"; \
		fi \
	done; \
	echo ""; \
	echo "=== NETWORK CONNECTIVITY ==="; \
	if curl -s --connect-timeout 5 https://github.com >/dev/null; then \
		echo "✅ GitHub connectivity: OK"; \
	else \
		echo "❌ GitHub connectivity: Failed"; \
	fi; \
	echo ""; \
	echo "=== PERMISSIONS CHECK ==="; \
	if [ -w "$$HOME/.local" ]; then \
		echo "✅ Home .local directory: Writable"; \
	else \
		echo "❌ Home .local directory: Not writable"; \
	fi; \
	if [ "$$OS" = "DEBIAN" ] || [ "$$OS" = "LINUX" ]; then \
		if sudo -n true 2>/dev/null; then \
			echo "✅ Sudo access: Available"; \
		else \
			echo "⚠️  Sudo access: May be required for some tools"; \
		fi \
	fi; \
	echo ""; \
	echo "=== RECOMMENDATIONS ==="; \
	if ! command -v ipcrawler >/dev/null 2>&1; then \
		echo "💡 Run 'make install' to install IPCrawler"; \
	fi; \
	if ! command -v pipx >/dev/null 2>&1; then \
		echo "💡 Install pipx for better Python package management"; \
	fi; \
	echo ""; \
	echo "🔬 Diagnostics complete!"; \
	rm -f .os_detected