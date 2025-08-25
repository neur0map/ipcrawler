BIN_DIR      := artifacts/bin
BIN          := $(BIN_DIR)/ipcrawler
LOG_DIR      := artifacts/logs
RUN_DIR      := artifacts/runs
PROFILE      ?= release
RUN_ARGS     ?=

.PHONY: help build clean test verbose-build

help:
	@echo "IPCrawler Build System"
	@echo ""
	@echo "Main Commands:"
	@echo "  make build    - Complete setup: compile, check tools, create symlinks, install config"
	@echo "  make clean    - Remove all artifacts, symlinks, and user config"
	@echo "  make test     - Run full validation: environment checks, formatting, linting, tests"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "Tool Installation:"
	@echo "  • Basic DNS tools (nslookup, dig) are required and usually pre-installed"
	@echo "  • Optional Go tools for hosts discovery: dnsx, httpx"
	@echo "  • Install Go tools: go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
	@echo "  •                  go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest"
	@echo ""
	@echo "After 'make build', run: ipcrawler -t google.com"

build:
	@echo "🔧 Building IPCrawler..."
	@echo "[▏         ] 10% - Setting up directories"
	@mkdir -p $(BIN_DIR) $(LOG_DIR) $(RUN_DIR) 2>/dev/null
	@echo "[▏▏        ] 20% - Checking tools"
	@bash scripts/install_tools.sh >/dev/null 2>&1 || echo "  ⚠ Some optional tools missing (continuing)"
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
	@bash scripts/install_tools.sh
	
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

# Swallow incidental phony goals if user passes flags directly
%:
	@: