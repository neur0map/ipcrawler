# ipcrawler

Automated penetration testing tool that executes multiple security tools in parallel with a modern terminal UI.

## Features

- **YAML-driven tool configuration** - Zero hardcoded tool logic, fully extensible
- **Parallel execution** - Runs up to 5 tools concurrently with intelligent queueing
- **Modern terminal UI** - Real-time progress tracking with colored output and live vulnerability feed
- **Auto-installation** - Detects and installs missing tools with user confirmation
- **Flexible targeting** - Supports single IPs, CIDR ranges, and file-based target lists
- **Smart port scanning** - Port lists, ranges, or common ports
- **Comprehensive reporting** - Markdown reports with tables, JSON output, and individual tool logs
- **Output parsing** - Native JSON support with regex fallback for any tool

## Installation

### Prerequisites

- Rust 1.70+ (install from [rustup.rs](https://rustup.rs))
- One of the supported package managers: apt, yum, dnf, brew, pacman, zypper

### Build from Source

```bash
git clone <repository-url>
cd ipcrawler
cargo build --release
```

The binary will be located at `target/release/ipcrawler`

## Usage

### Basic Scan

```bash
ipcrawler -t 192.168.1.1 -p 80,443
```

### CIDR Range Scan

```bash
ipcrawler -t 192.168.1.0/24 -p common
```

### File-based Targets

Create a `targets.txt` file:
```
192.168.1.1
192.168.1.10-192.168.1.20
10.0.0.0/24
```

```bash
ipcrawler -t targets.txt -p 1-1000
```

### Command Line Options

```
ipcrawler -t <TARGET> -p <PORTS> [OPTIONS]

Arguments:
  -t, --target <TARGET>        Target: IP, CIDR, or file path
  -p, --ports <PORTS>          Ports: list (22,80), range (1-1000), or "common"

Options:
  -o, --output <DIR>           Output directory (default: ./ipcrawler-results/{timestamp}/)
  --install                    Auto-install missing tools without prompting
  --tools-dir <PATH>           Path to tools directory (default: tools)
  -h, --help                   Print help
  -V, --version                Print version
```

### Port Specifications

- **Single port**: `80`
- **Port list**: `22,80,443,8080`
- **Port range**: `1-1000`
- **Common ports**: `common` (includes 21,22,23,25,53,80,110,143,443,445,3306,3389,5432,8080,8443)

## Adding Custom Tools

ipcrawler uses YAML files to define tools. Create a new YAML file in the `tools/` directory:

```yaml
name: "custom-scanner"
description: "My custom vulnerability scanner"
command: "custom-scanner -h {{target}} -p {{port}} -o {{output_file}}"
installer:
  apt: "apt install -y custom-scanner"
  brew: "brew install custom-scanner"
  pacman: "pacman -S --noconfirm custom-scanner"
timeout: 300
output:
  type: "json"
  json_flag: "-o"
  patterns:
    - name: "vulnerability_found"
      regex: "VULN: (.+)"
      severity: "high"
```

### YAML Schema

#### Required Fields

- `name` (string): Tool name
- `description` (string): Short description
- `command` (string): Command template with placeholders
- `installer` (object): Installation commands per package manager
- `output` (object): Output parsing configuration

#### Placeholders

Use these in the `command` field:
- `{{target}}` - Target IP address
- `{{port}}` - Port number (only if tool scans specific ports)
- `{{output_file}}` - Path where tool should write output

#### Output Types

- **json**: Tool outputs native JSON (use `json_flag` to specify the flag)
- **xml**: Tool outputs XML (use regex patterns to parse)
- **regex**: Plain text output parsed with regex patterns

#### Severity Levels

- `critical`
- `high`
- `medium`
- `low`
- `info`

## Output Structure

After a scan completes, results are saved to the output directory:

```
ipcrawler-results/YYYYMMDD_HHMMSS/
├── report.md           # Markdown summary report
├── results.json        # JSON formatted results
└── logs/              # Individual tool outputs
    ├── nmap_192_168_1_1_80.log
    ├── nikto_192_168_1_1_80.log
    └── ...
```

### Markdown Report Format

The `report.md` includes:
- Scan metadata (targets, ports, timestamp)
- Summary counts by severity
- Open ports list (actual port numbers, not count)
- Vulnerability tables organized by severity
- Tool execution log with status and duration

## Architecture

### Module Structure

```
src/
├── main.rs                # Entry point & orchestration
├── cli.rs                 # CLI parsing & input validation
├── config/
│   └── schema.rs          # YAML schema definitions
├── system/
│   └── detect.rs          # OS & package manager detection
├── tools/
│   ├── registry.rs        # Tool discovery & loading
│   └── installer.rs       # Tool installation
├── executor/
│   ├── queue.rs           # Task queue management
│   └── runner.rs          # Parallel task execution
├── output/
│   ├── parser.rs          # Output parsing & deduplication
│   └── reporter.rs        # Report generation
└── ui/
    └── tui.rs             # Terminal UI (ratatui)
```

### Key Design Principles

1. **Zero Hardcoded Tool Logic** - All tool behavior defined in YAML
2. **Parallel Execution** - Tokio-based async runtime with semaphore limiting (5 max concurrent)
3. **Extensibility** - Add new tools without modifying source code
4. **Type Safety** - Leverages Rust's type system for reliability

### Execution Flow

1. Parse CLI arguments and validate inputs
2. Discover and load tool definitions from YAML files
3. Check for missing tools and offer installation
4. Generate tasks (tool × target × port combinations)
5. Execute tasks in parallel (max 5 concurrent)
6. Parse outputs using tool-specific patterns
7. Deduplicate and aggregate findings
8. Generate markdown and JSON reports

## Terminal UI

The live terminal interface shows:

- **Header Panel**: Scan info, targets, ports, progress, elapsed time
- **Execution Table**: Real-time status of all tools with icons
  - `✓` Completed
  - `►` Running
  - `⋯` Queued
  - `✗` Failed
- **Findings Feed**: Live vulnerability feed with severity colors
  - Critical (Red), High (Orange), Medium (Yellow), Low (Blue), Info (Gray)

### Controls

- `↑/↓` - Scroll through findings
- `q` - Quit (after scan completes)

## Included Tools

ipcrawler ships with 5 pre-configured security tools:

1. **nmap** - Port scanner and service detection
2. **nikto** - Web server vulnerability scanner
3. **gobuster** - Directory and file bruteforcer
4. **sqlmap** - SQL injection testing
5. **sslscan** - SSL/TLS configuration scanner

## Development

### Build for Development

```bash
cargo build
```

### Run Tests

```bash
cargo test
```

### Lint & Format

```bash
cargo clippy
cargo fmt
```

### Adding a New Module

All modules must be YAML-driven and avoid hardcoded tool-specific logic. See the existing tools in `tools/` for examples.

## Troubleshooting

### Tool Not Found

If a tool isn't detected:
1. Ensure it's installed and in your PATH
2. Use `--install` flag to auto-install
3. Check the tool's YAML file has correct installer commands

### Permission Errors

Some tools require elevated privileges:
```bash
sudo ./target/release/ipcrawler -t 192.168.1.1 -p 80
```

### No Output from Tool

Check that:
1. The tool's `command` template is correct
2. Output parsing patterns match the tool's actual output
3. Review individual logs in the `logs/` directory

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Key areas:
- Additional pre-configured tools (add YAML files)
- Enhanced output parsers
- UI improvements
- Documentation

## Roadmap

- [ ] Plugin system for custom parsers
- [ ] Distributed scanning across multiple machines
- [ ] Web dashboard for result visualization
- [ ] Integration with vulnerability databases
- [ ] Custom scan profiles/templates
