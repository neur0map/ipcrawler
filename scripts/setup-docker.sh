#!/bin/bash

# Docker Build and Run Script  
# Usage: ./scripts/setup-docker.sh

check_docker() {
    get_platform_info  # Get platform info first
    
    if ! command -v docker >/dev/null 2>&1; then
        echo "❌ Docker is not installed on $PLATFORM"
        echo ""
        echo "Please install Docker first:"
        case "$OS_ID" in
            macos)
                echo "  • macOS: https://docs.docker.com/desktop/install/mac-install/"
                echo "  • Alternative: brew install --cask docker"
                ;;
            ubuntu|debian|kali|parrot)
                echo "  • Ubuntu/Debian: https://docs.docker.com/engine/install/ubuntu/"
                echo "  • Quick install: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
                ;;
            arch|manjaro)
                echo "  • Arch: sudo pacman -S docker docker-compose"
                echo "  • AUR: yay -S docker-desktop"
                ;;
            *)
                if [ -n "$WSL_DETECTED" ] && [ "$WSL_DETECTED" = "yes" ]; then
                    echo "  • Windows WSL: https://docs.docker.com/desktop/install/windows/"
                    echo "  • Alternative: Install Docker Engine in WSL2"
                else
                    echo "  • General: https://docs.docker.com/engine/install/"
                    echo "  • Ubuntu/Debian: https://docs.docker.com/engine/install/ubuntu/"
                    echo "  • CentOS/RHEL: https://docs.docker.com/engine/install/centos/"
                fi
                ;;
        esac
        echo ""
        exit 1
    fi
    
    # Platform-specific Docker daemon check
    if ! eval $DOCKER_HOST_CHECK; then
        echo "❌ Docker is installed but not running on $PLATFORM"
        echo ""
        echo "Please start Docker and try again:"
        case "$OS_ID" in
            macos)
                echo "  • Start Docker Desktop from Applications"
                echo "  • Or: open -a Docker"
                ;;
            ubuntu|debian|kali|parrot|arch|manjaro)
                echo "  • sudo systemctl start docker"
                echo "  • sudo systemctl enable docker (to start on boot)"
                echo "  • Add user to docker group: sudo usermod -aG docker \$USER"
                ;;
            *)
                if [ -n "$WSL_DETECTED" ] && [ "$WSL_DETECTED" = "yes" ]; then
                    echo "  • Start Docker Desktop from Windows Start Menu"
                    echo "  • Or: Install Docker Engine in WSL and start with: sudo dockerd"
                else
                    echo "  • sudo systemctl start docker"
                    echo "  • sudo systemctl enable docker (to start on boot)"
                fi
                ;;
        esac
        echo ""
        exit 1
    fi
    
    echo "✅ Docker is ready on $PLATFORM!"
    docker --version
    
    # Show additional platform-specific info
    case "$OS_ID" in
        ubuntu|debian|kali|parrot|arch|manjaro)
            if groups | grep -q docker; then
                echo "✅ User is in docker group"
            else
                echo "⚠️  Consider adding user to docker group: sudo usermod -aG docker \$USER"
            fi
            ;;
        macos)
            echo "💡 Using Docker Desktop for macOS"
            ;;
        *)
            if [ -n "$WSL_DETECTED" ] && [ "$WSL_DETECTED" = "yes" ]; then
                echo "💡 Using Docker in WSL environment"
            else
                echo "💡 Docker detected on $OS_ID"
            fi
            ;;
    esac
}

check_image_exists() {
    if docker images -q ipcrawler >/dev/null 2>&1 && [ -n "$(docker images -q ipcrawler)" ]; then
        echo "✅ ipcrawler Docker image found"
        return 0
    else
        echo "ℹ️  ipcrawler Docker image not found"
        return 1
    fi
}

build_ipcrawler_image() {
    echo "🐳 Building ipcrawler Docker image..."
    
    if [ ! -f "Dockerfile" ]; then
        echo "❌ Dockerfile not found in current directory"
        echo "Please run this command from the ipcrawler directory"
        return 1
    fi
    
    if docker build -t ipcrawler . ; then
        echo "✅ ipcrawler Docker image built successfully!"
        return 0
    else
        echo "❌ Failed to build Docker image"
        return 1
    fi
}

