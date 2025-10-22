# IPCrawler Makefile
# Smart build system with auto-detection and comprehensive checks

# Project configuration
PROJECT_NAME := ipcrawler
BINARY_NAME := ipcrawler
BUILD_DIR := target/release
INSTALL_DIR := /usr/local/bin

# Auto-detect system
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

# System-specific configuration
ifeq ($(UNAME_S),Linux)
    OS := linux
    SYMLINK_CMD := ln -sf
    REMOVE_CMD := rm -f
endif
ifeq ($(UNAME_S),Darwin)
    OS := macos
    SYMLINK_CMD := ln -sf
    REMOVE_CMD := rm -f
endif
ifeq ($(OS),Windows_NT)
    OS := windows
    BINARY_NAME := ipcrawler.exe
    SYMLINK_CMD := mklink
    REMOVE_CMD := del
endif

# Color output - use printf for better compatibility
RED := \x1b[0;31m
GREEN := \x1b[0;32m
YELLOW := \x1b[0;33m
BLUE := \x1b[0;34m
PURPLE := \x1b[0;35m
CYAN := \x1b[0;36m
NC := \x1b[0m # No Color

# Cargo flags
CARGO_BUILD_FLAGS := --release
CARGO_TEST_FLAGS := --all-features
CARGO_CLIPPY_FLAGS := -- -D warnings

# Get absolute path
CURRENT_DIR := $(shell pwd)
BINARY_PATH := $(CURRENT_DIR)/$(BUILD_DIR)/$(BINARY_NAME)

# Default target
.DEFAULT_GOAL := help

# Phony targets
.PHONY: help build check test clean install uninstall run fmt clippy doctor update all

##@ General

help: ## Display this help message
	@echo "$(CYAN)IPCrawler Build System$(NC)"
	@echo "$(BLUE)Detected OS: $(OS) ($(UNAME_M))$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(CYAN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(CYAN)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(PURPLE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Build

build: ## Build optimized release binary and create system symlink
	@printf "$(BLUE)Building $(PROJECT_NAME) for $(OS)...$(NC)\n"
	@cargo build $(CARGO_BUILD_FLAGS)
	@printf "$(GREEN)✓ Build complete: $(BINARY_PATH)$(NC)\n"
	@printf "$(BLUE)Creating system symlink...$(NC)\n"
	@if [ -w "$(INSTALL_DIR)" ]; then \
		$(SYMLINK_CMD) $(BINARY_PATH) $(INSTALL_DIR)/$(BINARY_NAME); \
		printf "$(GREEN)✓ Symlink created: $(INSTALL_DIR)/$(BINARY_NAME) -> $(BINARY_PATH)$(NC)\n"; \
	else \
		printf "$(YELLOW)[!] Need sudo privileges to create system symlink$(NC)\n"; \
		if sudo $(SYMLINK_CMD) $(BINARY_PATH) $(INSTALL_DIR)/$(BINARY_NAME) 2>/dev/null; then \
			printf "$(GREEN)✓ Symlink created: $(INSTALL_DIR)/$(BINARY_NAME) -> $(BINARY_PATH)$(NC)\n"; \
		else \
			printf "$(YELLOW)[!] Could not create system symlink. You can manually create it with:$(NC)\n"; \
			printf "$(YELLOW)  sudo $(SYMLINK_CMD) $(BINARY_PATH) $(INSTALL_DIR)/$(BINARY_NAME)$(NC)\n"; \
			printf "$(YELLOW)  Or run the binary directly: $(BINARY_PATH)$(NC)\n"; \
		fi; \
	fi
	@printf "$(GREEN)✓ You can now run: $(BINARY_NAME)$(NC)\n"

build-dev: ## Build development binary (debug mode)
	@echo "$(BLUE)Building $(PROJECT_NAME) (debug mode)...$(NC)"
	@cargo build
	@echo "$(GREEN)✓ Debug build complete: target/debug/$(BINARY_NAME)$(NC)"

rebuild: clean build ## Clean and rebuild from scratch

##@ Quality Checks

check: fmt-check clippy cargo-check test ## Run all quality checks (fmt, clippy, cargo check, tests)
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✓ All quality checks passed!$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════$(NC)"

fmt: ## Format code with rustfmt
	@echo "$(BLUE)Formatting code...$(NC)"
	@cargo fmt
	@echo "$(GREEN)✓ Code formatted$(NC)"

fmt-check: ## Check code formatting without modifying files
	@echo "$(BLUE)Checking code formatting...$(NC)"
	@cargo fmt -- --check || (echo "$(RED)✗ Code formatting issues found. Run 'make fmt' to fix.$(NC)" && exit 1)
	@echo "$(GREEN)✓ Code formatting is correct$(NC)"

clippy: ## Run clippy linter
	@echo "$(BLUE)Running clippy linter...$(NC)"
	@cargo clippy --all-targets $(CARGO_CLIPPY_FLAGS)
	@echo "$(GREEN)✓ Clippy checks passed$(NC)"

cargo-check: ## Run cargo check
	@echo "$(BLUE)Running cargo check...$(NC)"
	@cargo check --all-targets
	@echo "$(GREEN)✓ Cargo check passed$(NC)"

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	@cargo test $(CARGO_TEST_FLAGS)
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-verbose: ## Run tests with verbose output
	@echo "$(BLUE)Running tests (verbose)...$(NC)"
	@cargo test $(CARGO_TEST_FLAGS) -- --nocapture

bench: ## Run benchmarks
	@echo "$(BLUE)Running benchmarks...$(NC)"
	@cargo bench

##@ Installation

install: build ## Build and install to system (requires sudo)
	@echo "$(GREEN)✓ $(BINARY_NAME) installed to $(INSTALL_DIR)$(NC)"
	@echo "$(YELLOW)Run '$(BINARY_NAME) --help' to get started$(NC)"

uninstall: ## Remove system symlink
	@echo "$(BLUE)Removing system symlink...$(NC)"
	@sudo $(REMOVE_CMD) $(INSTALL_DIR)/$(BINARY_NAME)
	@echo "$(GREEN)✓ $(BINARY_NAME) uninstalled$(NC)"

##@ Development

run: ## Run the application (debug mode)
	@cargo run -- --help

run-release: build ## Run the release binary
	@$(BINARY_PATH) --help

watch: ## Watch for changes and rebuild (requires cargo-watch)
	@command -v cargo-watch >/dev/null 2>&1 || (echo "$(RED)cargo-watch not installed. Run: cargo install cargo-watch$(NC)" && exit 1)
	@echo "$(BLUE)Watching for changes...$(NC)"
	@cargo watch -x build

##@ Maintenance

clean: ## Remove build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@cargo clean
	@echo "$(GREEN)✓ Build artifacts cleaned$(NC)"

update: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	@cargo update
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

outdated: ## Check for outdated dependencies (requires cargo-outdated)
	@command -v cargo-outdated >/dev/null 2>&1 || (echo "$(RED)cargo-outdated not installed. Run: cargo install cargo-outdated$(NC)" && exit 1)
	@echo "$(BLUE)Checking for outdated dependencies...$(NC)"
	@cargo outdated

audit: ## Audit dependencies for security vulnerabilities (requires cargo-audit)
	@command -v cargo-audit >/dev/null 2>&1 || (echo "$(RED)cargo-audit not installed. Run: cargo install cargo-audit$(NC)" && exit 1)
	@echo "$(BLUE)Auditing dependencies...$(NC)"
	@cargo audit

##@ Diagnostics

doctor: ## Run comprehensive system diagnostics
	@echo "$(CYAN)═══════════════════════════════════════════════$(NC)"
	@echo "$(CYAN)IPCrawler System Diagnostics$(NC)"
	@echo "$(CYAN)═══════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(PURPLE)System Information:$(NC)"
	@echo "  OS: $(OS)"
	@echo "  Architecture: $(UNAME_M)"
	@echo "  Shell: $$SHELL"
	@echo ""
	@echo "$(PURPLE)Rust Toolchain:$(NC)"
	@rustc --version || echo "$(RED)rustc not found$(NC)"
	@cargo --version || echo "$(RED)cargo not found$(NC)"
	@rustfmt --version || echo "$(RED)rustfmt not found$(NC)"
	@cargo clippy --version || echo "$(RED)clippy not found$(NC)"
	@echo ""
	@echo "$(PURPLE)Project Status:$(NC)"
	@if [ -f "$(BINARY_PATH)" ]; then \
		echo "  Release binary: $(GREEN)✓ exists$(NC) ($(BINARY_PATH))"; \
		ls -lh $(BINARY_PATH) | awk '{print "  Size: " $$5}'; \
	else \
		echo "  Release binary: $(YELLOW)not built$(NC)"; \
	fi
	@if [ -L "$(INSTALL_DIR)/$(BINARY_NAME)" ]; then \
		echo "  System symlink: $(GREEN)✓ installed$(NC) ($(INSTALL_DIR)/$(BINARY_NAME))"; \
		ls -l $(INSTALL_DIR)/$(BINARY_NAME) | awk '{print "  Points to: " $$NF}'; \
	else \
		echo "  System symlink: $(YELLOW)not installed$(NC)"; \
	fi
	@echo ""
	@echo "$(PURPLE)Security Tools:$(NC)"
	@command -v nmap >/dev/null 2>&1 && echo "  nmap: $(GREEN)✓$(NC)" || echo "  nmap: $(RED)✗$(NC)"
	@command -v nikto >/dev/null 2>&1 && echo "  nikto: $(GREEN)✓$(NC)" || echo "  nikto: $(RED)✗$(NC)"
	@command -v gobuster >/dev/null 2>&1 && echo "  gobuster: $(GREEN)✓$(NC)" || echo "  gobuster: $(RED)✗$(NC)"
	@command -v sqlmap >/dev/null 2>&1 && echo "  sqlmap: $(GREEN)✓$(NC)" || echo "  sqlmap: $(RED)✗$(NC)"
	@command -v masscan >/dev/null 2>&1 && echo "  masscan: $(GREEN)✓$(NC)" || echo "  masscan: $(RED)✗$(NC)"
	@echo ""
	@echo "$(PURPLE)Wordlists:$(NC)"
	@if [ -d "/usr/share/seclists" ]; then \
		echo "  SecLists: $(GREEN)✓ installed$(NC) (/usr/share/seclists)"; \
	else \
		echo "  SecLists: $(YELLOW)not found$(NC)"; \
	fi
	@if [ -f "config/wordlists.yaml" ]; then \
		echo "  Wordlist config: $(GREEN)✓ exists$(NC)"; \
	else \
		echo "  Wordlist config: $(RED)✗ missing$(NC)"; \
	fi
	@echo ""

info: ## Display project information
	@echo "$(CYAN)Project: $(PROJECT_NAME)$(NC)"
	@echo "Binary: $(BINARY_NAME)"
	@echo "Build directory: $(BUILD_DIR)"
	@echo "Install directory: $(INSTALL_DIR)"
	@echo "Binary path: $(BINARY_PATH)"
	@echo ""
	@echo "$(CYAN)Targets:$(NC)"
	@echo "  13 tool definitions"
	@find tools -name "*.yaml" -type f | wc -l | xargs echo "  YAML files:"
	@find tools/scripts -name "*.sh" -type f 2>/dev/null | wc -l | xargs echo "  Shell scripts:"
	@echo ""

size: ## Show binary size
	@if [ -f "$(BINARY_PATH)" ]; then \
		ls -lh $(BINARY_PATH) | awk '{print "Release binary size: " $$5}'; \
		du -h $(BINARY_PATH) | awk '{print "Disk usage: " $$1}'; \
	else \
		echo "$(YELLOW)Release binary not found. Run 'make build' first.$(NC)"; \
	fi

##@ Complete Workflows

all: check build ## Run all checks and build release binary
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✓ All tasks completed successfully!$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════$(NC)"

dev: fmt clippy test ## Run development workflow (format, lint, test)
	@echo "$(GREEN)✓ Development checks complete$(NC)"

ci: fmt-check clippy cargo-check test ## Run CI/CD workflow (all checks without formatting)
	@echo "$(GREEN)✓ CI checks complete$(NC)"

release: clean ci build ## Full release workflow (clean, check, build)
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✓ Release build complete!$(NC)"
	@echo "$(GREEN)Binary: $(BINARY_PATH)$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════$(NC)"

##@ Documentation

docs: ## Generate and open documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@cargo doc --no-deps --open

docs-build: ## Generate documentation without opening
	@echo "$(BLUE)Generating documentation...$(NC)"
	@cargo doc --no-deps
	@echo "$(GREEN)✓ Documentation generated$(NC)"

readme: ## Display README
	@if [ -f "README.md" ]; then \
		cat README.md; \
	else \
		echo "$(RED)README.md not found$(NC)"; \
	fi
