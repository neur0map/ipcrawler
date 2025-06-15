.PHONY: setup clean setup-docker docker-cmd help update

setup:
	@echo "Setting up ipcrawler..." && \
	echo "" && \
	./scripts/system-check.sh && \
	echo "" && \
	. scripts/detect-os.sh && \
	./scripts/install-tools.sh "$$OS_ID" "$$OS_ID_LIKE" "$$WSL_DETECTED" && \
	echo "" && \
	./scripts/setup-python.sh

clean:
	@./scripts/cleanup.sh

setup-docker:
	@./scripts/setup-docker.sh

docker-cmd:
	@echo "Starting ipcrawler Docker container..."
	@echo "Results will be saved to: $$(pwd)/results"
	@echo "Type 'exit' to leave the container"
	@echo ""
	@mkdir -p results
	docker run -it --rm -v "$$(pwd)/results:/scans" -w /scans ipcrawler || true

help:
	@echo "Available make commands:"
	@echo ""
	@echo "  setup         - Set up local Python virtual environment + install 25+ security tools"
	@echo "  clean         - Remove local setup, virtual environment, and Docker resources"
	@echo "  setup-docker  - Build Docker image + open interactive terminal for ipcrawler"
	@echo "  update        - Update repository, tools, and Docker image"
	@echo "  docker-cmd    - Run interactive Docker container"
	@echo "  help          - Show this help message"
	@echo ""
	@echo "Supported Operating Systems:"
	@echo "  • Kali Linux       - Full tool installation (25+ security tools including tnscmd10g)"
	@echo "  • Parrot OS        - Full tool installation (25+ security tools including tnscmd10g)"
	@echo "  • Ubuntu/Debian    - Full tool installation (25+ security tools with fallbacks)"
	@echo "  • macOS (Homebrew) - Comprehensive toolkit (15+ security tools)"
	@echo "  • Arch/Manjaro     - Basic tools (nmap, curl, wget, git)"
	@echo "  • Other systems    - Python setup only (use Docker for full features)"
	@echo ""
	@echo "Windows Usage (Docker):"
	@echo "  1. Install Docker Desktop for Windows"
	@echo "  2. Double-click: ipcrawler-windows.bat    # Easy GUI setup"
	@echo "  3. Or use: make setup-docker              # Command line setup"
	@echo "  4. Inside container: /show-tools.sh       # Verify 25+ tools installed"
	@echo ""
	@echo "Docker Usage (Recommended for non-Kali systems):"
	@echo "  1. Install Docker manually for your OS first"
	@echo "  2. make setup-docker    # Build image + open interactive terminal"
	@echo "  3. make docker-cmd      # Start additional interactive sessions"
	@echo "  4. Inside container: /show-tools.sh or /install-extra-tools.sh"
	@echo ""
	@echo "Local Usage:"
	@echo "  1. make setup           # Set up locally with auto tool installation"
	@echo "  2. ipcrawler --help     # Use the tool"
	@echo "  3. make update          # Keep everything updated"
	@echo ""
	@echo "Tool Installation Features:"
	@echo "  • Automatic fallback methods (apt → snap → pip → go install)"
	@echo "  • Detailed installation feedback and error reporting"
	@echo "  • Oracle tools (tnscmd10g) with multiple installation attempts"
	@echo "  • Skip unavailable tools gracefully with --ignore-plugin-checks"

update:
	@./scripts/update.sh
