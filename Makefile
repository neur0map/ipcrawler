# IPCrawler Installation Makefile
# Cross-platform installer for IPCrawler security tool orchestration framework

.DEFAULT_GOAL := install
.PHONY: install install-deps install-seclists install-alias wordlist uninstall update test clean help

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

# Project configuration
PROJECT_NAME = ipcrawler
PROJECT_DIR = $(shell pwd)
MAIN_SCRIPT = $(PROJECT_DIR)/ipcrawler.py
REQUIREMENTS = requirements.txt

# System detection
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
	OS = macos
	INSTALL_CMD = brew install
	PYTHON_CMD = python3
	PIP_CMD = pip3
	USER_BIN = $(HOME)/.local/bin
else ifeq ($(UNAME_S),Linux)
	OS = linux
	INSTALL_CMD = sudo apt-get install
	PYTHON_CMD = python3
	PIP_CMD = pip3
	USER_BIN = $(HOME)/.local/bin
else
	OS = unknown
	PYTHON_CMD = python3
	PIP_CMD = pip3
	USER_BIN = $(HOME)/.local/bin
endif

# SecLists paths (priority order)
SECLISTS_PATHS = /usr/share/seclists /opt/seclists $(HOME)/.local/share/seclists $(PROJECT_DIR)/seclists
SECLISTS_REPO = https://github.com/danielmiessler/SecLists.git

# Find existing SecLists installation
SECLISTS_PATH = $(shell for path in $(SECLISTS_PATHS); do \
	if [ -d "$$path" ]; then echo "$$path"; break; fi; \
done)

# Determine install location for SecLists
ifeq ($(SECLISTS_PATH),)
	ifeq ($(OS),linux)
		SECLISTS_INSTALL_PATH = /usr/share/seclists
	else
		SECLISTS_INSTALL_PATH = $(HOME)/.local/share/seclists
	endif
else
	SECLISTS_INSTALL_PATH = $(SECLISTS_PATH)
endif

help:
	@echo "$(BLUE)IPCrawler Installation System$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@echo "  install        - Full installation (dependencies + SecLists + alias)"
	@echo "  install-deps   - Install Python dependencies only"
	@echo "  install-seclists - Install SecLists wordlists only"
	@echo "  install-alias  - Create ipcrawler command alias only"
	@echo "  wordlist       - Parse and catalog wordlists into JSON"
	@echo "  uninstall      - Remove ipcrawler alias"
	@echo "  update         - Update SecLists via git pull"
	@echo "  test           - Test installation"
	@echo "  clean          - Remove cache files"
	@echo ""
	@echo "$(YELLOW)System Info:$(NC)"
	@echo "  OS: $(OS)"
	@echo "  Python: $(PYTHON_CMD)"
	@echo "  Project: $(PROJECT_DIR)"
	@echo "  User bin: $(USER_BIN)"
	@echo "  SecLists: $(SECLISTS_INSTALL_PATH)"

install: system-check install-deps install-seclists install-alias
	@echo "$(GREEN)✅ IPCrawler installation completed successfully!$(NC)"
	@echo ""
	@echo "$(BLUE)Usage:$(NC)"
	@echo "  ipcrawler --help"
	@echo "  ipcrawler list"
	@echo "  ipcrawler run template target"
	@echo ""
	@echo "$(YELLOW)Note: Changes to code will be reflected immediately (no reinstallation needed)$(NC)"

system-check:
	@echo "$(BLUE)🔍 System Check$(NC)"
	@echo "Detected OS: $(OS)"
	@echo "Python path: $(shell which $(PYTHON_CMD))"
	@echo "Python version: $(shell $(PYTHON_CMD) --version)"
	@echo "Project directory: $(PROJECT_DIR)"
	@echo "User bin directory: $(USER_BIN)"
	@echo ""
	@if ! command -v $(PYTHON_CMD) >/dev/null 2>&1; then \
		echo "$(RED)❌ Python 3 not found. Please install Python 3.8+$(NC)"; \
		exit 1; \
	fi
	@if ! $(PYTHON_CMD) -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then \
		echo "$(RED)❌ Python 3.8+ required. Current: $(shell $(PYTHON_CMD) --version)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ System check passed$(NC)"

install-deps:
	@echo "$(BLUE)📦 Installing Python dependencies$(NC)"
	@if [ ! -f "$(REQUIREMENTS)" ]; then \
		echo "$(RED)❌ requirements.txt not found$(NC)"; \
		exit 1; \
	fi
	@$(PIP_CMD) install --break-system-packages --user -r $(REQUIREMENTS)
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

