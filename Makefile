# IPCrawler Makefile - Simple Direct Execution Installation
# Universal for macOS and Linux
#
# IPCrawler SmartList Engine - Intelligent wordlist recommendations
# GitHub: https://github.com/ipcrawler/ipcrawler
# Support: https://patreon.com/ipcrawler

# Detect OS and set paths dynamically
UNAME_S := $(shell uname -s)
USER_HOME := $(shell echo $$HOME)

ifeq ($(UNAME_S),Darwin)
	OS_TYPE = macos
	SYSTEM_BIN = /usr/local/bin
	PYTHON_CMD = python3
else ifeq ($(UNAME_S),Linux)
	OS_TYPE = linux
	SYSTEM_BIN = /usr/local/bin
	PYTHON_CMD = python3
else
	OS_TYPE = unknown
	SYSTEM_BIN = /usr/local/bin
	PYTHON_CMD = python3
endif

.PHONY: install uninstall clean clean-install fix-deps test setup-tools help

# Default target
all: help

help:
	@echo "IPCrawler Installation ($(OS_TYPE))"
	@echo "====================="
	@echo ""
	@echo "Commands:"
	@echo "  make install      - Install IPCrawler system-wide (with tool setup)"
	@echo "  make setup-tools  - Install and configure essential tools only"
	@echo "  make uninstall    - Remove IPCrawler from system"
	@echo "  make clean-install - Clean all existing IPCrawler installations"
	@echo "  make fix-deps     - Fix Python dependencies for sudo access"
	@echo "  make clean        - Clean Python cache files"
	@echo "  make test         - Test installation"
	@echo ""
	@echo "Tool Management:"
	@echo "  make setup-tools  - Install hakrawler and other essential tools"
	@echo ""
	@echo "System info:"
	@echo "  OS: $(OS_TYPE)"
	@echo "  System bin: $(SYSTEM_BIN)"
	@echo "  Python: $(PYTHON_CMD)"
	@echo "  Current dir: $$(pwd)"
	@echo "  User home: $(USER_HOME)"
	@echo ""
	@echo "Features:"
	@echo "  • Automatic tool installation (hakrawler, etc.)"
	@echo "  • PATH configuration for Go tools"
	@echo "  • System-wide symlinks for easy access"
	@echo "  • Smart dependency management"
	@echo ""
	@echo "Usage after install:"
	@echo "  ipcrawler <target>       - Run as user"
	@echo "  sudo ipcrawler <target>  - Run with privileges"
	@echo ""
	@echo "Support:"
	@echo "  GitHub: https://github.com/ipcrawler/ipcrawler"
	@echo "  Patreon: https://patreon.com/ipcrawler"