verify_tools_in_container() {
    echo "🔧 Verifying all security tools are working..."
    
    # Use the comprehensive tool verification script
    docker run --rm ipcrawler /show-tools.sh
}

get_platform_info() {
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Source the existing OS detection script
    source "$SCRIPT_DIR/detect-os.sh"
    
    # Map OS_ID to PLATFORM for user-friendly display
    case "$OS_ID" in
        macos)
            PLATFORM="macOS"
            DOCKER_HOST_CHECK="docker ps >/dev/null 2>&1"
            ;;
        kali|ubuntu|debian|parrot|arch|manjaro)
            PLATFORM="Linux ($OS_ID)"
            DOCKER_HOST_CHECK="sudo systemctl status docker >/dev/null 2>&1 || docker ps >/dev/null 2>&1"
            ;;
        *)
            if [ -n "$WSL_DETECTED" ] && [ "$WSL_DETECTED" = "yes" ]; then
                PLATFORM="Windows (WSL: $OS_ID)"
                DOCKER_HOST_CHECK="docker ps >/dev/null 2>&1"
            else
                PLATFORM="$OS_ID"
                DOCKER_HOST_CHECK="docker ps >/dev/null 2>&1"
            fi
            ;;
    esac
}

start_docker_terminal() {
    get_platform_info
    
    echo "🚀 Starting ipcrawler Docker terminal..."
    echo "🖥️  Platform: $PLATFORM"
    echo ""
    echo "📋 Available commands once inside:"
    echo "  • /show-tools.sh            (List all available tools)"
    echo "  • ipcrawler --help          (Show help)"
    echo "  • ipcrawler 127.0.0.1       (Test scan)"
    echo "  • ipcrawler target.com      (Scan target)" 
    echo "  • ls /scans                 (View results)"
    echo "  • exit                      (Leave container)"
    echo ""
    echo "💾 Results will be saved to: $(pwd)/results/"
    echo ""
    
    # Create results directory if it doesn't exist
    mkdir -p results
    
    # Verify tools before starting interactive session
    verify_tools_in_container
    echo ""
    
    # Platform-specific Docker run with better compatibility
    echo "🐳 Launching cross-platform Docker container..."
    
    # Use absolute path for better Windows compatibility
    RESULTS_DIR="$(cd "$(pwd)/results" && pwd)" 2>/dev/null || RESULTS_DIR="$(pwd)/results"
    
    # Run the container with platform-optimized settings
    docker run -it --rm \
        -v "$RESULTS_DIR:/scans" \
        -w /scans \
        --name "ipcrawler-session-$(date +%s)" \
        --platform linux/amd64 \
        ipcrawler bash
        
    echo ""
    echo "👋 ipcrawler session ended"
    echo "📁 Check your results in: $(pwd)/results/"
    
    # Platform-specific result viewing hint
    case "$OS_ID" in
        macos)
            echo "💡 On macOS: open $(pwd)/results"
            ;;
        ubuntu|debian|kali|parrot)
            echo "💡 On Linux: nautilus $(pwd)/results (or your file manager)"
            ;;
        arch|manjaro)
            echo "💡 On Arch: dolphin $(pwd)/results (or your file manager)"
            ;;
        *)
            if [ -n "$WSL_DETECTED" ] && [ "$WSL_DETECTED" = "yes" ]; then
                echo "💡 On WSL: explorer.exe $(pwd | sed 's|/mnt/c|C:|')/results"
                echo "💡 Or: cd $(pwd)/results && explorer.exe ."
            else
                echo "💡 View results: ls $(pwd)/results"
            fi
            ;;
    esac
}

# Main execution
main() {
    echo "🐳 ipcrawler Docker Setup"
    echo ""
    
    # Check Docker availability
    check_docker
    echo ""
    
    # Check if image exists, build if needed
    if check_image_exists; then
        echo "🚀 Image ready! Starting Docker terminal..."
    else
        echo ""
        build_ipcrawler_image
        if [ $? -ne 0 ]; then
            exit 1
        fi
    fi
    
    echo ""
    start_docker_terminal
}

# Run if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi 