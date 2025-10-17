# IPCrawler Makefile

.PHONY: help build clean install-tools init test

# Default target
help:
	@echo "IPCrawler Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  build         - Build the project"
	@echo "  clean         - Clean build artifacts"
	@echo "  install-tools - Install required tools (auto-detects OS)"
	@echo "  init          - Install binary to /usr/local/bin"
	@echo "  test          - Run basic tests"
	@echo "  help          - Show this help"
	@echo ""
	@echo "Supported systems for install-tools:"
	@echo "  - macOS (Homebrew)"
	@echo "  - Linux (apt, yum, dnf, pacman, zypper)"
	@echo "  - FreeBSD (pkg)"
	@echo "  - Windows (chocolatey, winget)"

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
	@echo "Detecting operating system..."
	@SYSTEM=$$(uname -s); \
	if [ "$$SYSTEM" = "Darwin" ]; then \
		echo "macOS detected. Installing with Homebrew..."; \
		if command -v brew >/dev/null 2>&1; then \
			brew install nmap bind-tools || true; \
		else \
			echo "Homebrew not found. Please install Homebrew first:"; \
			echo "https://brew.sh/"; \
		fi; \
	elif [ "$$SYSTEM" = "Linux" ]; then \
		echo "Linux detected. Installing with package manager..."; \
		if command -v apt >/dev/null 2>&1; then \
			echo "Using apt (Debian/Ubuntu)..."; \
			sudo apt update; \
			sudo apt install -y nmap dnsutils whois traceroute python3-pip pipx || true; \
		elif command -v yum >/dev/null 2>&1; then \
			echo "Using yum (CentOS/RHEL)..."; \
			sudo yum install -y nmap bind-utils whois traceroute python3-pip || true; \
			python3 -m pip install --user pipx || true; \
		elif command -v dnf >/dev/null 2>&1; then \
			echo "Using dnf (Fedora)..."; \
			sudo dnf install -y nmap bind-utils whois traceroute python3-pip || true; \
			python3 -m pip install --user pipx || true; \
		elif command -v pacman >/dev/null 2>&1; then \
			echo "Using pacman (Arch)..."; \
			sudo pacman -S --noconfirm nmap bind whois traceroute python-pip python-pipx || true; \
		elif command -v zypper >/dev/null 2>&1; then \
			echo "Using zypper (openSUSE)..."; \
			sudo zypper install -y nmap bind-utils whois traceroute python3-pip || true; \
			# Install pipx for better Python package management
			python3 -m pip install --user pipx || true; \
			python3 -m pipx ensurepath || true; \
		else \
			echo "Unknown Linux package manager. Please install manually:"; \
			echo "- nmap: Package manager specific"; \
			echo "- dig/dnsutils: Package manager specific"; \
			echo "- whois: Package manager specific"; \
			echo "- traceroute: Package manager specific"; \
		fi; \
	elif [ "$$SYSTEM" = "FreeBSD" ]; then \
		echo "FreeBSD detected. Installing with pkg..."; \
		sudo pkg install -y nmap bind-tools whois traceroute python3 || true; \
	elif [ "$$SYSTEM" = "MINGW64_NT" ] || [ "$$SYSTEM" = "MSYS_NT" ] || [ "$$SYSTEM" = "CYGWIN_NT" ]; then \
		echo "Windows detected. Installing with package managers..."; \
		if command -v choco >/dev/null 2>&1; then \
			echo "Using Chocolatey..."; \
			choco install -y nmap python3 || true; \
		elif command -v winget >/dev/null 2>&1; then \
			echo "Using winget..."; \
			winget install -e --id Insecure.Nmap || true; \
			winget install -e --id Python.Python.3 || true; \
		else \
			echo "No supported package manager found. Please install manually:"; \
			echo "- nmap: https://nmap.org/download.html"; \
			echo "- Python: https://www.python.org/downloads/"; \
		fi; \
	else \
		echo "Unsupported system: $$SYSTEM"; \
		echo "Please install tools manually:"; \
		echo "- nmap: https://nmap.org/download.html"; \
		echo "- dig/dnsutils/bind-tools: System package"; \
		echo "- whois: System package"; \
		echo "- traceroute: System package"; \
	fi
	@echo "Installing Rust tools..."
	@if command -v cargo >/dev/null 2>&1; then \
		cargo install rustscan || true; \
	else \
		echo "Cargo not found. Please install Rust first:"; \
		echo "https://rustup.rs/"; \
	fi
	@echo "Installing Python tools..."
	@if command -v pipx >/dev/null 2>&1; then \
		echo "Using pipx (recommended)..."; \
		pipx install shodan || pip3 install --user shodan || pip install --user shodan || true; \
	elif command -v pip3 >/dev/null 2>&1; then \
		echo "Using pip3 with --user flag..."; \
		pip3 install --user shodan || pip3 install --break-system-packages shodan || pip3 install shodan || true; \
	elif command -v pip >/dev/null 2>&1; then \
		echo "Using pip with --user flag..."; \
		pip install --user shodan || pip install --break-system-packages shodan || pip install shodan || true; \
	else \
		echo "Pip not found. Please install Python and pip first."; \
		echo "Alternative: Install shodan via system package manager or use pipx."; \
	fi
	@echo "Installation complete!"
	@echo "Note: Some tools may require manual setup or API keys (e.g., Shodan)."

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
