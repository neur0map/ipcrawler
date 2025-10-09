#!/bin/bash

set -e

REPO="neur0map/ipcrawler"
BINARY_NAME="ipcrawler"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
VERSION="stable"
FORCE=false

print_help() {
    cat << EOF
ipcrawler installer

Usage: $0 [OPTIONS]

OPTIONS:
    --unstable          Install the latest unstable build (default: stable)
    --version VERSION   Install a specific version (e.g., v1.0.0)
    --dir DIR          Installation directory (default: ~/.local/bin)
    --force            Force reinstall even if already installed
    -h, --help         Show this help message

EXAMPLES:
    # Install stable version
    curl -fsSL https://raw.githubusercontent.com/$REPO/main/install.sh | bash

    # Install unstable version
    curl -fsSL https://raw.githubusercontent.com/$REPO/main/install.sh | bash -s -- --unstable

    # Install specific version
    curl -fsSL https://raw.githubusercontent.com/$REPO/main/install.sh | bash -s -- --version v1.0.0

    # Install to custom directory
    curl -fsSL https://raw.githubusercontent.com/$REPO/main/install.sh | bash -s -- --dir /usr/local/bin

EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --unstable)
            VERSION="unstable"
            shift
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

detect_platform() {
    local os=""
    local arch=""
    
    case "$(uname -s)" in
        Linux*)
            os="linux"
            ;;
        Darwin*)
            os="macos"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            os="windows"
            ;;
        *)
            echo "Error: Unsupported operating system: $(uname -s)"
            exit 1
            ;;
    esac
    
    case "$(uname -m)" in
        x86_64|amd64)
            arch="x86_64"
            ;;
        aarch64|arm64)
            arch="aarch64"
            ;;
        *)
            echo "Error: Unsupported architecture: $(uname -m)"
            exit 1
            ;;
    esac
    
    echo "${os}-${arch}"
}

get_download_url() {
    local platform="$1"
    local version="$2"
    local asset_name=""
    
    if [ "$version" = "unstable" ]; then
        asset_name="${BINARY_NAME}-unstable-${platform}"
    else
        asset_name="${BINARY_NAME}-${platform}"
    fi
    
    if [[ "$platform" == *"windows"* ]]; then
        asset_name="${asset_name}.exe.zip"
    else
        asset_name="${asset_name}.tar.gz"
    fi
    
    if [ "$version" = "unstable" ]; then
        echo "https://github.com/${REPO}/releases/download/unstable/${asset_name}"
    else
        if [ "$version" = "stable" ]; then
            echo "https://github.com/${REPO}/releases/latest/download/${asset_name}"
        else
            echo "https://github.com/${REPO}/releases/download/${version}/${asset_name}"
        fi
    fi
}

main() {
    echo "ipcrawler installer"
    echo "==================="
    echo ""
    
    if [ "$FORCE" = false ] && command -v "$BINARY_NAME" &> /dev/null; then
        echo "✓ $BINARY_NAME is already installed at: $(which $BINARY_NAME)"
        echo "  Version: $($BINARY_NAME --version 2>/dev/null || echo 'unknown')"
        echo ""
        echo "Use --force to reinstall"
        exit 0
    fi
    
    local platform
    platform=$(detect_platform)
    echo "Detected platform: $platform"
    echo "Installing version: $VERSION"
    echo "Installation directory: $INSTALL_DIR"
    echo ""
    
    if [ ! -d "$INSTALL_DIR" ]; then
        echo "Creating installation directory: $INSTALL_DIR"
        mkdir -p "$INSTALL_DIR"
    fi
    
    local download_url
    download_url=$(get_download_url "$platform" "$VERSION")
    echo "Download URL: $download_url"
    echo ""
    
    local tmp_dir
    tmp_dir=$(mktemp -d)
    trap "rm -rf $tmp_dir" EXIT
    
    echo "Downloading binary..."
    if ! curl -fsSL "$download_url" -o "$tmp_dir/archive"; then
        echo "Error: Failed to download binary"
        echo "Please check that the release exists and your internet connection is working"
        exit 1
    fi
    
    echo "Extracting binary..."
    cd "$tmp_dir"
    
    if [[ "$download_url" == *.zip ]]; then
        if command -v unzip &> /dev/null; then
            unzip -q archive
        else
            echo "Error: unzip is not installed"
            exit 1
        fi
        binary_file="${BINARY_NAME}.exe"
    else
        tar xzf archive
        binary_file="$BINARY_NAME"
    fi
    
    if [ ! -f "$binary_file" ]; then
        echo "Error: Binary not found in archive"
        exit 1
    fi
    
    echo "Installing binary to $INSTALL_DIR/$BINARY_NAME..."
    chmod +x "$binary_file"
    mv "$binary_file" "$INSTALL_DIR/$BINARY_NAME"
    
    echo ""
    echo "✓ Installation complete!"
    echo ""
    
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        echo "⚠ Warning: $INSTALL_DIR is not in your PATH"
        echo ""
        echo "Add this line to your shell configuration file (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
        echo ""
        echo "Then reload your shell or run:"
        echo "  source ~/.bashrc  # or ~/.zshrc"
        echo ""
    fi
    
    if [ -f "$INSTALL_DIR/$BINARY_NAME" ]; then
        echo "Installed version:"
        "$INSTALL_DIR/$BINARY_NAME" --version 2>/dev/null || echo "Unable to determine version"
        echo ""
        echo "Run '$BINARY_NAME --help' to get started"
    fi
}

if [ -z "$REPO" ] || [ "$REPO" = "OWNER/REPO" ]; then
    echo "Error: REPO variable not set"
    echo "This script needs to be configured with the repository owner and name"
    echo "Please edit the script and set REPO='owner/repo'"
    exit 1
fi

main
