# Makefile for ipcrawler build and release engineering
# Enforces hard separation between development and production binaries

.PHONY: all build build-prod build-both where verify test lint fmt audit bench validate clean help install-tools

# Default development target
all: validate build test

# ═══════════════════════════════════════════════════════════════════════════════
# BINARY MANAGEMENT TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

# Build development binary (same features as production, just different paths)
build:
	@echo "🔨 Building development binary..."
	cargo build --release
	cargo build
	@echo "✅ Development binary built: ./target/release/ipcrawler"
	@echo "   • Uses project directory for configs and results"
	@echo "   • Version shows +dev when run from project directory"
	@echo "   • Use 'make where' to see all binaries"

# Build and atomically replace production binary on system PATH
build-prod:
	@echo "🚀 Building production binary..."
	cargo build --release
	@echo "✅ Production binary built (identical features to dev)"
	@echo "🔄 Installing to system PATH..."
	@DEST_PATH=$$(command -v ipcrawler 2>/dev/null || echo "/usr/local/bin/ipcrawler"); \
	./scripts/ipcrawler-manager.sh replace ./target/release/ipcrawler "$$DEST_PATH"
	@echo
	@echo "📍 Production binary status:"
	@./scripts/ipcrawler-manager.sh show

# Build both development and production binaries in sequence
build-both:
	@echo "🏗️  Building both development and production binaries..."
	@echo
	@echo "Step 1: Building unified binary..."
	cargo build --release
	cargo build
	@echo "✅ Binary built with unified features"
	@echo
	@echo "Step 2: Installing production binary to system PATH..."
	@DEST_PATH=$$(command -v ipcrawler 2>/dev/null || echo "/usr/local/bin/ipcrawler"); \
	./scripts/ipcrawler-manager.sh replace ./target/release/ipcrawler "$$DEST_PATH"
	@echo
	@echo "🎉 Both binaries ready:"
	@echo "   📁 Development: ./target/release/ipcrawler (uses project paths)"
	@echo "   🚀 Production:  $$(command -v ipcrawler 2>/dev/null || echo "/usr/local/bin/ipcrawler") (uses system paths)"
	@echo "   Note: Both binaries have identical features - only paths differ"
	@echo
	@echo "📍 Binary status:"
	@./scripts/ipcrawler-manager.sh show

# Show all ipcrawler binaries with detailed diagnostics
where:
	@./scripts/ipcrawler-manager.sh show

# Verify binary separation and detect issues
verify:
	@./scripts/ipcrawler-manager.sh verify

# ═══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL BUILD TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

# Build size-optimized binary (for distribution)
build-lean:
	@echo "📦 Building lean binary (size-optimized)..."
	cargo build --profile lean
	@echo "📏 Binary size comparison:"
	@ls -lh target/lean/ipcrawler target/release/ipcrawler 2>/dev/null || echo "Build both first"

# ═══════════════════════════════════════════════════════════════════════════════
# DEVELOPMENT TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

# Run all tests
test:
	@echo "🧪 Running tests..."
	cargo test --all-features
	
# Run property-based tests
proptest:
	@echo "🎲 Running property-based tests..."
	cargo test --test proptest -- --nocapture

# Format code
fmt:
	@echo "🎨 Formatting code..."
	cargo fmt --all

# Run clippy linting
lint:
	@echo "🔍 Linting with clippy..."
	cargo clippy --all-targets --all-features -- -D warnings

# Run security audit
audit:
	@echo "🔐 Running security audit..."
	cargo audit

# Run benchmarks
bench:
	@echo "📊 Running benchmarks..."
	cargo bench --all-features

# Memory safety check with miri (requires nightly)
miri:
	@echo "🧠 Running miri checks..."
	cargo +nightly miri test

# Validate configurations
validate:
	@echo "✅ Validating configurations..."
	cargo run --bin validate-tools-config
	yamllint config/
	
# Check for unused dependencies
deps-check:
	@echo "📦 Checking for unused dependencies..."
	cargo machete

# Run all validation checks
validate-all: fmt lint test audit validate deps-check
	@echo "✅ All validation checks passed!"

# Generate test coverage report
coverage:
	@echo "📈 Generating coverage report..."
	cargo tarpaulin --all-features --out Html --output-dir coverage/

# Profile memory usage
profile-memory:
	@echo "💾 Profiling memory usage..."
	cargo run --bin ipcrawler -- --dry-run -t 127.0.0.1 | dhat-viewer

# Install development tools
install-tools:
	@echo "🛠️ Installing development tools..."
	cargo install cargo-audit
	cargo install cargo-machete
	cargo install cargo-tarpaulin
	cargo install cargo-fuzz
	rustup component add miri --toolchain nightly
	pip3 install pre-commit yamllint
	
# Setup pre-commit hooks
setup-hooks:
	@echo "🪝 Setting up pre-commit hooks..."
	pre-commit install
	
# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	cargo clean
	rm -rf coverage/
	rm -rf target/criterion/

# Update dependencies
update:
	@echo "⬆️ Updating dependencies..."
	cargo update

# Generate documentation
docs:
	@echo "📚 Generating documentation..."
	cargo doc --all-features --no-deps --open

# Run fuzzing tests
fuzz:
	@echo "🐛 Running fuzz tests..."
	cargo fuzz run parser_fuzz -- -max_total_time=60

# Performance profiling
profile:
	@echo "⚡ Profiling performance..."
	cargo build --release
	perf record --call-graph=dwarf ./target/release/ipcrawler --dry-run -t 127.0.0.1
	perf report

# Stress test with many targets
stress-test:
	@echo "💪 Running stress test..."
	seq 1 100 | xargs -P 10 -I {} ./target/release/ipcrawler --dry-run -t 192.168.1.{} &

# Check binary size and dependencies
analyze:
	@echo "🔬 Analyzing binary..."
	@echo "Binary size:"
	@ls -lh target/release/ipcrawler
	@echo "\nDynamic dependencies:"
	@otool -L target/release/ipcrawler 2>/dev/null || ldd target/release/ipcrawler 2>/dev/null || echo "Not available"

# Help
help:
	@echo "═══════════════════════════════════════════════════════════════════════════════"
	@echo "ipcrawler Build & Release Engineering Targets"
	@echo "═══════════════════════════════════════════════════════════════════════════════"
	@echo
	@echo "🔧 BINARY MANAGEMENT (Primary Targets):"
	@echo "  build        - Build development binary (./target/release/ipcrawler +dev)"
	@echo "  build-prod   - Build & install production binary to system PATH"
	@echo "  build-both   - Build both dev and prod binaries in one command"
	@echo "  where        - Show all ipcrawler binaries with diagnostics"
	@echo "  verify       - Verify binary separation, detect duplicates"
	@echo
	@echo "🛠️  DEVELOPMENT:"
	@echo "  test         - Run all tests"
	@echo "  lint         - Run clippy linting"
	@echo "  fmt          - Format code with rustfmt"
	@echo "  validate     - Validate configurations"
	@echo "  clean        - Clean build artifacts"
	@echo
	@echo "📊 ANALYSIS & OPTIMIZATION:"
	@echo "  build-lean   - Build size-optimized binary"
	@echo "  audit        - Security audit"
	@echo "  coverage     - Generate test coverage"
	@echo "  bench        - Run benchmarks"
	@echo
	@echo "💡 QUICK DIAGNOSIS:"
	@echo "  make where   - See which binaries exist and which is active"
	@echo "  make verify  - Check if dev/prod separation is working"
	@echo
	@echo "⚠️  IMPORTANT: Never run 'make install' - use 'make build-prod' instead"