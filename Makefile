# IPCrawler Makefile
# Commands for installation, running, and cleaning

# OS Detection
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

# Platform-specific paths
ifeq ($(UNAME_S),Darwin)
    # macOS
    OS_TYPE = macos
    SYSTEM_BIN_PATHS = /usr/local/bin /opt/homebrew/bin /opt/local/bin
    PIP_CACHE_DIR = ~/Library/Caches/pip
    PYTHON_SITE_PACKAGES = $(shell python3 -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)
else ifeq ($(UNAME_S),Linux)
    # Linux
    OS_TYPE = linux
    SYSTEM_BIN_PATHS = /usr/local/bin /usr/bin /opt/bin
    PIP_CACHE_DIR = ~/.cache/pip
    PYTHON_SITE_PACKAGES = $(shell python3 -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)
    
    # Detect Linux distribution
    ifneq ($(wildcard /etc/os-release),)
        DISTRO := $(shell . /etc/os-release && echo $$ID)
    else ifneq ($(wildcard /etc/debian_version),)
        DISTRO := debian
    else ifneq ($(wildcard /etc/redhat-release),)
        DISTRO := rhel
    else
        DISTRO := unknown
    endif
else
    # Other (Windows WSL, etc)
    OS_TYPE = other
    SYSTEM_BIN_PATHS = /usr/local/bin /usr/bin
    PIP_CACHE_DIR = ~/.cache/pip
endif

# User paths (cross-platform)
USER_BIN_PATHS = ~/.local/bin ~/bin

.PHONY: install install-user install-system run check clean clean-cache clean-install clean-system clean-quick help os-info

# Default target
help:
	@echo "IPCrawler Makefile Commands:"
	@echo "  make install        - Full installation (user + prompt for system)"
	@echo "  make install-user   - Install for current user only"
	@echo "  make install-system - Install system-wide (requires sudo)"
	@echo "  make fix-sudo       - Quick fix to enable 'sudo ipcrawler' command"
	@echo "  make run TARGET=<ip> - Run IPCrawler on target"
	@echo "  make check          - Check dependency installation"
	@echo "  make clean          - Complete cleanup of IPCrawler (interactive)"
	@echo "  make clean-quick    - Quick cleanup without prompts"
	@echo "  make clean-cache    - Clean Python cache only"
	@echo "  make clean-install  - Remove installed commands only"
	@echo "  make os-info        - Show detected OS and paths"

# Installation targets
install:
	@./install.sh

install-user:
	@echo "Installing IPCrawler for current user..."
	@python3 -m pip install --user -r requirements.txt
	@mkdir -p ~/.local/bin
	@ln -sf $$(pwd)/ipcrawler ~/.local/bin/ipcrawler
	@echo "Installation complete. IPCrawler installed to ~/.local/bin/"

install-system:
	@echo "Installing IPCrawler system-wide (requires sudo)..."
	@sudo python3 -m pip install -r requirements.txt
	@echo "System-wide dependencies installed"
	@echo "Creating system-wide command..."
	@sudo ln -sf $(shell pwd)/ipcrawler /usr/local/bin/ipcrawler
	@echo "System command installed to /usr/local/bin/ipcrawler"

# Quick fix for sudo command
fix-sudo:
	@echo "Creating system-wide command for sudo usage..."
	@sudo mkdir -p /usr/local/bin
	@sudo ln -sf $(shell pwd)/ipcrawler /usr/local/bin/ipcrawler
	@echo "Done! You can now use: sudo ipcrawler <target>"

# Run IPCrawler
run:
	@if [ -z "$(TARGET)" ]; then \
		echo "Error: Please specify TARGET"; \
		echo "Usage: make run TARGET=<ip_or_hostname>"; \
		exit 1; \
	fi
	@python3 ipcrawler.py $(TARGET)

# Check dependencies
check:
	@if [ -f ./check_deps.sh ]; then \
		./check_deps.sh; \
	else \
		echo "Creating dependency check script..."; \
		echo '#!/usr/bin/env bash' > check_deps.sh; \
		echo 'echo "User environment:"' >> check_deps.sh; \
		echo 'python3 -c "import httpx; print(\"  httpx: installed\")" 2>/dev/null || echo "  httpx: NOT installed"' >> check_deps.sh; \
		echo 'python3 -c "import dns.resolver; print(\"  dnspython: installed\")" 2>/dev/null || echo "  dnspython: NOT installed"' >> check_deps.sh; \
		chmod +x check_deps.sh; \
		./check_deps.sh; \
	fi

