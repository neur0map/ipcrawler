#!/bin/bash

# IPCrawler Setup Wizard
# Interactive configuration script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    
    while true; do
        if [ "$default" = "y" ]; then
            read -p "$(echo -e ${PURPLE}$prompt${NC} ${YELLOW}[Y/n]${NC}: )" response
        else
            read -p "$(echo -e ${PURPLE}$prompt${NC} ${YELLOW}[y/N]${NC}: )" response
        fi
        
        response=${response:-$default}
        case $response in
            [Yy]|[Yy][Ee][Ss]) return 0 ;;
            [Nn]|[Nn][Oo]) return 1 ;;
            *) echo "Please answer yes or no." ;;
        esac
    done
}

ask_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$(echo -e ${PURPLE}$prompt${NC} ${YELLOW}[$default]${NC}: )" response
        response=${response:-$default}
    else
        read -p "$(echo -e ${PURPLE}$prompt${NC}: )" response
        while [ -z "$response" ]; do
            echo -e "${RED}This field is required.${NC}"
            read -p "$(echo -e ${PURPLE}$prompt${NC}: )" response
        done
    fi
    
    eval "$var_name='$response'"
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        elif [ -f /etc/arch-release ]; then
            echo "arch"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

check_tool() {
    local tool="$1"
    if command -v "$tool" >/dev/null 2>&1; then
        local version=$("$tool" --version 2>/dev/null || echo "unknown")
        echo "✓ $tool ($version)"
        return 0
    else
        echo "✗ $tool (not found)"
        return 1
    fi
}

install_tool() {
    local tool="$1"
    local os=$(detect_os)
    
    print_info "Attempting to install $tool..."
    
    case $os in
        "debian")
            if command -v apt >/dev/null 2>&1; then
                sudo apt update && sudo apt install -y "$tool"
            else
                print_error "apt not found. Please install $tool manually."
                return 1
            fi
            ;;
        "redhat")
            if command -v yum >/dev/null 2>&1; then
                sudo yum install -y "$tool"
            elif command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y "$tool"
            else
                print_error "Neither yum nor dnf found. Please install $tool manually."
                return 1
            fi
            ;;
        "arch")
            if command -v pacman >/dev/null 2>&1; then
                sudo pacman -S --noconfirm "$tool"
            else
                print_error "pacman not found. Please install $tool manually."
                return 1
            fi
            ;;
        "macos")
            if command -v brew >/dev/null 2>&1; then
                brew install "$tool"
            else
                print_error "Homebrew not found. Please install Homebrew first: https://brew.sh"
                return 1
            fi
            ;;
        "windows")
            print_error "Automatic installation not supported on Windows. Please install $tool manually."
            return 1
            ;;
        *)
            print_error "Unsupported OS for automatic installation. Please install $tool manually."
            return 1
            ;;
    esac
    
    if check_tool "$tool" >/dev/null 2>&1; then
        print_success "$tool installed successfully"
        return 0
    else
        print_error "Failed to install $tool"
        return 1
    fi
}

