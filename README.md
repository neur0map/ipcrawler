# IPCrawler

Intelligent automated penetration testing scanner with LLM-powered output parsing.

## Features

- **YAML Template System** - Easy tool configuration with automatic sudo detection
- **Async Execution** - Tokio-based concurrent tool execution
- **LLM Parsing** - AI extracts structured data without hardcoded regex patterns
- **Multiple Output Formats** - Terminal, HTML, Markdown, and JSON outputs
- **4 LLM Providers** - OpenAI, Groq, Anthropic, Ollama support
- **Secure Config** - Store API keys safely with file permissions

## Installation

```bash
cargo build --release
```

## Quick Start

```bash
# 1. Configure (one-time setup)
./target/release/ipcrawler setup

# 2. Run scan
./target/release/ipcrawler 192.168.1.1 -o ./scan

# 3. View results
#    - Terminal output appears immediately
#    - Open ./scan/report.html in browser
#    - Read ./scan/report.md for documentation
```

## Configuration

### Interactive Setup

```bash
ipcrawler setup
```

Guides you through:
- LLM provider selection (Groq, OpenAI, Anthropic, Ollama)
- API key configuration
- Default settings (templates directory, verbose mode)

Config stored at: `~/.config/ipcrawler/config.toml` with secure permissions (0600)

### View Current Config

```bash
ipcrawler config
```

Shows current settings with masked API key.

### Config File Format

```toml
[llm]
provider = "groq"
api_key = "gsk_..."

[defaults]
templates_dir = "templates"
verbose = false
```

### Override Config

```bash
# Override provider
ipcrawler <target> -o ./scan --llm-provider openai

# Override via environment variable
export LLM_API_KEY="different-key"
ipcrawler <target> -o ./scan
```

## Usage

### Basic Scan

```bash
ipcrawler <target> -o <output_dir>
```

### List Available Templates

```bash
ipcrawler list
```

### Show Template Details

```bash
ipcrawler show nmap
```

### With Sudo (Enhanced Scans)

```bash
sudo ipcrawler <target> -o <output_dir>
```

Automatically uses privileged templates (e.g., nmap-sudo instead of nmap).

### Skip LLM Parsing

```bash
ipcrawler <target> -o <output_dir> --no-parse
```

## Supported LLM Providers

All configured via `ipcrawler setup`:

- **Groq** (Recommended) - Fast, free tier - https://console.groq.com
- **OpenAI** - Reliable - https://platform.openai.com
- **Anthropic** - High quality - https://console.anthropic.com  
- **Ollama** - Local, free - https://ollama.ai

## Output Structure

```
scan_output/
├── raw/                  # Raw tool outputs
│   ├── nmap/
│   ├── nikto/
│   └── ...
├── entities.json         # Extracted data (JSON)
├── report.json           # Full report (JSON)
├── report.html           # HTML report (open in browser)
└── report.md             # Markdown report (for docs)
```

### Output Formats

1. **Terminal** - Immediate colored output
2. **HTML** - Professional web report
3. **Markdown** - Documentation-friendly format
4. **JSON** - Machine-readable for automation

## Template System

Templates are YAML files in `templates/` directory:

```yaml
name: nmap
description: Fast port scan
enabled: true

command:
  binary: nmap
  args:
    - "-sT"
    - "-T4"
    - "--top-ports"
    - "1000"
    - "{{target}}"

timeout: 600
requires_sudo: false
```

### Variables

- `{{target}}` - Scan target
- `{{output_dir}}` - Output directory

### Sudo Detection

Create two variants:
- `tool.yaml` - Regular scan
- `tool-sudo.yaml` - Privileged scan

IPCrawler automatically selects the appropriate version based on privileges.

### Included Templates

- `ping.yaml` - Connectivity check
- `nmap.yaml` - TCP port scan (top 1000)
- `nmap-sudo.yaml` - SYN scan with OS detection (requires root)
- `nikto.yaml` - Web vulnerability scanner
- `whatweb.yaml` - Web technology fingerprinting
- `gobuster.yaml` - Directory brute-forcing (disabled by default)

## How the AI Works

### Data Flow

```
1. Tools execute → Raw text output
2. AI extracts data → Structured JSON
3. Display module → Human-readable formats
```

### AI's Role

The AI only does text-to-JSON conversion:

```
Input:  "PORT     STATE SERVICE VERSION\n22/tcp   open  ssh     OpenSSH 8.2"
Output: {"ports": [{"port": 22, "service": "ssh", "version": "OpenSSH 8.2"}]}
```