# Complete cleanup - removes everything
clean:
	@if [ -f ./scripts/deep_clean.sh ]; then \
		./scripts/deep_clean.sh; \
	else \
		echo "Running inline cleanup..."; \
		$(MAKE) clean-cache clean-install clean-system; \
	fi

# Clean Python cache
clean-cache:
	@echo "Cleaning Python cache for $(OS_TYPE)..."
	@# Clean project cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf .mypy_cache 2>/dev/null || true
	@# Clean pip cache (OS-specific)
	@if [ -d "$(PIP_CACHE_DIR)" ]; then \
		echo "  Cleaning pip cache at $(PIP_CACHE_DIR)"; \
		rm -rf $(PIP_CACHE_DIR)/wheels 2>/dev/null || true; \
		rm -rf $(PIP_CACHE_DIR)/http 2>/dev/null || true; \
	fi
	@# Clean user site-packages remnants
	@rm -rf ~/.local/lib/python*/site-packages/ipcrawler* 2>/dev/null || true
	@echo "Python cache cleaned"

# Clean installed commands and links
clean-install:
	@echo "Removing IPCrawler commands from detected paths..."
	@echo "OS Type: $(OS_TYPE)"
	@# Remove from user paths
	@for path in $(USER_BIN_PATHS); do \
		if [ -f $$path/ipcrawler ] || [ -L $$path/ipcrawler ]; then \
			rm -f $$path/ipcrawler 2>/dev/null && echo "  Removed: $$path/ipcrawler" || true; \
		fi; \
	done
	@# Remove from system paths (requires sudo)
	@for path in $(SYSTEM_BIN_PATHS); do \
		if [ -f $$path/ipcrawler ] || [ -L $$path/ipcrawler ]; then \
			sudo rm -f $$path/ipcrawler 2>/dev/null && echo "  Removed: $$path/ipcrawler" || true; \
		fi; \
	done
	@echo "Commands removed"

# Deep system cleanup (requires sudo)
clean-system:
	@echo "Performing deep system cleanup..."
	@# Remove pip packages (user)
	@python3 -m pip uninstall -y httpx dnspython typer rich pydantic pyyaml 2>/dev/null || true
	@# Remove pip packages (system)
	@sudo python3 -m pip uninstall -y httpx dnspython typer rich pydantic pyyaml 2>/dev/null || true
	@# Clean pip cache
	@python3 -m pip cache purge 2>/dev/null || true
	@sudo python3 -m pip cache purge 2>/dev/null || true
	@# Remove any workspace directories
	@rm -rf workspaces 2>/dev/null || true
	@# Remove test files
	@rm -f test_*.py debug_*.py 2>/dev/null || true
	@rm -f check_deps.sh 2>/dev/null || true
	@echo "System cleanup complete"

# Quick cleanup without prompts
clean-quick: clean-cache clean-install
	@echo "Quick cleanup..."
	@# Remove workspaces
	@rm -rf workspaces 2>/dev/null || true
	@# Remove test files
	@rm -f test_*.py debug_*.py check_deps.sh 2>/dev/null || true
	@# Uninstall packages (user only, no sudo)
	@python3 -m pip uninstall -y httpx dnspython typer rich pydantic pyyaml 2>/dev/null || true
	@echo "Quick cleanup complete"

# Show OS detection info
os-info:
	@echo "=== OS Detection Info ==="
	@echo "OS Type: $(OS_TYPE)"
	@echo "Platform: $(UNAME_S) $(UNAME_M)"
ifeq ($(OS_TYPE),linux)
	@echo "Linux Distro: $(DISTRO)"
endif
	@echo ""
	@echo "=== Path Configuration ==="
	@echo "User bin paths: $(USER_BIN_PATHS)"
	@echo "System bin paths: $(SYSTEM_BIN_PATHS)"
	@echo "Pip cache dir: $(PIP_CACHE_DIR)"
	@echo "Python site-packages: $(PYTHON_SITE_PACKAGES)"
	@echo ""
	@echo "=== Current Installation ==="
	@echo -n "IPCrawler in PATH: "
	@which ipcrawler 2>/dev/null || echo "Not found"
	@echo -n "Python3 location: "
	@which python3
	@echo -n "Pip3 location: "
	@which pip3 2>/dev/null || echo "Not found"