# IPCrawler Makefile
# Comprehensive build and installation automation for non-coding experts

.PHONY: help install uninstall build build-release clean test setup-deps check-deps verify config wizard docker-up docker-down symlink update dev run

# Default target
.DEFAULT_GOAL := help

# Variables
BINARY_NAME := ipcrawler
INSTALL_PATH := /usr/local/bin/$(BINARY_NAME)
BUILD_DIR := target
RELEASE_BINARY := $(BUILD_DIR)/release/$(BINARY_NAME)
DEBUG_BINARY := $(BUILD_DIR)/debug/$(BINARY_NAME)
CONFIG_DIR := $(HOME)/.config/ipcrawler
CARGO := cargo

# Color output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

##@ Help

help: ## Display this help message
	@echo "$(BLUE)IPCrawler - Auto-Reconnaissance Tool$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC) make [target]"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Quick Start

setup: check-deps setup-deps build-release symlink wizard docker-up ## Complete initial setup
	@echo ""
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Run: $(BINARY_NAME) --help"
	@echo "  2. Try: $(BINARY_NAME) scan --help"

##@ Building

build: ## Build debug version
	@echo "$(BLUE)Building debug version...$(NC)"
	@$(CARGO) build
	@echo "$(GREEN)✓ Debug build complete: $(DEBUG_BINARY)$(NC)"

build-release: ## Build optimized release version
	@echo "$(BLUE)Building release version (optimized)...$(NC)"
	@$(CARGO) build --release
	@echo "$(GREEN)✓ Release build complete: $(RELEASE_BINARY)$(NC)"

clean: ## Remove build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@$(CARGO) clean
	@echo "$(GREEN)✓ Clean complete$(NC)"

rebuild: clean build-release ## Clean and rebuild release version
	@echo "$(GREEN)✓ Rebuild complete$(NC)"

##@ Installation

symlink: build-release ## Create symlink to release binary (recommended)
	@echo "$(BLUE)Creating symlink...$(NC)"
	@if [ -L "$(INSTALL_PATH)" ]; then \
		echo "$(YELLOW)Removing existing symlink...$(NC)"; \
		sudo rm -f $(INSTALL_PATH); \
	fi
	@if [ -f "$(INSTALL_PATH)" ] && [ ! -L "$(INSTALL_PATH)" ]; then \
		echo "$(RED)Error: $(INSTALL_PATH) exists and is not a symlink$(NC)"; \
		echo "$(YELLOW)Remove it manually or use 'make uninstall' first$(NC)"; \
		exit 1; \
	fi
	@sudo ln -sf $(shell pwd)/$(RELEASE_BINARY) $(INSTALL_PATH)
	@echo "$(GREEN)✓ Symlink created: $(INSTALL_PATH) -> $(RELEASE_BINARY)$(NC)"
	@echo "$(BLUE)Now you can run '$(BINARY_NAME)' from anywhere!$(NC)"
	@echo "$(YELLOW)Tip: After code changes, just run 'make build-release' and the symlink will use the new binary$(NC)"

install: build-release ## Install binary to /usr/local/bin (copy)
	@echo "$(BLUE)Installing $(BINARY_NAME)...$(NC)"
	@sudo cp $(RELEASE_BINARY) $(INSTALL_PATH)
	@sudo chmod +x $(INSTALL_PATH)
	@echo "$(GREEN)✓ Installed to $(INSTALL_PATH)$(NC)"
	@echo "$(YELLOW)Note: Using 'make symlink' is recommended for development$(NC)"

uninstall: ## Remove installed binary
	@echo "$(BLUE)Uninstalling $(BINARY_NAME)...$(NC)"
	@if [ -f "$(INSTALL_PATH)" ] || [ -L "$(INSTALL_PATH)" ]; then \
		sudo rm -f $(INSTALL_PATH); \
		echo "$(GREEN)✓ Uninstalled from $(INSTALL_PATH)$(NC)"; \
	else \
		echo "$(YELLOW)Not installed at $(INSTALL_PATH)$(NC)"; \
	fi