**What AI does NOT do:**
- Execute commands
- Make security decisions
- Analyze vulnerabilities
- Provide recommendations

**Why no regex:**
- AI adapts to different output formats
- Works with any tool without custom parsers
- No maintenance when tools update

### System Prompt

The AI uses a focused prompt to prevent over-engineering:

```
You are a penetration testing output parser.
Your ONLY job is to extract data from tool outputs.

CRITICAL RULES:
1. DO NOT analyze, interpret, or add commentary
2. DO NOT suggest fixes or recommendations  
3. DO NOT explain vulnerabilities
4. ONLY extract what is explicitly present
5. Return ONLY valid JSON
```

## Security

- Config file stored with 0600 permissions (owner read/write only)
- API keys masked when viewing config
- No keys stored in environment after setup
- Config location: `~/.config/ipcrawler/config.toml`

## Architecture

```
src/
├── main.rs              # Entry point
├── cli.rs               # CLI parsing
├── config/              # Configuration system
│   ├── mod.rs           # Config loading/saving
│   └── setup.rs         # Interactive setup wizard
├── display/             # Output formatting
│   ├── terminal.rs      # Console output
│   ├── html.rs          # HTML reports
│   └── markdown.rs      # Markdown reports
├── parser/              # AI integration
│   ├── llm.rs           # LLM API calls (4 providers)
│   └── extractor.rs     # Entity extraction
├── templates/           # YAML system
│   ├── parser.rs        # YAML loader
│   ├── selector.rs      # Sudo detection
│   └── executor.rs      # Async execution
└── storage/             # Output management
    ├── output.rs        # File operations
    └── report.rs        # Report generation
```

## Development

### Code Quality

This project uses automated GitHub Actions workflows to maintain code quality:

**Workflow: Rust Quality Checks** (`.github/workflows/rust-quality.yml`)

Runs on every push and pull request to `main`/`master` branches:

1. **Format Check** - Runs `cargo fmt --check`
   - Automatically fixes formatting issues on push events
   - Commits fixes as: "Auto-fix: Apply cargo fmt"

2. **Clippy Check** - Runs `cargo clippy -- -D warnings`
   - Automatically fixes clippy warnings on push events
   - Commits fixes as: "Auto-fix: Apply clippy suggestions"

3. **Build & Test** - Runs after format and clippy checks
   - Verifies the code builds successfully
   - Runs all tests

**Manual Commands:**

```bash
# Build
cargo build

# Run with debug logging
cargo run -- <target> -o ./scan -v

# Check formatting
cargo fmt --check

# Apply formatting
cargo fmt

# Run clippy
cargo clippy -- -D warnings

# Auto-fix clippy issues
cargo clippy --fix

# Run tests
cargo test
```

## Example Output

```
============================================================
Scan Results for example.com
============================================================

[IP Addresses]
------------------------------------------------------------
  1. 93.184.216.34

[Open Ports]
------------------------------------------------------------
  80 (tcp)  http nginx
  443 (tcp)  ssl/http nginx

[No vulnerabilities detected]

============================================================
[Scan Summary]
============================================================

  Target: example.com
  Duration: 23s
  Tools: 4/4

  Discovered:
    - 1 IPs
    - 2 Domains
    - 2 URLs
    - 2 Open Ports
    - 0 Vulnerabilities

[Scan completed successfully]

Output Files:
  - ./scan/entities.json
  - ./scan/report.json
  - ./scan/report.html
  - ./scan/report.md
  - ./scan/raw/
```

## License

MIT

## Troubleshooting

### Setup Command Issues

If `ipcrawler setup` shows a TTY warning:

```bash
# Use the release binary directly (recommended)
./target/release/ipcrawler setup

# Or force interactive mode
FORCE_INTERACTIVE=1 ipcrawler setup

# Or build first then run
cargo build --release
./target/release/ipcrawler setup
```

**Note:** Running through `cargo run` may not have proper TTY access. Build the release binary first for best results.

### Common Issues

**Q: "No TTY detected" warning during setup**  
A: This is normal when running through cargo. Use the release binary directly or set `FORCE_INTERACTIVE=1`.

**Q: Setup prompts don't work**  
A: Ensure you're running in an actual terminal, not through pipes or CI. Build the release binary and run it directly.

**Q: Auto-generated output directories**  
A: Output path is optional. Without `-o`, creates `./ipcrawler_<target>_<timestamp>` automatically.
