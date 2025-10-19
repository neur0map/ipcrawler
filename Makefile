# IPCrawler Makefile
# Smart build and initialization system

.PHONY: help build init clean install-deps test lint format check-deps setup-symlink

# Default target
help:
	@echo "IPCrawler - IP-focused reconnaissance tool with LLM-powered output parsing"
	@echo ""
	@echo "Available targets:"
	@echo "  build        - Build the project"
	@echo "  init         - Interactive setup wizard (recommended for first-time users)"
	@echo "  clean        - Clean build artifacts"
	@echo "  install-deps - Install system dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"
	@echo "  check-deps   - Check system dependencies"
	@echo "  help         - Show this help message"

# Build the project
build:
	@echo "Building IPCrawler..."
	cargo build --release
	@echo "Build complete! Binary available at: ./target/release/ipcrawler"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	cargo clean
	@echo "Clean complete!"

# Install system dependencies
install-deps:
	@echo "Installing system dependencies..."
	@./scripts/install_deps.sh

# Check system dependencies
check-deps:
	@echo "Checking system dependencies..."
	@./target/release/ipcrawler scan --help > /dev/null 2>&1 && echo "✓ IPCrawler binary is ready" || echo "✗ IPCrawler binary not found - run 'make build' first"

# Run tests
test:
	@echo "Running tests..."
	cargo test

# Run linting
lint:
	@echo "Running linter..."
	cargo clippy -- -D warnings

# Format code
format:
	@echo "Formatting code..."
	cargo fmt

# Interactive setup wizard
init:
	@echo "🚀 Welcome to IPCrawler Setup Wizard!"
	@echo "====================================="
	@echo ""
	@echo "This wizard will help you configure IPCrawler for optimal performance."
	@echo ""
	@./scripts/setup_wizard.sh

# Setup symlink (called by wizard)
setup-symlink:
	@echo "Setting up IPCrawler symlink..."
	@if [ -L /usr/local/bin/ipcrawler ]; then \
		echo "✓ Symlink already exists at /usr/local/bin/ipcrawler"; \
	elif [ -w /usr/local/bin ]; then \
		ln -sf "$(PWD)/target/release/ipcrawler" /usr/local/bin/ipcrawler && \
		echo "✓ Symlink created: /usr/local/bin/ipcrawler -> $(PWD)/target/release/ipcrawler"; \
	else \
		echo "⚠️  Cannot create symlink in /usr/local/bin (insufficient permissions)"; \
		echo "   Attempting with sudo..."; \
		if sudo ln -sf "$(PWD)/target/release/ipcrawler" /usr/local/bin/ipcrawler 2>/dev/null; then \
			echo "✓ Symlink created with sudo: /usr/local/bin/ipcrawler -> $(PWD)/target/release/ipcrawler"; \
		else \
			echo "❌ Failed to create symlink. Please run manually:"; \
			echo "   sudo ln -sf $(PWD)/target/release/ipcrawler /usr/local/bin/ipcrawler"; \
		fi \
	fi

# Development targets
dev-build:
	@echo "Building in development mode..."
	cargo build

dev-run: dev-build
	@echo "Running IPCrawler in development mode..."
	./target/debug/ipcrawler $(ARGS)

# Installation target
install: build
	@echo "Installing IPCrawler..."
	@if [ -w /usr/local/bin ]; then \
		cp target/release/ipcrawler /usr/local/bin/ && \
		echo "✓ IPCrawler installed to /usr/local/bin/ipcrawler"; \
	else \
		echo "⚠️  Cannot install to /usr/local/bin (insufficient permissions)"; \
		echo "   Run with sudo: make install"; \
	fi

# Uninstallation target
uninstall:
	@echo "Uninstalling IPCrawler..."
	@if [ -f /usr/local/bin/ipcrawler ]; then \
		rm -f /usr/local/bin/ipcrawler && \
		echo "✓ IPCrawler uninstalled from /usr/local/bin/ipcrawler"; \
	else \
		echo "✓ IPCrawler not found in /usr/local/bin"; \
	fi

# Update dependencies
update:
	@echo "Updating dependencies..."
	cargo update

# Check for security vulnerabilities
audit:
	@echo "Checking for security vulnerabilities..."
	cargo audit

# Generate documentation
docs:
	@echo "Generating documentation..."
	cargo doc --open

# Create release package
package: clean build
	@echo "Creating release package..."
	@mkdir -p dist
	@tar -czf dist/ipcrawler-$(shell uname -s)-$(shell uname -m).tar.gz -C target/release ipcrawler
	@echo "✓ Package created: dist/ipcrawler-$(shell uname -s)-$(shell uname -m).tar.gz"