<div align="center">

# IPCrawler

High-performance reconnaissance framework for security professionals. Delivers comprehensive network intelligence through parallel tool execution using Shell/Yaml templates and optional LLM-enhanced reports.

[![prowl.sh](https://img.shields.io/badge/prowl-sh-blue)](https://prowl.sh)

</div>

---

## Quick Start

Refer to the documentation for detailed usage examples, including basic scans, network range scans, and advanced options.

## Core Features

**Performance & Features**
- Parallel execution of up to 10 tools
- Automatic tool discovery from YAML configurations
- Smart timeout and retry handling
- Privilege escalation detection

**Output**
- Structured JSON findings
- Markdown reports grouped by severity
- Complete raw logs preserved
- Optional LLM-enhanced analysis

**Extensibility**
- YAML-driven tool configuration
- Support for custom shell scripts
- No hardcoded tool logic
- Built-in script security validation

## Installation

### Build from Source

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
make build     # this will make a symlink
```

**Requirements:**
- Rust 1.70+ ([rustup.rs](https://rustup.rs))
- Go latest version- [Go Programming Language](https://go.dev)
- Python latest version- [Python Programming Language](https://www.python.org)

## Included Tools

| **Category**          | **Tool Name**         | **Description**                                    |
|-----------------------|-----------------------|---------------------------------------------------|
| **Network Scanning**  | `nmap_comprehensive` | Multi-phase port scanning with service detection  |
|                       | `traceroute`         | Network path analysis                              |
| **HTTP Analysis**     | `httpx_enumeration`  | Security headers, TLS certs, technology detection |
| **DNS Reconnaissance**| `dig`                | 17 DNS record types, subdomain enum, zone transfers|
| **Information Gathering** | `whois`          | Domain registration and ownership                 |

See [Tool Documentation](docs/TOOLS.md) for complete details.

## Documentation

- **[Configuration Guide](docs/CONFIGURATION.md)** - Custom tools, JSON format, wordlists
- **[Tool Reference](docs/TOOLS.md)** - Complete tool specifications
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow
- **[Security](docs/SECURITY.md)** - Script validation and sudo usage
- **[Development](docs/DEVELOPMENT.md)** - Contributing and building


## Legal Notice

**For authorized security testing only:**
- Penetration testing with permission
- Security research and CTF competitions
- Defensive security operations
- Educational purposes

**Do not use for unauthorized scanning.**

## License

Apache License 2.0 - See [LICENSE](LICENSE) file.

---

<div align="center">

**IPCrawler** is part of the [prowl.sh](https://prowl.sh) security tools ecosystem

Maintained by [neur0map](mailto:neur0map@prowl.sh)

</div>
