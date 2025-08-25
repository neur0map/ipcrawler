BIN_DIR      := artifacts/bin
BIN          := $(BIN_DIR)/ipcrawler
LOG_DIR      := artifacts/logs
RUN_DIR      := artifacts/runs
PROFILE      ?= release
RUN_ARGS     ?=

.PHONY: help build clean test

help:
	@echo "IPCrawler Build System"
	@echo ""
	@echo "Main Commands:"
	@echo "  make build    - Complete setup: compile, install tools, create symlinks, install config"
	@echo "  make clean    - Remove all artifacts, symlinks, and user config"
	@echo "  make test     - Run full validation: environment checks, formatting, linting, tests"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "After 'make build', run: ipcrawler -t google.com"

build:
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