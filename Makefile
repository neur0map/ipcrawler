# IPCrawler Makefile - Simple Direct Execution Installation

.PHONY: install uninstall clean test help

# Default target
all: help

help:
	@echo "IPCrawler Installation"
	@echo "====================="
	@echo ""
	@echo "Commands:"
	@echo "  make install   - Install IPCrawler system-wide"
	@echo "  make uninstall - Remove IPCrawler from system"
	@echo "  make clean     - Clean Python cache files"
	@echo "  make test      - Test installation"
	@echo ""
	@echo "Usage after install:"
	@echo "  ipcrawler <target>       - Run as user"
	@echo "  sudo ipcrawler <target>  - Run with privileges"

install:
	@echo "Installing IPCrawler..."
	@chmod +x ipcrawler.py
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
	@sudo ln -sf $(shell pwd)/ipcrawler /usr/local/bin/ipcrawler
	@echo "✓ IPCrawler installed successfully"
	@echo ""
	@echo "You can now use:"
	@echo "  ipcrawler <target>       - Run as user"
	@echo "  sudo ipcrawler <target>  - Run with privileges"

uninstall:
	@echo "Uninstalling IPCrawler..."
	@sudo rm -f /usr/local/bin/ipcrawler
	@echo "✓ IPCrawler uninstalled"

clean:
	@echo "Cleaning Python cache files..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "✓ Cache cleaned"

test:
	@echo "Testing IPCrawler installation..."
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
	@python3 ipcrawler.py --help >/dev/null 2>&1 && echo "✓ Script works" || echo "✗ Script has issues"