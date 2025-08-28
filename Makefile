BIN_DIR      := artifacts/bin
BIN          := $(BIN_DIR)/ipcrawler
LOG_DIR      := artifacts/logs
RUN_DIR      := artifacts/runs
PROFILE      ?= release
RUN_ARGS     ?=

.PHONY: help build clean test verbose-build install-tools check-tools install-go

help:
	@echo "IPCrawler Build System"
	@echo ""
	@echo "Main Commands:"
	@echo "  make build         - Complete setup: compile, install tools, create symlinks, install config"
	@echo "  make install-go    - Install/update Go compiler with HTB VM support"
	@echo "  make install-tools - Install/update all reconnaissance tools only"
	@echo "  make check-tools   - Verify all tools are available (no installation)"
	@echo "  make clean         - Remove all artifacts, symlinks, and user config"
	@echo "  make test          - Run full validation: environment checks, formatting, linting, tests"
	@echo "  make help          - Show this help message"
	@echo ""
	@echo "Tool Installation:"
	@echo "  • 'make build' automatically installs ALL missing tools"
	@echo "  • Go compiler: 'make install-go' (HTB VM compatible)"
	@echo "  • DNS tools: dig (via brew/apt)"
	@echo "  • Go tools: dnsx, httpx, katana, hakrawler, ffuf (via go install)"
	@echo "  • Rust tools: rustscan, feroxbuster, xh (via cargo install)"
	@echo "  • System tools: nmap, gobuster, cewl (via brew/apt)"
	@echo "  • SecLists wordlists (via git clone)"
	@echo "  • Requires: Homebrew/apt, Go compiler, Rust/Cargo"
	@echo ""
	@echo "After 'make build', run: ipcrawler -t google.com"

build:
	@echo "🔧 Building IPCrawler..."
	@echo "[▏         ] 10% - Setting up directories"
	@mkdir -p $(BIN_DIR) $(LOG_DIR) $(RUN_DIR) 2>/dev/null
	@echo "[▏▏        ] 20% - Installing and checking tools"
	@if bash scripts/install_tools.sh; then \
		echo "  ✅ All tools installed successfully"; \
	else \
		echo "  ⚠️  Some tools failed to install - see warnings above"; \
		echo "  ⚠️  Run 'make check-tools' after build to see what's missing"; \
		echo "  ⚠️  IPCrawler will work but some plugins may be disabled"; \
	fi
	@echo "[▏▏▏       ] 30% - Starting compilation"
	@echo "[▏▏▏▏      ] 40% - Compiling dependencies"
	@echo "[▏▏▏▏▏     ] 50% - Compiling ipcrawler"
	@cargo build --release --quiet || (echo "  ✗ Compilation failed" && exit 1)
	@echo "[▏▏▏▏▏▏▏   ] 70% - Optimizing release build"
	@echo "[▏▏▏▏▏▏▏▏  ] 80% - Copying binary"
	@cp -f target/release/ipcrawler $(BIN) 2>/dev/null
	@echo "[▏▏▏▏▏▏▏▏▏ ] 90% - Installing system integration"
	@mkdir -p ~/.local/bin 2>/dev/null
	@rm -f ~/.local/bin/ipcrawler 2>/dev/null || true
	@ln -sf $(PWD)/$(BIN) ~/.local/bin/ipcrawler 2>/dev/null
	@mkdir -p ~/.config/ipcrawler 2>/dev/null
	@cp -f global.toml ~/.config/ipcrawler/global.toml 2>/dev/null
	@echo "[▏▏▏▏▏▏▏▏▏▏] 100% - Complete!"
	@echo "✅ IPCrawler build successful! Try: ipcrawler -t google.com"

verbose-build:
	@echo "🔧 Setting up IPCrawler..."
	@mkdir -p $(BIN_DIR) $(LOG_DIR) $(RUN_DIR)
	
	@echo "📦 Installing/verifying required tools..."
	@bash scripts/install_tools.sh || echo "⚠️  Some tool installations failed - continuing with build"
	
	@echo "🔨 Building IPCrawler..."
	@cargo build --release
	@cp -f target/release/ipcrawler $(BIN)
	
	@echo "🔗 Creating system integration..."
	@mkdir -p ~/.local/bin
	@rm -f ~/.local/bin/ipcrawler
	@ln -sf $(PWD)/$(BIN) ~/.local/bin/ipcrawler
	
	@echo "⚙️  Installing configuration..."
	@mkdir -p ~/.config/ipcrawler
	@cp -f global.toml ~/.config/ipcrawler/global.toml
	
	@echo "✅ IPCrawler is ready! Try: ipcrawler -t google.com"
	@echo "💡 Add ~/.local/bin to PATH if needed: export PATH=~/.local/bin:$$PATH"

test:
	@echo "🧪 Running full test suite..."
	
	@echo "🔍 Verifying environment and tools..."
	@bash scripts/check_tools.sh
	@mkdir -p $(RUN_DIR) $(LOG_DIR) && touch $(LOG_DIR)/.write && rm $(LOG_DIR)/.write
	
	@echo "🎨 Checking code formatting..."
	@cargo fmt --all --check || (echo "❌ Code formatting issues found. Run 'cargo fmt --all' to fix." && exit 1)
	
	@echo "🔎 Running linter..."
	@cargo clippy -- -D warnings
	
	@echo "🧪 Running unit tests..."
	@cargo test
	
	@echo "✅ All tests passed!"

clean:
	@echo "🧹 Cleaning up IPCrawler..."
	@cargo clean
	@rm -rf artifacts/
	@echo "🔗 Removing system integration..."
	@rm -f ~/.local/bin/ipcrawler
	@echo "⚙️  Removing user configuration..."
	@rm -rf ~/.config/ipcrawler
	@echo "✅ Cleanup complete"

install-go:
	@echo "🔧 Installing/updating Go compiler for IPCrawler..."
	@bash scripts/install_go.sh
	@echo "💡 After Go installation, run 'make install-tools' to install Go-based reconnaissance tools"

install-tools:
	@echo "🔧 Installing/updating IPCrawler reconnaissance tools..."
	@bash scripts/install_tools.sh
	@echo "✅ Tool installation complete!"
	@echo "💡 Run 'make check-tools' to verify all tools are working"

check-tools:
	@bash scripts/check_tools.sh

# Swallow incidental phony goals if user passes flags directly
%:
	@: