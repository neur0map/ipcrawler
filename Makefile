# IPCrawler Makefile - Complete Rewrite for Reliability
# Handles all installation, caching, and PATH issues

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Get absolute path of current directory
ROOT_DIR := $(shell pwd)

# Python interpreter detection
PYTHON := $(shell which python3 2>/dev/null || which python 2>/dev/null)
PIP := $(PYTHON) -m pip

# Standard targets
.PHONY: all install clean uninstall test help
.PHONY: clean-all clean-cache fix-sudo deps-check deps-install
.PHONY: install-user install-system quick-fix

# Default target
all: help

help:
	@echo "$(BLUE)IPCrawler Installation System$(NC)"
	@echo "=============================="
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  make quick-fix     - Fast fix for 'sudo ipcrawler' command"
	@echo "  make install       - Complete installation"
	@echo ""
	@echo "$(GREEN)Installation Options:$(NC)"
	@echo "  make install-user  - Install for current user only"
	@echo "  make install-system- Install system-wide (requires sudo)"
	@echo "  make fix-sudo      - Just create the sudo command link"
	@echo ""
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  make clean-all     - Remove ALL caches and reinstall deps"
	@echo "  make clean-cache   - Remove Python cache files only"
	@echo "  make deps-check    - Check if dependencies are installed"
	@echo "  make deps-install  - Force reinstall all dependencies"
	@echo "  make uninstall     - Completely remove IPCrawler"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test          - Test the installation"
	@echo ""

# Quick fix for sudo command - most common issue
quick-fix: clean-cache fix-sudo
	@echo "$(GREEN)✓ Quick fix applied!$(NC)"
	@echo "You can now use: $(YELLOW)sudo ipcrawler <target>$(NC)"

# Complete installation
install: clean-all install-user install-system test
	@echo "$(GREEN)✓ Complete installation finished!$(NC)"

# Install for current user
install-user:
	@echo "$(BLUE)Installing IPCrawler for current user...$(NC)"
	@# Make scripts executable
	@chmod +x $(ROOT_DIR)/ipcrawler.py
	@chmod +x $(ROOT_DIR)/ipcrawler
	@# Install Python dependencies with no cache
	@echo "Installing Python dependencies..."
	@$(PIP) install --user --no-cache-dir -r requirements.txt 2>/dev/null || \
		$(PIP) install --user --no-cache-dir --break-system-packages -r requirements.txt || \
		(echo "$(RED)Failed to install dependencies$(NC)" && exit 1)
	@# Create user bin directory
	@mkdir -p ~/.local/bin
	@# Create symlink
	@ln -sf $(ROOT_DIR)/ipcrawler ~/.local/bin/ipcrawler
	@echo "$(GREEN)✓ User installation complete$(NC)"
	@# Check PATH
	@if ! echo "$$PATH" | grep -q "$$HOME/.local/bin"; then \
		echo "$(YELLOW)⚠ Add to your shell config:$(NC)"; \
		echo '  export PATH="$$HOME/.local/bin:$$PATH"'; \
	fi

# Install system-wide
install-system:
	@echo "$(BLUE)Installing IPCrawler system-wide...$(NC)"
	@# Install system Python dependencies
	@echo "Installing system Python dependencies..."
	@sudo $(PIP) install --no-cache-dir -r requirements.txt 2>/dev/null || \
		sudo $(PIP) install --no-cache-dir --break-system-packages -r requirements.txt 2>/dev/null || \
		echo "$(YELLOW)⚠ System deps failed (will use user deps with sudo)$(NC)"
	@# Create system command
	@sudo mkdir -p /usr/local/bin
	@sudo ln -sf $(ROOT_DIR)/ipcrawler /usr/local/bin/ipcrawler
	@sudo chmod +x /usr/local/bin/ipcrawler
	@echo "$(GREEN)✓ System installation complete$(NC)"

# Just fix the sudo command
fix-sudo:
	@echo "Creating system-wide command..."
	@sudo mkdir -p /usr/local/bin
	@sudo ln -sf $(ROOT_DIR)/ipcrawler /usr/local/bin/ipcrawler
	@sudo chmod +x /usr/local/bin/ipcrawler
	@echo "$(GREEN)✓ System command created$(NC)"