install:
	@echo "Installing IPCrawler..."
	@echo "Performing complete cleanup of existing installations..."
	@# Remove from common system locations
	@sudo rm -f /usr/local/bin/ipcrawler 2>/dev/null || true
	@sudo rm -f /usr/bin/ipcrawler 2>/dev/null || true
	@sudo rm -f /opt/local/bin/ipcrawler 2>/dev/null || true
	@# Remove from user local locations
	@rm -f $(USER_HOME)/.local/bin/ipcrawler 2>/dev/null || true
	@rm -f $(USER_HOME)/bin/ipcrawler 2>/dev/null || true
	@# Skip dynamic cleanup to avoid hanging issues - explicit removal above should be sufficient
	@# Clean cache and temporary files
	@rm -rf /tmp/ipcrawler_cache_* 2>/dev/null || true
	@find $(USER_HOME) -name ".ipcrawler*" -type f -delete 2>/dev/null || true
	@echo "✓ Cleanup completed"
	@chmod +x ipcrawler.py
	@echo "Installing Python dependencies..."
	@# Try system-wide installation first (works with sudo)
	@if sudo $(PYTHON_CMD) -m pip install -r requirements.txt 2>/dev/null; then \
		echo "✓ Dependencies installed system-wide (works with sudo)"; \
	elif sudo $(PYTHON_CMD) -m pip install --break-system-packages -r requirements.txt 2>/dev/null; then \
		echo "✓ Dependencies installed system-wide with --break-system-packages"; \
	elif $(PYTHON_CMD) -m pip install --user -r requirements.txt 2>/dev/null; then \
		echo "✓ Dependencies installed for user only"; \
		echo "⚠ Note: sudo ipcrawler may not work due to user-only installation"; \
	elif $(PYTHON_CMD) -m pip install --user --break-system-packages -r requirements.txt 2>/dev/null; then \
		echo "✓ Dependencies installed for user only (with --break-system-packages)"; \
		echo "⚠ Note: sudo ipcrawler may not work due to user-only installation"; \
	else \
		echo "⚠ Failed to install dependencies - HTTP scanner will use fallback mode"; \
		echo "⚠ You may need to install dependencies manually"; \
	fi
	@echo "Setting up essential tools..."
	@# Install and configure hakrawler
	@echo "→ Installing hakrawler for enhanced URL discovery..."
	@if $(PYTHON_CMD) scripts/install_hakrawler.py; then \
		echo "✓ Hakrawler setup completed"; \
	else \
		echo "⚠ Hakrawler setup had issues - Mini Spider will still work"; \
	fi
	@if [ ! -f ipcrawler ]; then \
		echo "Creating wrapper script..."; \
		echo '#!/usr/bin/env bash' > ipcrawler; \
		echo '# IPCrawler - Direct execution wrapper script' >> ipcrawler; \
		echo 'export PYTHONDONTWRITEBYTECODE=1' >> ipcrawler; \
		echo 'export PYTHONPYCACHEPREFIX=/tmp/ipcrawler_cache_$$' >> ipcrawler; \
		echo 'if [ -L "$${BASH_SOURCE[0]}" ]; then' >> ipcrawler; \
		echo '    SCRIPT_PATH="$$(readlink "$${BASH_SOURCE[0]}")"' >> ipcrawler; \
		echo '    if [[ "$$SCRIPT_PATH" != /* ]]; then' >> ipcrawler; \
		echo '        SCRIPT_PATH="$$(dirname "$${BASH_SOURCE[0]}")/$$SCRIPT_PATH"' >> ipcrawler; \
		echo '    fi' >> ipcrawler; \
		echo '    SCRIPT_DIR="$$(cd "$$(dirname "$$SCRIPT_PATH")" && pwd)"' >> ipcrawler; \
		echo 'else' >> ipcrawler; \
		echo '    SCRIPT_DIR="$$(cd "$$(dirname "$${BASH_SOURCE[0]}")" && pwd)"' >> ipcrawler; \
		echo 'fi' >> ipcrawler; \
		echo 'find "$${SCRIPT_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true' >> ipcrawler; \
		echo 'PYTHON_CMD=""' >> ipcrawler; \
		echo 'for py in python3 python3.12 python3.11 python3.10 python3.9 python; do' >> ipcrawler; \
		echo '    if command -v "$$py" >/dev/null 2>&1; then' >> ipcrawler; \
		echo '        PYTHON_CMD="$$py"' >> ipcrawler; \
		echo '        break' >> ipcrawler; \
		echo '    fi' >> ipcrawler; \
		echo 'done' >> ipcrawler; \
		echo 'if [ -z "$$PYTHON_CMD" ]; then' >> ipcrawler; \
		echo '    echo "Error: No Python interpreter found"' >> ipcrawler; \
		echo '    exit 1' >> ipcrawler; \
		echo 'fi' >> ipcrawler; \
		echo 'exec "$$PYTHON_CMD" -B -u "$${SCRIPT_DIR}/ipcrawler.py" "$$@"' >> ipcrawler; \
	fi
	@chmod +x ipcrawler
	@echo "Creating system symlink..."
	@sudo rm -f $(SYSTEM_BIN)/ipcrawler
	@sudo ln -sf "$$(pwd)/ipcrawler" $(SYSTEM_BIN)/ipcrawler
	@echo "Verifying installation..."
	@if [ -L $(SYSTEM_BIN)/ipcrawler ]; then \
		echo "  Symlink target: $$(readlink $(SYSTEM_BIN)/ipcrawler)"; \
		if [ -f "$$(readlink $(SYSTEM_BIN)/ipcrawler)" ]; then \
			echo "  ✓ Symlink target exists"; \
		else \
			echo "  ✗ Symlink target missing"; \
		fi; \
	fi
	@echo "✓ IPCrawler installed successfully"
	@echo ""
	@echo "Setting up SecLists and generating catalog..."
	@# Ensure database/wordlists directory exists
	@mkdir -p database/wordlists
	@# Run SecLists check and catalog generation in foreground
	@AUTO_INSTALL=true ./scripts/check_seclists.sh && \
		if [ -f .seclists_path ] && [ -s .seclists_path ]; then \
			. ./.seclists_path && \
			if [ ! -z "$$SECLISTS_PATH" ]; then \
				echo "→ Generating SecLists catalog..."; \
				if $(PYTHON_CMD) -m src.core.tools.catalog.generate_catalog; then \
					echo "✓ SecLists catalog generated successfully"; \
				else \
					echo "⚠ Failed to generate wordlist catalog - SmartList will use fallback mode"; \
				fi; \
			else \
				echo "⚠ SECLISTS_PATH is empty, skipping catalog generation"; \
			fi; \
		else \
			echo "⚠ .seclists_path file missing or empty, skipping catalog generation"; \
		fi
	@echo ""
	@echo "✓ Installation complete!"
	@echo ""
	@echo "💖 Support IPCrawler Development"
	@echo "  GitHub: https://github.com/ipcrawler/ipcrawler"
	@echo "  Patreon: https://patreon.com/ipcrawler"
	@echo ""
	@echo "Testing installation..."
	@$(SYSTEM_BIN)/ipcrawler --version || echo "⚠ Failed to run $(SYSTEM_BIN)/ipcrawler --version"
	@echo ""
	@echo "You can now use:"
	@echo "  ipcrawler <target>       - Run as user"
	@echo "  sudo ipcrawler <target>  - Run with privileges"

