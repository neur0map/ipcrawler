# IPCrawler Makefile

.PHONY: help build clean install-tools init test

# Default target
help:
	@echo "IPCrawler Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  build         - Build the project"
	@echo "  clean         - Clean build artifacts"
	@echo "  install-tools - Install required tools"
	@echo "  init          - Install binary to /usr/local/bin"
	@echo "  test          - Run basic tests"
	@echo "  help          - Show this help"

# Build the project
build:
	cargo build --release

# Clean build artifacts
clean:
	cargo clean
	rm -rf raw/ reports/

# Install required tools for IPCrawler
install-tools:
	@echo "Installing required tools..."
	@echo "Checking for Homebrew..."
	@if command -v brew >/dev/null 2>&1; then \
		echo "Homebrew found. Installing tools..."; \
		brew install nmap rustscan bind-tools || true; \
		echo "Installing Rust tools..."; \
		cargo install rustscan || true; \
		echo "Installing Python tools..."; \
		pip3 install shodan || true; \
	else \
		echo "Homebrew not found. Please install manually:"; \
		echo "- nmap: https://nmap.org/download.html"; \
		echo "- rustscan: cargo install rustscan"; \
		echo "- dig: Usually comes with bind-utils (Linux) or system (macOS)"; \
		echo "- whois: Usually system package"; \
		echo "- traceroute: Usually system package"; \
		echo "- shodan: pip install shodan"; \
	fi

# Create symlink in /usr/local/bin
init: build
	@echo "Installing IPCrawler to /usr/local/bin..."
	@if [ -f ./target/release/ipcrawler ]; then \
		sudo ln -sf $(PWD)/target/release/ipcrawler /usr/local/bin/ipcrawler; \
		echo "✓ IPCrawler installed to /usr/local/bin/ipcrawler"; \
		echo "You can now run 'ipcrawler' from anywhere"; \
	else \
		echo "Binary not found. Run 'make build' first"; \
		exit 1; \
	fi

# Run basic tests
test:
	@echo "Running basic IPCrawler test..."
	@if [ -f ./target/release/ipcrawler ]; then \
		echo "✓ Binary exists - IPCrawler is ready"; \
		echo "Run './target/release/ipcrawler 127.0.0.1' to test functionality"; \
	else \
		echo "Binary not found. Run 'make build' first"; \
		exit 1; \
	fi
