<div align="center">

# IPCrawler

**AI-powered penetration testing scanner with concurrent execution**

[![Version](https://img.shields.io/github/v/release/neur0map/ipcrawler?style=for-the-badge&logo=github)](https://github.com/neur0map/ipcrawler/releases)
[![License](https://img.shields.io/github/license/neur0map/ipcrawler?style=for-the-badge)](https://github.com/neur0map/ipcrawler/blob/main/LICENSE)
[![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-blue?style=for-the-badge)](https://github.com/neur0map/ipcrawler)

Runs security tools concurrently, uses LLMs to parse outputs into structured JSON, and generates comprehensive reports—all through simple YAML templates.

![Stars](https://img.shields.io/github/stars/neur0map/ipcrawler?style=social)
![Forks](https://img.shields.io/github/forks/neur0map/ipcrawler?style=social)

</div>
</parameter>


```bash
ipcrawler 192.168.1.1
```

## Features

- **AI-Powered Parsing** - Converts any tool output to structured JSON (OpenAI, Groq, Anthropic, Ollama)
- **Concurrent Execution** - Tokio-based async with automatic pre-scan and dependency handling
- **Template System** - Add tools via YAML without code changes
- **Multiple Formats** - Terminal, HTML, Markdown, and JSON reports
- **Smart Consistency** - Multi-pass parsing with union merge strategy

> [!NOTE]
> LLMs are used solely to parse raw tool outputs into structured data. They do not provide security analysis, opinions, or recommendations—only data transformation from unstructured to structured format.

## Installation

```bash
# Quick install
curl -fsSL https://raw.githubusercontent.com/neur0map/ipcrawler/main/install.sh | bash

# Build from source
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
cargo build --release
sudo mv target/release/ipcrawler /usr/local/bin/
```

## Quick Start

```bash
# 1. Configure LLM provider (one-time)
ipcrawler setup

# 2. Run scan
ipcrawler example.com -o ./scan

# 3. View results
open ./scan/report.html
```

## Usage

```bash
# Basic scan
ipcrawler <target> -o <output_dir>

# Specific ports
ipcrawler <target> -p 22,80,443 -o <output>

# Custom wordlist
ipcrawler <target> -w big -o <output>

# With sudo (privileged templates)
sudo ipcrawler <target> -o <output>

# List available templates
ipcrawler list
```

## Configuration

Get an API key from [Groq](https://console.groq.com) (recommended), [OpenAI](https://platform.openai.com), [Anthropic](https://console.anthropic.com), or install [Ollama](https://ollama.ai) for local models.

```bash
# Interactive setup
ipcrawler setup

# Or set environment variables
export LLM_PROVIDER="groq"
export LLM_API_KEY="your-key"
```

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Detailed commands, options, and examples
- **[Configuration](docs/CONFIGURATION.md)** - LLM setup and advanced configuration
- **[Template Guide](templates/README.md)** - Creating custom tool templates
- **[Development](docs/DEVELOPMENT.md)** - Building and contributing
- **[Architecture](docs/ARCHITECTURE.md)** - System design and internals
- **[Contributing](CONTRIBUTING.md)** - Contribution guidelines

## License

MIT License - see [LICENSE](LICENSE) for details

---

**Built with Rust • Powered by AI**