uninstall:
	@echo "Uninstalling IPCrawler..."
	@echo "Performing complete cleanup of all installations..."
	@# Remove from common system locations
	@sudo rm -f /usr/local/bin/ipcrawler 2>/dev/null || true
	@sudo rm -f /usr/bin/ipcrawler 2>/dev/null || true
	@sudo rm -f /opt/local/bin/ipcrawler 2>/dev/null || true
	@# Remove from user local locations
	@rm -f $(USER_HOME)/.local/bin/ipcrawler 2>/dev/null || true
	@rm -f $(USER_HOME)/bin/ipcrawler 2>/dev/null || true
	@# Skip dynamic cleanup to avoid hanging issues - explicit removal above should be sufficient
	@# Clean cache and temporary files
	@rm -rf /tmp/ipcrawler_cache_* 2>/dev/null || true
	@find $(USER_HOME) -name ".ipcrawler*" -type f -delete 2>/dev/null || true
	@echo "✓ All IPCrawler installations removed"
	@echo "Uninstalling Python dependencies..."
	@# Try to uninstall both system-wide and user installations
	@UNINSTALLED=false; \
	if sudo $(PYTHON_CMD) -m pip uninstall -y -r requirements.txt 2>/dev/null; then \
		echo "✓ System-wide dependencies uninstalled"; \
		UNINSTALLED=true; \
	fi; \
	if $(PYTHON_CMD) -m pip uninstall -y -r requirements.txt 2>/dev/null; then \
		echo "✓ User dependencies uninstalled"; \
		UNINSTALLED=true; \
	fi; \
	if [ "$$UNINSTALLED" = "false" ]; then \
		echo "⚠ Some dependencies may not have been uninstalled"; \
	fi
	@echo "✓ IPCrawler completely uninstalled"

clean-install:
	@echo "Performing complete cleanup of existing IPCrawler installations..."
	@# Remove from common system locations
	@sudo rm -f /usr/local/bin/ipcrawler 2>/dev/null || true
	@sudo rm -f /usr/bin/ipcrawler 2>/dev/null || true
	@sudo rm -f /opt/local/bin/ipcrawler 2>/dev/null || true
	@# Remove from user local locations
	@rm -f $(USER_HOME)/.local/bin/ipcrawler 2>/dev/null || true
	@rm -f $(USER_HOME)/bin/ipcrawler 2>/dev/null || true
	@# Skip dynamic cleanup to avoid hanging issues - explicit removal above should be sufficient
	@# Clean cache and temporary files
	@rm -rf /tmp/ipcrawler_cache_* 2>/dev/null || true
	@find $(USER_HOME) -name ".ipcrawler*" -type f -delete 2>/dev/null || true
	@echo "✓ All existing IPCrawler installations cleaned"

fix-deps:
	@echo "Fixing Python dependencies for both user and sudo access..."
	@echo "Installing dependencies system-wide (requires sudo)..."
	@if sudo $(PYTHON_CMD) -m pip install -r requirements.txt; then \
		echo "✓ Dependencies installed system-wide successfully"; \
		echo "✓ Both 'ipcrawler' and 'sudo ipcrawler' should now work"; \
	elif sudo $(PYTHON_CMD) -m pip install --break-system-packages -r requirements.txt; then \
		echo "✓ Dependencies installed system-wide with --break-system-packages"; \
		echo "✓ Both 'ipcrawler' and 'sudo ipcrawler' should now work"; \
	else \
		echo "✗ Failed to install system-wide dependencies"; \
		echo "Installing for user only..."; \
		if $(PYTHON_CMD) -m pip install --user -r requirements.txt; then \
			echo "✓ User dependencies installed"; \
			echo "⚠ Only 'ipcrawler' will work, 'sudo ipcrawler' may fail"; \
		else \
			echo "✗ Failed to install dependencies"; \
		fi; \
	fi

