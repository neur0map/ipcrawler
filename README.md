# ipcrawler 🕷️

A modern Rust-based auto-reconnaissance tool with RAG (Retrieval-Augmented Generation) for intelligent querying of scan results.

## Features

- >> **Fast & Async** - Built with Tokio for concurrent execution
- [INFO] **YAML Templates** - Easy-to-configure tool definitions
- 🔗 **Dependency Resolution** - Automatic ordering of scans
- [WATCHING] **Real-time Indexing** - Watches output directory and indexes files as they're created
- 🤖 **AI-Powered Queries** - Ask questions about your scan results in natural language
- 🛠️ **Extensible** - Add custom tools via YAML templates

## Installation

### Prerequisites

- Rust 1.70+ (install from [rustup.rs](https://rustup.rs))
- Reconnaissance tools you want to use (nmap, gobuster, etc.)

### Build from Source

```bash
git clone https://github.com/neur0map/ipcrawler
cd ipcrawler
cargo build --release
```

The binary will be at `target/release/ipcrawler`.

## Quick Start

### First Time Setup

```bash
# Run the interactive setup wizard (RECOMMENDED)
ipcrawler setup
```

The setup wizard will:
- [SEARCH] Detect available AI services (Ollama, Qdrant)
- [SUMMARY] Help you choose between local (free) or cloud models
- [DOWNLOAD] Install and configure models automatically
- [SAVE] Save your configuration

**Setup options:**
- **Local (Ollama):** 100% free, private, no API keys needed (local)
- **Cloud (OpenAI):** Fast setup, requires API key (cloud)

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

### Basic Usage

```bash
# Run reconnaissance on a target
ipcrawler run -t 192.168.1.100 -o ./results --templates-dir ./templates

# Query your results with AI
ipcrawler ask "what ports are open?" -o ./results

# List available templates
ipcrawler templates list --templates-dir ./templates

# Show template details
ipcrawler templates show nmap --templates-dir ./templates
```

### With Custom Templates

```bash
ipcrawler run -t example.com -o ./scan --templates ./my-templates
```

## Templates

Templates are YAML files that define how to run reconnaissance tools. Each template specifies:

- Command and arguments
- Dependencies on other templates
- Output patterns
- Timeouts
- Environment variables

### Example Template

```yaml
name: nmap
description: Network port scanner
enabled: true

command:
  binary: nmap
  args:
    - "-sV"
    - "-p-"
    - "-oA"
    - "{{output_dir}}/nmap/{{target}}"
    - "{{target}}"

depends_on: []
outputs:
  - pattern: "{{output_dir}}/nmap/*.xml"
timeout: 3600
env: {}
```

### Built-in Templates

- **nmap** - Full port scan with service detection
- **nmap-quick** - Quick scan of top 1000 ports
- **ping** - Basic connectivity test
- **naabu** - Fast port scanner (requires naabu)
- **gobuster** - Web directory brute-forcer (requires gobuster)
- **nikto** - Web vulnerability scanner (requires nikto)
- **whatweb** - Web technology identifier (requires whatweb)

## RAG Integration

ipcrawler uses [Swiftide](https://swiftide.rs) for intelligent indexing and querying.

### Setup for Full RAG

1. **Install Qdrant** (vector database):
```bash
docker run -p 6333:6333 qdrant/qdrant
```

2. **Set OpenAI API Key**:
```bash
export OPENAI_API_KEY="your-api-key"
```

3. **Run reconnaissance** - files are automatically indexed as they're created

4. **Query with natural language**:
```bash
ipcrawler ask "how many web services were found?"
ipcrawler ask "what paths returned 200 status code?"
ipcrawler ask "are there any interesting findings?"
```

### Fallback Mode

Without RAG setup, ipcrawler uses basic text search to answer queries.

## Commands

### `run` - Execute Reconnaissance

```bash
ipcrawler run [OPTIONS] -t <TARGET> -o <OUTPUT>

Options:
  -t, --target <TARGET>              Target IP or hostname
  -o, --output <OUTPUT>              Output directory [default: ./output]
      --templates-dir <DIR>          Custom templates directory
  -v, --verbose                      Enable verbose logging
```

### `ask` - Query Results

```bash
ipcrawler ask [OPTIONS] <QUESTION>

Options:
  -o, --output <OUTPUT>              Output directory [default: ./output]
  -k, --top-k <NUM>                  Number of top results [default: 5]

Example:
  ipcrawler ask "what services are running on port 80?"
```

### `templates` - Manage Templates

```bash
# List all templates
ipcrawler templates list

# Show template details
ipcrawler templates show <NAME>

Options:
      --templates-dir <DIR>          Custom templates directory
```

## Architecture

```
ipcrawler/
├── src/
│   ├── main.rs           # Entry point
│   ├── cli.rs            # CLI definitions
│   ├── templates/        # Template parsing & execution
│   ├── watcher/          # File system monitoring
│   ├── indexer/          # Swiftide RAG indexing
│   └── query/            # Natural language queries
└── templates/            # YAML tool definitions
```

## Environment Variables

- `OPENAI_API_KEY` - OpenAI API key for RAG queries
- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)

## Development

### Build

```bash
cargo build
```

### Run Tests

```bash
cargo test
```

### Format & Lint

```bash
cargo fmt
cargo clippy
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add your changes with tests
4. Submit a pull request

### Adding Templates

To contribute a new template:

1. Create a YAML file in `templates/`
2. Follow the template structure
3. Test with your local setup
4. Submit a PR with documentation

## License

MIT License - see LICENSE file

## Credits

- Inspired by [AutoRecon](https://github.com/Tib3rius/AutoRecon)
- Built with [Swiftide](https://swiftide.rs)
- Created by [neur0map](https://github.com/neur0map)

## Roadmap

- [ ] Web UI for visualization
- [ ] Template marketplace
- [ ] Multi-target support
- [ ] Parallel execution where possible
- [ ] Custom plugins via WASM
- [ ] Report generation (PDF, HTML, JSON)
- [ ] Integration with OWASP tools
- [ ] Cloud storage backends

## Troubleshooting

### Templates not found
Ensure templates are in `./templates/` or specify with `--templates-dir`.

### Tool not found errors
Install the required tools (nmap, gobuster, etc.) on your system.

### RAG queries not working
1. Check Qdrant is running: `curl http://localhost:6333`
2. Verify OPENAI_API_KEY is set: `echo $OPENAI_API_KEY`
3. Re-run reconnaissance to index data

### Permission denied
Some tools (like nmap) may require sudo privileges for certain scans.

## Support

- GitHub Issues: [Report bugs](https://github.com/neur0map/ipcrawler/issues)
- Documentation: [Wiki](https://github.com/neur0map/ipcrawler/wiki)

---

**Note**: ipcrawler is for authorized security testing only. Always obtain proper authorization before scanning systems you don't own.