# Deep clean everything including caches
clean-all:
	@echo "$(BLUE)Deep cleaning all caches...$(NC)"
	@# Remove all Python caches
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .mypy_cache build dist 2>/dev/null || true
	@# Clear pip cache
	@$(PIP) cache purge 2>/dev/null || true
	@# Clear system pip cache if we have sudo
	@sudo $(PIP) cache purge 2>/dev/null || true
	@# Remove compiled Python files from site-packages
	@find ~/.local/lib -name "*httpx*.pyc" -delete 2>/dev/null || true
	@find ~/.local/lib -name "*dns*.pyc" -delete 2>/dev/null || true
	@# Force Python to ignore bytecode
	@export PYTHONDONTWRITEBYTECODE=1
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

# Clean only Python cache
clean-cache:
	@echo "Cleaning Python cache..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@export PYTHONDONTWRITEBYTECODE=1

# Check dependencies
deps-check:
	@echo "$(BLUE)Checking dependencies...$(NC)"
	@echo -n "Core deps: "
	@$(PYTHON) -c "import typer, rich, pydantic; print('$(GREEN)✓$(NC)')" 2>/dev/null || echo "$(RED)✗$(NC)"
	@echo -n "HTTP deps: "
	@$(PYTHON) -c "import httpx, dns.resolver; print('$(GREEN)✓$(NC)')" 2>/dev/null || echo "$(RED)✗$(NC)"
	@echo -n "nmap: "
	@which nmap >/dev/null 2>&1 && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo ""
	@echo "$(BLUE)Checking with sudo...$(NC)"
	@echo -n "System HTTP deps: "
	@sudo $(PYTHON) -c "import httpx, dns.resolver; print('$(GREEN)✓$(NC)')" 2>/dev/null || echo "$(RED)✗$(NC)"

# Force reinstall dependencies
deps-install: clean-all
	@echo "$(BLUE)Force reinstalling all dependencies...$(NC)"
	@$(PIP) uninstall -y httpx dnspython typer rich pydantic pyyaml 2>/dev/null || true
	@$(PIP) install --user --no-cache-dir --force-reinstall -r requirements.txt || \
		$(PIP) install --user --no-cache-dir --force-reinstall --break-system-packages -r requirements.txt

# Test installation
test:
	@echo "$(BLUE)Testing installation...$(NC)"
	@echo -n "ipcrawler command: "
	@if which ipcrawler >/dev/null 2>&1; then \
		echo "$(GREEN)✓$(NC) Found at $$(which ipcrawler)"; \
	else \
		echo "$(RED)✗$(NC) Not found"; \
	fi
	@echo -n "sudo ipcrawler: "
	@if sudo which ipcrawler >/dev/null 2>&1; then \
		echo "$(GREEN)✓$(NC) Works"; \
	else \
		echo "$(RED)✗$(NC) Not found"; \
	fi
	@echo -n "Dependencies: "
	@if $(PYTHON) -c "import httpx, dns.resolver" 2>/dev/null; then \
		echo "$(GREEN)✓$(NC) All present"; \
	else \
		echo "$(YELLOW)⚠$(NC) Fallback mode"; \
	fi
	@echo ""
	@echo "$(BLUE)Debug info:$(NC)"
	@$(PYTHON) $(ROOT_DIR)/ipcrawler.py --help >/dev/null 2>&1 && echo "Script works: $(GREEN)✓$(NC)" || echo "Script error: $(RED)✗$(NC)"

# Complete uninstall
uninstall:
	@echo "$(BLUE)Uninstalling IPCrawler...$(NC)"
	@# Remove commands
	@rm -f ~/.local/bin/ipcrawler 2>/dev/null || true
	@sudo rm -f /usr/local/bin/ipcrawler 2>/dev/null || true
	@# Remove Python packages
	@$(PIP) uninstall -y httpx dnspython typer rich pydantic pyyaml 2>/dev/null || true
	@# Clean caches
	@$(MAKE) clean-all
	@echo "$(GREEN)✓ Uninstall complete$(NC)"