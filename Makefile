# IPCrawler Makefile - Simple Direct Execution Installation
# Universal for macOS and Linux

# Detect OS
UNAME_S := $(shell uname -s)
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

.PHONY: install uninstall clean test help

# Default target
all: help

help:
	@echo "IPCrawler Installation ($(OS_TYPE))"
	@echo "====================="
	@echo ""
	@echo "Commands:"
	@echo "  make install   - Install IPCrawler system-wide"
	@echo "  make uninstall - Remove IPCrawler from system"
	@echo "  make clean     - Clean Python cache files"
	@echo "  make test      - Test installation"
	@echo ""
	@echo "System info:"
	@echo "  OS: $(OS_TYPE)"
	@echo "  System bin: $(SYSTEM_BIN)"
	@echo "  Python: $(PYTHON_CMD)"
	@echo ""
	@echo "Usage after install:"
	@echo "  ipcrawler <target>       - Run as user"
	@echo "  sudo ipcrawler <target>  - Run with privileges"

install:
	@echo "Installing IPCrawler..."
	@chmod +x ipcrawler.py
	@echo "Installing Python dependencies..."
	@if $(PYTHON_CMD) -m pip install --user -r requirements.txt 2>/dev/null; then \
		echo "✓ Dependencies installed successfully"; \
	else \
		echo "Retrying with --break-system-packages..."; \
		if $(PYTHON_CMD) -m pip install --user --break-system-packages -r requirements.txt; then \
			echo "✓ Dependencies installed (with --break-system-packages)"; \
		else \
			echo "⚠ Failed to install dependencies - HTTP scanner will use fallback mode"; \
		fi; \
	fi
	@if [ ! -f ipcrawler ]; then \
		echo "Creating wrapper script..."; \
		echo '#!/usr/bin/env bash' > ipcrawler; \
		echo '# IPCrawler - Direct execution wrapper script' >> ipcrawler; \
		echo 'export PYTHONDONTWRITEBYTECODE=1' >> ipcrawler; \
		echo 'export PYTHONPYCACHEPREFIX=/tmp/ipcrawler_cache_$$' >> ipcrawler; \
		echo 'SCRIPT_DIR="$$(cd "$$(dirname "$${BASH_SOURCE[0]}")" && pwd)"' >> ipcrawler; \
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
	@sudo ln -sf $(shell pwd)/ipcrawler $(SYSTEM_BIN)/ipcrawler
	@echo "✓ IPCrawler installed successfully"
	@echo ""
	@echo "You can now use:"
	@echo "  ipcrawler <target>       - Run as user"
	@echo "  sudo ipcrawler <target>  - Run with privileges"

uninstall:
	@echo "Uninstalling IPCrawler..."
	@sudo rm -f $(SYSTEM_BIN)/ipcrawler
	@echo "✓ IPCrawler uninstalled"

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
	@echo ""
	@echo -n "Command location: "
	@which ipcrawler 2>/dev/null || echo "Not found"
	@echo -n "Sudo command: "
	@sudo which ipcrawler 2>/dev/null && echo "✓ Works" || echo "✗ Failed"
	@echo -n "Script executable: "
	@test -x ipcrawler.py && echo "✓ Yes" || echo "✗ No"
	@echo -n "Wrapper executable: "
	@test -x ipcrawler && echo "✓ Yes" || echo "✗ No"
	@echo ""
	@echo "Testing basic functionality..."
	@$(PYTHON_CMD) ipcrawler.py --help >/dev/null 2>&1 && echo "✓ Script works" || echo "✗ Script has issues"
	@echo ""
	@echo "Testing dependencies..."
	@$(PYTHON_CMD) -c "import httpx, dns.resolver" 2>/dev/null && echo "✓ HTTP scanner ready" || echo "⚠ HTTP scanner will use fallback mode"