clean:
	@echo "Cleaning Python cache files..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "✓ Cache cleaned"

test:
	@echo "Testing IPCrawler installation..."
	@echo "OS: $(OS_TYPE)"
	@echo "System bin: $(SYSTEM_BIN)"
	@echo "Current dir: $$(pwd)"
	@echo "User home: $(USER_HOME)"
	@echo ""
	@echo -n "System symlink: "
	@test -L $(SYSTEM_BIN)/ipcrawler && echo "✓ Exists" || echo "✗ Missing"
	@echo -n "Symlink target: "
	@test -f "$$(readlink $(SYSTEM_BIN)/ipcrawler 2>/dev/null)" && echo "✓ Valid" || echo "✗ Broken"
	@echo -n "Command location (which): "
	@which ipcrawler 2>/dev/null || echo "Not found"
	@echo -n "Sudo command: "
	@sudo which ipcrawler 2>/dev/null && echo "✓ Works" || echo "✗ Failed"
	@echo -n "Script executable: "
	@test -x ipcrawler.py && echo "✓ Yes" || echo "✗ No"
	@echo -n "Wrapper executable: "
	@test -x ipcrawler && echo "✓ Yes" || echo "✗ No"
	@echo ""
	@echo "Testing functionality..."
	@echo -n "Direct Python script: "
	@$(PYTHON_CMD) ipcrawler.py --help >/dev/null 2>&1 && echo "✓ Works" || echo "✗ Failed"
	@echo -n "Symlink execution: "
	@$(SYSTEM_BIN)/ipcrawler --help >/dev/null 2>&1 && echo "✓ Works" || echo "✗ Failed"
	@echo -n "Shell resolution: "
	@command -v ipcrawler >/dev/null 2>&1 && echo "✓ Found" || echo "✗ Not found"
	@echo ""
	@echo "Checking for conflicts..."
	@echo -n "Shell aliases: "
	@alias | grep -q "ipcrawler=" && echo "⚠ Alias detected (may override symlink)" || echo "✓ None"
	@echo -n "Shell functions: "
	@type ipcrawler 2>/dev/null | grep -q "function" && echo "⚠ Function detected" || echo "✓ None"
	@echo ""
	@echo "Testing dependencies..."
	@$(PYTHON_CMD) -c "import httpx, dns.resolver" 2>/dev/null && echo "✓ HTTP scanner ready" || echo "⚠ HTTP scanner will use fallback mode"
	@echo ""
	@echo "Testing tool integration..."
	@echo -n "Hakrawler detection: "
	@if $(PYTHON_CMD) scripts/check_hakrawler.py >/dev/null 2>&1; then \
		echo "✓ Working"; \
	else \
		echo "⚠ Issues detected - run 'python scripts/check_hakrawler.py' for details"; \
	fi

setup-tools:
	@echo "Setting up essential tools for IPCrawler..."
	@echo "=========================================="
	@echo ""
	@echo "→ Installing and configuring hakrawler..."
	@if $(PYTHON_CMD) scripts/install_hakrawler.py; then \
		echo "✓ Hakrawler setup completed successfully"; \
	else \
		echo "⚠ Hakrawler setup encountered issues"; \
		echo "  Run 'python scripts/check_hakrawler.py' for diagnostics"; \
	fi
	@echo ""
	@echo "→ Testing tool integration..."
	@if $(PYTHON_CMD) scripts/check_hakrawler.py >/dev/null 2>&1; then \
		echo "✓ All tools working correctly"; \
	else \
		echo "⚠ Some tools may have issues"; \
		echo "  Run 'python scripts/check_hakrawler.py' for details"; \
	fi
	@echo ""
	@echo "✓ Tool setup completed!"
	@echo ""
	@echo "Tools are now ready for IPCrawler workflows."
	@echo "You may need to restart your terminal or run:"
	@echo "  source ~/.bashrc (Linux)"
	@echo "  source ~/.zshrc (macOS with zsh)"

# Master report generation has been moved to centralized reporting system
# Use: ipcrawler report master-report --workspace=<workspace_name>