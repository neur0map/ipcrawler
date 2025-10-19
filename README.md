# IPCrawler

IP-focused reconnaissance tool with LLM-powered output parsing for penetration testing.

## Features

- **LLM-Powered Parsing**: Uses cloud LLMs to parse tool outputs into structured JSON without hardcoded regex
- **Multi-Provider Support**: OpenAI, Groq, OpenRouter, and Ollama support with automatic fallback
- **Cost Optimization**: Smart token usage, caching, and cost tracking
- **Tool Agnostic**: Add any tool without writing parsing code
- **Modern CLI**: Clean, intuitive command-line interface
- **Cross-Platform**: Works on Linux, macOS, and Windows
- **Secure Key Storage**: Encrypted API key management
- **Comprehensive Reporting**: JSON and Markdown reports

## Quick Start

### 🚀 Smart Setup (Recommended)

The easiest way to get started is with our interactive setup wizard:

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make init
```

The setup wizard will:
- ✅ Build the project automatically
- ✅ Install required system tools (nmap, dig, etc.)
- ✅ Set up system-wide access
- ✅ Configure LLM providers interactively
- ✅ Test your configuration

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler

# Build the project
make build

# Install system dependencies
make install-deps
```

### Configure API Keys

```bash
# Set your preferred LLM provider
./target/release/ipcrawler keys set --provider groq --key your_groq_api_key

# Or use OpenAI
./target/release/ipcrawler keys set --provider openai --key your_openai_api_key

# List configured providers
./target/release/ipcrawler keys list

# Test API key
./target/release/ipcrawler keys test --provider groq
```

> 💡 **Tip**: Use `make init` for guided API key setup with automatic testing

### Basic Usage

```bash
# Scan default top 1000 ports
ipcrawler example.com

# Scan custom port range
ipcrawler example.com -p 22-3000

# Scan multiple targets
ipcrawler example.com 192.168.1.1 -p 80,443,8080

# Verbose output
ipcrawler example.com -v

# Custom output directory
ipcrawler example.com -o /path/to/output
```

## LLM Providers

### Groq (Recommended)
- Fast and cost-effective
- Models: Llama 3.1 8B/70B
- Cost: ~$0.00005 per 1K tokens

```bash
ipcrawler keys set --provider groq --key gsk_your_key
```

### OpenRouter
- Multiple model options
- Free tier available
- Models: Llama 3.1, Mixtral, etc.

```bash
ipcrawler keys set --provider openrouter --key sk-or-your_key
```

### OpenAI
- High quality parsing
- Models: GPT-4o mini, GPT-4o
- Cost: ~$0.00015 per 1K tokens

```bash
ipcrawler keys set --provider openai --key sk-your_key
```

### Ollama (Local)
- Free local hosting
- Models: Llama 3.1, CodeLlama
- Requires Ollama installation

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.1:8b

# Use with IPCrawler
ipcrawler example.com --llm-provider ollama
```

## Supported Tools

### Port Scanning
- **nmap**: Comprehensive port scanning
- **rustscan**: Fast port scanning
- **masscan**: Very fast port scanning

### DNS Discovery
- **dig**: DNS record enumeration
- **nslookup**: Basic DNS queries
- **whois**: Domain information

### Network Mapping
- **traceroute**: Network path tracing
- **ping**: Connectivity testing

### SSL/TLS
- **sslscan**: SSL/TLS scanning
- **openssl**: SSL certificate analysis

## Templates

IPCrawler uses TOML templates to define tool execution:

```toml
[tools.nmap_default]
name = "nmap_default"
description = "Scan top 1000 ports with service detection"
command = "nmap"
args = [
    "-sV",
    "-O", 
    "--top-ports 1000",
    "-oN", "-",
    "-oX", "-",
    "{target}"
]
category = "scanning"
dependencies = ["nmap"]
parse_strategy = "llm"
output_format = "json"
```

## Output Reports

### JSON Report
Structured data for programmatic use:

```json
{
  "scan_info": {
    "start_time": "2023-01-01T12:00:00Z",
    "duration_seconds": 120,
    "total_targets": 1,
    "tools_used": ["nmap", "dig"]
  },
  "targets": [...],
  "findings": [...]
}
```

### Markdown Report
Human-readable report with:
- Executive summary
- Target details
- Open ports and services
- DNS records
- Detailed findings
- Recommendations

## Cost Management

### Default Limits
- $0.01 per request
- $1.00 daily limit
- $30.00 monthly limit

### Cost Tracking
```bash
# View usage statistics
ipcrawler --show-stats

# Reset daily usage
ipcrawler --reset-stats
```

### Optimization Features
- Output preprocessing to reduce tokens
- Intelligent caching
- Provider cost comparison
- Token usage estimation

## Configuration

Configuration files in `config/`:

- `default.toml`: General settings
- `providers.toml`: LLM provider configurations

### Example Configuration

```toml
[llm]
default_provider = "groq"
max_cost_per_request = 0.01
daily_limit = 1.0

[execution]
max_concurrent = 10
default_timeout_seconds = 300
```

## Development

### Makefile Commands

Our smart Makefile provides convenient commands for development and deployment:

```bash
# Setup & Building
make init              # Interactive setup wizard (recommended for first-time users)
make build             # Build optimized release binary
make clean             # Clean build artifacts
make dev-build         # Build in development mode
make dev-run ARGS="scan example.com"  # Build and run with arguments

# Dependencies
make install-deps      # Install system dependencies automatically
make check-deps        # Check if dependencies are installed

# Code Quality
make test              # Run tests
make lint              # Run linting with clippy
make format            # Format code with rustfmt
make audit             # Check for security vulnerabilities

# Installation
make install           # Install to system (requires sudo)
make uninstall         # Remove from system
make setup-symlink     # Create symlink for system-wide access

# Utilities
make help              # Show available commands
make update            # Update Rust dependencies
make docs              # Generate and open documentation
make package           # Create release package
```

### Manual Building
```bash
cargo build --release
```

### Testing
```bash
make test  # or: cargo test
```

### Adding New Tools

1. Create a TOML template in `templates/`
2. Define command, arguments, and dependencies
3. No parsing code required - LLM handles output

Example template:
```toml
[tools.custom_tool]
name = "custom_tool"
description = "Custom reconnaissance tool"
command = "mytool"
args = ["{target}", "--format", "json"]
category = "custom"
dependencies = ["mytool"]
parse_strategy = "llm"
output_format = "json"
```

## Security

- API keys stored encrypted locally
- No data sent to LLMs except tool output
- Cost limits prevent unexpected charges
- Local Ollama option for sensitive data

## Requirements

- Rust 1.70+
- One or more reconnaissance tools (nmap, dig, etc.)
- API key for chosen LLM provider (or Ollama)

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

- Issues: [GitHub Issues](https://github.com/neur0map/ipcrawler/issues)
- Documentation: [Wiki](https://github.com/neur0map/ipcrawler/wiki)

---

**IPCrawler** - Intelligent reconnaissance powered by LLMs.