reinstall: uninstall symlink ## Uninstall and reinstall (using symlink)
	@echo "$(GREEN)✓ Reinstall complete$(NC)"

##@ Dependencies

check-deps: ## Check if required dependencies are installed
	@echo "$(BLUE)Checking dependencies...$(NC)"
	@command -v cargo >/dev/null 2>&1 || { echo "$(RED)✗ Rust/Cargo not found. Install from https://rustup.rs$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Rust/Cargo found$(NC)"
	@command -v docker >/dev/null 2>&1 || echo "$(YELLOW)⚠ Docker not found (optional, needed for Qdrant)$(NC)"
	@command -v ollama >/dev/null 2>&1 || echo "$(YELLOW)⚠ Ollama not found (optional, for local LLMs)$(NC)"

setup-deps: ## Install Rust dependencies
	@echo "$(BLUE)Installing Rust dependencies...$(NC)"
	@$(CARGO) fetch
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

update-deps: ## Update dependencies to latest versions
	@echo "$(BLUE)Updating dependencies...$(NC)"
	@$(CARGO) update
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

##@ Configuration

wizard: ## Run interactive setup wizard
	@if [ -f "$(RELEASE_BINARY)" ]; then \
		$(RELEASE_BINARY) wizard; \
	elif [ -f "$(DEBUG_BINARY)" ]; then \
		$(DEBUG_BINARY) wizard; \
	else \
		echo "$(RED)Binary not found. Run 'make build' first$(NC)"; \
		exit 1; \
	fi

config: ## Show current configuration
	@if [ -f "$(CONFIG_DIR)/config.yaml" ]; then \
		echo "$(BLUE)Current configuration:$(NC)"; \
		cat $(CONFIG_DIR)/config.yaml; \
	else \
		echo "$(YELLOW)No configuration found at $(CONFIG_DIR)/config.yaml$(NC)"; \
		echo "$(BLUE)Run 'make wizard' to create one$(NC)"; \
	fi

config-dir: ## Open configuration directory
	@mkdir -p $(CONFIG_DIR)
	@echo "$(BLUE)Configuration directory: $(CONFIG_DIR)$(NC)"
	@open $(CONFIG_DIR) 2>/dev/null || xdg-open $(CONFIG_DIR) 2>/dev/null || echo "$(YELLOW)Open manually: $(CONFIG_DIR)$(NC)"

##@ Docker Services

docker-up: ## Start Qdrant vector database
	@echo "$(BLUE)Starting Qdrant (vector database)...$(NC)"
	@if [ ! -f "docker-compose.yml" ]; then \
		echo "$(YELLOW)Creating docker-compose.yml...$(NC)"; \
		echo "version: '3.8'\nservices:\n  qdrant:\n    image: qdrant/qdrant:latest\n    container_name: ipcrawler-qdrant\n    ports:\n      - '6333:6333'\n      - '6334:6334'\n    volumes:\n      - ./qdrant_storage:/qdrant/storage\n    restart: unless-stopped" > docker-compose.yml; \
	fi
	@docker-compose up -d
	@echo "$(GREEN)✓ Qdrant running at http://localhost:6333$(NC)"

docker-down: ## Stop Qdrant vector database
	@echo "$(BLUE)Stopping Qdrant...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✓ Qdrant stopped$(NC)"

docker-status: ## Check Docker services status
	@docker-compose ps

docker-logs: ## Show Qdrant logs
	@docker-compose logs -f qdrant

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	@$(CARGO) test
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-verbose: ## Run tests with verbose output
	@$(CARGO) test -- --nocapture

verify: build-release ## Verify installation and dependencies
	@echo "$(BLUE)Verifying setup...$(NC)"
	@echo ""
	@echo "$(YELLOW)[1/5] Checking binary...$(NC)"
	@if [ -f "$(RELEASE_BINARY)" ]; then \
		echo "$(GREEN)✓ Binary exists$(NC)"; \
	else \
		echo "$(RED)✗ Binary not found$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(YELLOW)[2/5] Checking installation...$(NC)"
	@if [ -L "$(INSTALL_PATH)" ]; then \
		echo "$(GREEN)✓ Symlink installed at $(INSTALL_PATH)$(NC)"; \
	elif [ -f "$(INSTALL_PATH)" ]; then \
		echo "$(GREEN)✓ Binary installed at $(INSTALL_PATH)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Not installed (run 'make symlink')$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)[3/5] Checking configuration...$(NC)"
	@if [ -f "$(CONFIG_DIR)/config.yaml" ]; then \
		echo "$(GREEN)✓ Configuration exists$(NC)"; \
	else \
		echo "$(YELLOW)⚠ No configuration (run 'make wizard')$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)[4/5] Checking Qdrant...$(NC)"
	@if curl -s http://localhost:6333 >/dev/null 2>&1; then \
		echo "$(GREEN)✓ Qdrant running$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Qdrant not running (run 'make docker-up')$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)[5/5] Checking Ollama (optional)...$(NC)"
	@if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then \
		echo "$(GREEN)✓ Ollama running$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Ollama not running (optional)$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)✓ Verification complete!$(NC)"

##@ Development

dev: ## Run in development mode (auto-rebuild)
	@echo "$(BLUE)Running in development mode...$(NC)"
	@$(CARGO) watch -x run

run: build ## Build and run debug version
	@$(DEBUG_BINARY) $(ARGS)

run-release: build-release ## Build and run release version
	@$(RELEASE_BINARY) $(ARGS)

fmt: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	@$(CARGO) fmt
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Run clippy linter
	@echo "$(BLUE)Running linter...$(NC)"
	@$(CARGO) clippy -- -D warnings
	@echo "$(GREEN)✓ Linting complete$(NC)"

check: ## Quick compile check without building
	@$(CARGO) check

##@ Examples

example-scan: ## Example: Scan a target
	@echo "$(BLUE)Example scan command:$(NC)"
	@echo "$(BINARY_NAME) scan 192.168.1.0/24 --template network"

example-query: ## Example: Query results with RAG
	@echo "$(BLUE)Example query command:$(NC)"
	@echo "$(BINARY_NAME) query 'What vulnerabilities were found on the SSH service?'"

example-watch: ## Example: Watch directory for new files
	@echo "$(BLUE)Example watch command:$(NC)"
	@echo "$(BINARY_NAME) watch ./scan-results --auto-index"

##@ Maintenance

update: ## Update and rebuild project
	@echo "$(BLUE)Updating project...$(NC)"
	@git pull
	@$(MAKE) update-deps
	@$(MAKE) build-release
	@echo "$(GREEN)✓ Update complete$(NC)"

clean-all: clean ## Clean everything (build + docker volumes)
	@echo "$(BLUE)Cleaning all artifacts...$(NC)"
	@docker-compose down -v 2>/dev/null || true
	@rm -rf qdrant_storage
	@echo "$(GREEN)✓ All artifacts cleaned$(NC)"

reset: clean-all uninstall ## Reset everything (uninstall + clean)
	@echo "$(YELLOW)Removing configuration...$(NC)"
	@rm -rf $(CONFIG_DIR)
	@echo "$(GREEN)✓ Reset complete$(NC)"

info: ## Show project information
	@echo "$(BLUE)IPCrawler Information$(NC)"
	@echo ""
	@echo "Binary name:      $(BINARY_NAME)"
	@echo "Install path:     $(INSTALL_PATH)"
	@echo "Config directory: $(CONFIG_DIR)"
	@echo "Build directory:  $(BUILD_DIR)"
	@echo ""
	@echo "$(YELLOW)Installed:$(NC)"
	@if [ -L "$(INSTALL_PATH)" ]; then \
		echo "  Type: Symlink"; \
		echo "  Target: $$(readlink $(INSTALL_PATH))"; \
	elif [ -f "$(INSTALL_PATH)" ]; then \
		echo "  Type: Binary copy"; \
	else \
		echo "  Status: Not installed"; \
	fi
	@echo ""
	@echo "$(YELLOW)Version:$(NC)"
	@grep '^version' Cargo.toml | head -1

##@ Aliases

all: build-release ## Alias for build-release
	@echo "$(GREEN)✓ Build complete$(NC)"

.PHONY: all
