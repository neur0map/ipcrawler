# IPCrawler

IP-focused reconnaissance tool for penetration testing. IPCrawler leverages external tools and advanced shell scripts to gather comprehensive IP intelligence through parallel execution.

## Features

- **Parallel Execution**: Maximizes system resources using Tokio async runtime
- **Template-Driven**: Easy configuration via TOML files for external tools
- **Minimal CLI**: Simple interface - `ipcrawler <target> [-o output] [-v]`
- **Dual Output**: Raw result files and processed markdown reports
- **Modern Terminal UI**: Clean, minimal interface with live status updates
- **Extensible**: Add new tools by creating TOML template files

## Quick Start

### Prerequisites

- Rust toolchain (for building from source)
- External tools (auto-installed with `make install-tools`):
  - nmap, rustscan, dig, whois, traceroute, shodan

### Installation

#### From Source (Cross-Platform)

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make install-tools  # Auto-detects OS and installs dependencies
make init          # Build and install system-wide
```

#### Supported Systems

The `make install-tools` command automatically detects and supports:

- **macOS**: Homebrew package manager
- **Linux**: 
  - Debian/Ubuntu (apt)
  - CentOS/RHEL (yum)
  - Fedora (dnf)
  - Arch Linux (pacman)
  - openSUSE (zypper)
- **FreeBSD**: pkg package manager
- **Windows**: Chocolatey or winget

#### Manual Installation

If automatic installation fails, install tools manually:

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install nmap dnsutils whois traceroute python3-pip pipx
cargo install rustscan
pipx install shodan  # Recommended, or:
pip3 install --user shodan  # If pipx not available
```

**macOS:**
```bash
brew install nmap bind-tools pipx
cargo install rustscan
pipx install shodan  # Recommended, or:
pip3 install --user shodan
```

**Windows:**
```bash
# Using Chocolatey
choco install nmap python3 pipx
cargo install rustscan
pipx install shodan  # Recommended, or:
pip install --user shodan

# Or using winget
winget install Insecure.Nmap
winget install Python.Python.3
winget install pipx
cargo install rustscan
pipx install shodan
```

**Note on Python Installation:**
Modern Python versions may have "externally managed environments" protection. If you encounter this error:
- Use `pipx` (recommended for CLI tools)
- Use `pip install --user <package>` for user-level installation
- Use `pip install --break-system-packages <package>` if necessary (not recommended)

#### Manual Build

```bash
cargo build --release
./target/release/ipcrawler --help
```

## Usage

### Basic Usage

```bash
# Scan single IP
ipcrawler 192.168.1.1

# Scan multiple IPs
ipcrawler 8.8.8.8 1.1.1.1

# Custom output directory
ipcrawler 10.0.0.1 --output pentest_results

# Verbose mode
ipcrawler 192.168.1.1 -v
```

### CLI Options

- `<TARGETS>`: One or more IP addresses to scan
- `-o, --output <DIR>`: Output directory (default: current directory)
- `-v, --verbose`: Show detailed command execution
- `-h, --help`: Display help information
- `-V, --version`: Show version information

## Tool Categories

IPCrawler organizes reconnaissance tools into categories:

### Discovery
- **DNS Records**: dig (ANY, reverse lookups)
- **WHOIS**: Registration and ownership information
- **Ping**: Basic connectivity testing

### Scanning
- **NMAP**: Service detection and OS fingerprinting
- **RustScan**: Fast port scanning

### Intelligence
- **Shodan**: Internet-wide device intelligence
- **VirusTotal**: Malware analysis and reputation

### Mapping
- **Traceroute**: Network path discovery

## Output Structure

```
output_directory/
├── raw/                    # Raw tool outputs
│   ├── nmap_192.168.1.1.txt
│   ├── dig_basic_192.168.1.1.txt
│   └── shodan_192.168.1.1.txt
└── reports/               # Processed markdown reports
    ├── ipcrawler_summary_20241017_143022.md
    └── ipcrawler_detailed_20241017_143022.md
```

## Report Types

### Summary Report
- Executive summary with success rates
- Tool categories and results overview
- Links to raw output files

### Detailed Report
- Complete command and output for each tool
- Execution timestamps and status
- Full tool outputs for analysis

## Template System

Add custom tools by creating TOML files in `templates/`:

```toml
[tools.custom_tool]
name = "custom_tool"
description = "Custom reconnaissance tool"
command = "tool_command"
args = ["-option", "{target}"]
output_file = "custom_{target}.txt"
category = "custom"
dependencies = ["tool_command"]
```

### Template Structure
- `templates/discovery/`: Basic information gathering
- `templates/scanning/`: Port and service scanning
- `templates/intelligence/`: OSINT and threat intelligence
- `templates/mapping/`: Network topology tools

## Development

### Build Commands

```bash
make help          # Show all commands
make build         # Build release version
make clean         # Clean build artifacts
make test          # Basic functionality test
```

### Project Structure

```
src/
├── main.rs          # Entry point and CLI parsing
├── executor.rs      # Parallel execution engine
├── template.rs      # TOML template management
├── reporter.rs      # Markdown report generation
├── output.rs        # File output management
└── cli.rs           # Command line interface

templates/
├── discovery/       # DNS, WHOIS, ping
├── scanning/        # NMAP, RustScan
├── intelligence/    # Shodan, VirusTotal
└── mapping/         # Traceroute, network tools
```

## Dependencies

- **tokio**: Async runtime for parallel execution
- **serde/toml**: Configuration parsing
- **clap**: CLI argument parsing
- **tera**: Markdown template engine
- **indicatif**: Progress indicators
- **colored**: Terminal styling

## Requirements

- **Operating Systems**: 
  - Linux (Debian, Ubuntu, CentOS, RHEL, Fedora, Arch, openSUSE)
  - macOS (with Homebrew)
  - FreeBSD
  - Windows (with Chocolatey or winget)
- **Rust**: 1.70+ (for building from source)
- **External Tools**: Automatically installed via `make install-tools` or manually:
  - nmap, rustscan, dig/dnsutils/bind-tools, whois, traceroute, shodan

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

Created by Neur0map - contact@neur0map.io

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