# Main wizard starts here
main() {
    print_header "🚀 IPCrawler Setup Wizard"
    echo "====================================="
    echo ""
    print_info "This wizard will help you configure IPCrawler for optimal performance."
    echo ""
    
    # Check if Rust and Cargo are installed
    if ! command -v cargo >/dev/null 2>&1; then
        print_error "Rust/Cargo not found. Please install Rust first:"
        echo "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
        exit 1
    fi
    
    print_success "Rust/Cargo found: $(cargo --version)"
    
    # Step 1: Build the project
    echo ""
    print_header "Step 1: Building IPCrawler"
    if ask_yes_no "Would you like to build IPCrawler now?" "y"; then
        make build
        print_success "IPCrawler built successfully"
    else
        print_warning "Skipping build. You can build later with 'make build'"
    fi
    
    # Step 2: System symlink setup
    echo ""
    print_header "Step 2: System Integration"
    print_info "You can create a symlink to use 'ipcrawler' from anywhere."
    
    if ask_yes_no "Create symlink for system-wide access?" "y"; then
        if [ -f "./target/release/ipcrawler" ]; then
            make setup-symlink
            
            # Check if symlink was created successfully
            if ! command -v ipcrawler >/dev/null 2>&1; then
                echo ""
                print_warning "System-wide symlink failed. Creating user-local symlink..."
                mkdir -p ~/.local/bin
                ln -sf "$(PWD)/target/release/ipcrawler" ~/.local/bin/ipcrawler
                
                # Add to PATH if not already there
                if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
                    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc 2>/dev/null
                    export PATH="$HOME/.local/bin:$PATH"
                    print_success "Added ~/.local/bin to PATH in your shell config"
                fi
                
                if command -v ipcrawler >/dev/null 2>&1; then
                    print_success "User-local symlink created successfully!"
                else
                    print_error "Failed to create symlink. Please add to PATH manually:"
                    echo "  export PATH=\"$(pwd)/target/release:\$PATH\""
                fi
            fi
        else
            print_warning "IPCrawler binary not found. Building first..."
            make build
            make setup-symlink
        fi
    else
        print_info "You can create the symlink later with 'make setup-symlink'"
        print_info "Or add to PATH: export PATH=\"$(pwd)/target/release:\$PATH\""
    fi
    
    # Step 3: Tool inspection and installation
    echo ""
    print_header "Step 3: Tool Inspection"
    print_info "Checking for essential reconnaissance tools..."
    echo ""
    
    # Essential tools for reconnaissance
    local tools=(
        "nmap:Network scanner and security auditor"
        "dig:DNS lookup utility"
        "ping:Network connectivity tester"
        "traceroute:Network route tracer"
        "whois:Domain information lookup"
        "curl:Data transfer tool"
        "openssl:SSL/TLS toolkit"
    )
    
    local missing_tools=()
    
    echo "Checking installed tools:"
    for tool_info in "${tools[@]}"; do
        local tool=$(echo "$tool_info" | cut -d: -f1)
        local description=$(echo "$tool_info" | cut -d: -f2)
        
        if check_tool "$tool"; then
            print_success "$tool is available"
        else
            missing_tools+=("$tool:$description")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo ""
        print_warning "Missing tools detected:"
        for tool_info in "${missing_tools[@]}"; do
            local tool=$(echo "$tool_info" | cut -d: -f1)
            local description=$(echo "$tool_info" | cut -d: -f2)
            echo "  ✗ $tool - $description"
        done
        
        echo ""
        if ask_yes_no "Would you like to install missing tools automatically?" "y"; then
            for tool_info in "${missing_tools[@]}"; do
                local tool=$(echo "$tool_info" | cut -d: -f1)
                echo ""
                if ask_yes_no "Install $tool?" "y"; then
                    install_tool "$tool" || print_warning "Failed to install $tool. You can install it manually."
                fi
            done
        else
            print_info "You can install tools later with 'make install-deps'"
        fi
    else
        print_success "All essential tools are installed!"
    fi
    
    # Step 4: LLM Provider Configuration
    echo ""
    print_header "Step 4: LLM Provider Configuration"
    print_info "IPCrawler uses LLM providers to parse tool outputs intelligently."
    echo ""
    
    local providers=(
        "groq:Fast, affordable, high-quality models"
        "openai:GPT models with excellent reasoning"
        "openrouter:Access to multiple model providers"
        "ollama:Local models (requires local setup)"
    )
    
    echo "Available LLM providers:"
    for i in "${!providers[@]}"; do
        local provider=$(echo "${providers[$i]}" | cut -d: -f1)
        local description=$(echo "${providers[$i]}" | cut -d: -f2)
        echo "  $((i+1)). $provider - $description"
    done
    
    echo ""
    ask_input "Select LLM provider (1-4)" "" provider_choice
    
    case $provider_choice in
        1) selected_provider="groq" ;;
        2) selected_provider="openai" ;;
        3) selected_provider="openrouter" ;;
        4) selected_provider="ollama" ;;
        *) 
            print_error "Invalid choice. Defaulting to groq."
            selected_provider="groq"
            ;;
    esac
    
    print_info "Selected provider: $selected_provider"
    
    # Check if API key already exists for this provider
    if [[ -f "./target/release/ipcrawler" ]]; then
        # Check if key exists using the list command which is more reliable
        if ./target/release/ipcrawler keys list | grep -q "$selected_provider ✓"; then
            print_success "Found existing API key for $selected_provider"
            if ! ask_yes_no "Do you want to override the existing API key?" "n"; then
                print_info "Keeping existing API key for $selected_provider"
                skip_key_test=true
            else
                print_info "Please enter a new API key for $selected_provider"
                skip_key_test=false
            fi
        else
            skip_key_test=false
        fi
    else
        skip_key_test=false
    fi
    
    # Configure API key or URL
    if [ "$selected_provider" = "ollama" ]; then
        if [[ "$skip_key_test" != "true" ]]; then
            ask_input "Enter Ollama server URL" "http://localhost:11434" api_key
        fi
    else
        if [[ "$skip_key_test" != "true" ]]; then
            print_info "You'll need an API key for $selected_provider"
            echo "Get your API key from:"
            case $selected_provider in
                "groq") echo "  https://console.groq.com/keys" ;;
                "openai") echo "  https://platform.openai.com/api-keys" ;;
                "openrouter") echo "  https://openrouter.ai/keys" ;;
            esac
            echo ""
        fi
        
        # API key validation loop
        if [[ "$skip_key_test" != "true" ]]; then
        while true; do
            ask_input "Enter your API key" "" api_key
            
            # Basic API key format validation
            case $selected_provider in
                "groq")
                    if [[ ! "$api_key" =~ ^gsk_[A-Za-z0-9]+$ ]]; then
                        print_error "Invalid Groq API key format. Should start with 'gsk_'"
                        continue
                    fi
                    ;;
                "openai")
                    if [[ ! "$api_key" =~ ^sk-[A-Za-z0-9]+$ ]]; then
                        print_error "Invalid OpenAI API key format. Should start with 'sk-'"
                        continue
                    fi
                    ;;
                "openrouter")
                    if [[ ! "$api_key" =~ ^sk-or-[A-Za-z0-9-]+$ ]]; then
                        print_error "Invalid OpenRouter API key format. Should start with 'sk-or-'"
                        continue
                    fi
                    ;;
            esac
            
            # Test the API key immediately
            print_info "Testing API key..."
            if [ -f "./target/release/ipcrawler" ]; then
                local test_output
                test_output=$(./target/release/ipcrawler keys set --provider "$selected_provider" --key "$api_key" 2>&1)
                local set_exit_code=$?
                
                if [ $set_exit_code -eq 0 ]; then
                    # Now test the key
                    test_output=$(./target/release/ipcrawler keys test --provider "$selected_provider" 2>&1)
                    local test_exit_code=$?
                    
                    if [ $test_exit_code -eq 0 ]; then
                        print_success "API key is valid and working!"
                        break
                    else
                        print_error "API key test failed:"
                        echo "$test_output" | sed 's/^/   /'
                        if ask_yes_no "Would you like to try a different API key?" "y"; then
                            continue
                        else
                            print_warning "Proceeding with untested API key..."
                            break
                        fi
                    fi
                else
                    print_error "Failed to store API key:"
                    echo "$test_output" | sed 's/^/   /'
                    if ask_yes_no "Would you like to try again?" "y"; then
                        continue
                    else
                        print_warning "Skipping API key configuration..."
                        api_key=""
                        break
                    fi
                fi
            else
                print_warning "Cannot test API key - IPCrawler binary not found"
                break
            fi
        done
        else
            print_success "Using existing API key for $selected_provider"
        fi
    fi
    
    # Step 5: Test configuration
    echo ""
    print_header "Step 5: Testing Configuration"
        
    if [[ -f "./target/release/ipcrawler" ]]; then
        echo ""
        if ask_yes_no "Would you like to test IPCrawler with a basic scan?" "n"; then
            print_info "Running test scan on example.com..."
            ./target/release/ipcrawler scan --llm-provider "$selected_provider" --max-cost-per-request 0.01 example.com || {
                print_warning "Test scan failed. This might be due to missing tools or network issues."
            }
        fi
    else
        print_warning "Cannot test configuration - IPCrawler binary not found"
    fi
    
    # Step 6: Completion
    echo ""
    print_header "🎉 Setup Complete!"
    print_success "IPCrawler has been configured successfully!"
    echo ""
    print_info "Quick start commands:"
    echo "  ipcrawler scan example.com                    # Basic scan"
    echo "  ipcrawler scan --llm-provider groq 8.8.8.8   # Scan with specific provider"
    echo "  ipcrawler keys list                           # List configured API keys"
    echo "  ipcrawler --help                              # Show all options"
    echo ""
    print_info "For more information, check the documentation or run 'ipcrawler --help'"
    echo ""
    print_success "Happy reconnaissance! 🕵️"
}

# Run the wizard
main "$@"