install-seclists:
	@echo "$(BLUE)📚 Installing SecLists wordlists$(NC)"
	@if [ -d "$(SECLISTS_INSTALL_PATH)" ]; then \
		echo "$(YELLOW)SecLists already exists at: $(SECLISTS_INSTALL_PATH)$(NC)"; \
		echo "$(BLUE)Updating existing SecLists...$(NC)"; \
		cd "$(SECLISTS_INSTALL_PATH)" && git pull; \
	else \
		echo "$(BLUE)Installing SecLists to: $(SECLISTS_INSTALL_PATH)$(NC)"; \
		mkdir -p "$(dir $(SECLISTS_INSTALL_PATH))"; \
		if [ "$(SECLISTS_INSTALL_PATH)" = "/usr/share/seclists" ] && [ "$(OS)" = "linux" ]; then \
			sudo git clone --depth 1 $(SECLISTS_REPO) "$(SECLISTS_INSTALL_PATH)"; \
		else \
			git clone --depth 1 $(SECLISTS_REPO) "$(SECLISTS_INSTALL_PATH)"; \
		fi; \
	fi
	@echo "$(GREEN)✅ SecLists installed/updated at: $(SECLISTS_INSTALL_PATH)$(NC)"
	@echo "$(BLUE)Updating config.toml with SecLists path...$(NC)"
	@$(PYTHON_CMD) -c "import toml, os; \
		config = toml.load('config.toml') if os.path.exists('config.toml') else {}; \
		config.setdefault('wordlists', {})['seclists_path'] = '$(SECLISTS_INSTALL_PATH)'; \
		toml.dump(config, open('config.toml', 'w'))"

install-alias:
	@echo "$(BLUE)🔗 Creating ipcrawler command alias$(NC)"
	@mkdir -p "$(USER_BIN)"
	@if [ ! -f "$(MAIN_SCRIPT)" ]; then \
		echo "$(RED)❌ Main script not found: $(MAIN_SCRIPT)$(NC)"; \
		exit 1; \
	fi
	@ln -sf "$(MAIN_SCRIPT)" "$(USER_BIN)/ipcrawler"
	@chmod +x "$(MAIN_SCRIPT)"
	@echo "$(GREEN)✅ Created symlink: $(USER_BIN)/ipcrawler -> $(MAIN_SCRIPT)$(NC)"
	@if ! echo "$$PATH" | grep -q "$(USER_BIN)"; then \
		echo "$(YELLOW)⚠️  $(USER_BIN) not in PATH$(NC)"; \
		echo "$(BLUE)Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):$(NC)"; \
		echo "export PATH=\"$(USER_BIN):\$$PATH\""; \
	else \
		echo "$(GREEN)✅ $(USER_BIN) is in PATH$(NC)"; \
	fi

uninstall:
	@echo "$(BLUE)🗑️  Uninstalling ipcrawler$(NC)"
	@if [ -L "$(USER_BIN)/ipcrawler" ]; then \
		rm "$(USER_BIN)/ipcrawler"; \
		echo "$(GREEN)✅ Removed ipcrawler alias$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  ipcrawler alias not found$(NC)"; \
	fi
	@echo "$(BLUE)SecLists remains at: $(SECLISTS_INSTALL_PATH)$(NC)"
	@echo "$(BLUE)To remove SecLists: rm -rf $(SECLISTS_INSTALL_PATH)$(NC)"

update:
	@echo "$(BLUE)🔄 Updating SecLists$(NC)"
	@if [ -d "$(SECLISTS_INSTALL_PATH)" ]; then \
		cd "$(SECLISTS_INSTALL_PATH)" && git pull; \
		echo "$(GREEN)✅ SecLists updated$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  SecLists not found. Run 'make install-seclists' first$(NC)"; \
	fi

test:
	@echo "$(BLUE)🧪 Testing installation$(NC)"
	@if [ -x "$(USER_BIN)/ipcrawler" ]; then \
		echo "$(GREEN)✅ ipcrawler alias exists and is executable$(NC)"; \
	else \
		echo "$(RED)❌ ipcrawler alias not found or not executable$(NC)"; \
		exit 1; \
	fi
	@if [ -d "$(SECLISTS_INSTALL_PATH)" ]; then \
		echo "$(GREEN)✅ SecLists found at: $(SECLISTS_INSTALL_PATH)$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  SecLists not found$(NC)"; \
	fi
	@echo "$(BLUE)Testing basic functionality...$(NC)"
	@$(USER_BIN)/ipcrawler --version >/dev/null 2>&1 && echo "$(GREEN)✅ Version check passed$(NC)" || echo "$(RED)❌ Version check failed$(NC)"
	@$(USER_BIN)/ipcrawler list >/dev/null 2>&1 && echo "$(GREEN)✅ List command passed$(NC)" || echo "$(RED)❌ List command failed$(NC)"
	@echo "$(GREEN)✅ Installation test completed$(NC)"

wordlist:
	@echo "$(BLUE)📚 Parsing and cataloging wordlists$(NC)"
	@if [ ! -f "config.toml" ]; then \
		echo "$(RED)❌ config.toml not found. Run 'make install' first$(NC)"; \
		exit 1; \
	fi
	@if ! grep -q "seclists_path" config.toml; then \
		echo "$(RED)❌ SecLists path not configured. Run 'make install-seclists' first$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Scanning SecLists and other wordlists...$(NC)"
	@$(PYTHON_CMD) -m ipcrawler.core.wordlist_manager
	@echo "$(GREEN)✅ Wordlist catalog generated$(NC)"
	@echo "$(BLUE)Files created:$(NC)"
	@echo "  - wordlists/catalog.json (machine-readable metadata)"
	@echo "  - wordlists/README.md (human-readable guide)"
	@echo ""
	@echo "$(YELLOW)Usage examples:$(NC)"
	@echo "  - Find web directory wordlists with 'web' technology tag"
	@echo "  - Filter by CTF-optimized wordlists"
	@echo "  - Sort by quality score for best results"

clean:
	@echo "$(BLUE)🧹 Cleaning cache files$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .cache 2>/dev/null || true
	@echo "$(GREEN)✅ Cache files cleaned$(NC)"