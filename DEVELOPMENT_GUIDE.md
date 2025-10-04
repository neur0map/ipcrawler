# ipcrawler Development Guide

Complete reference for setup, development, and usage of the ipcrawler reconnaissance automation tool.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Setup & Installation](#setup--installation)
4. [Configuration](#configuration)
5. [Templates](#templates)
6. [RAG Pipeline](#rag-pipeline)
7. [Database Organization](#database-organization)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)

---

## Quick Start

### Install and Run

```bash
# Build release binary
cargo build --release

# Run setup wizard
./target/release/ipcrawler setup

# Execute first scan
ipcrawler run -t 192.168.1.1 -o ./scan --templates-dir ./templates

# Query results
ipcrawler ask "what services were found?" -o ./scan
```

### Prerequisites

- Rust 1.70+
- Docker (for Qdrant vector database)
- Reconnaissance tools: nmap, gobuster, nikto (optional)
- OpenAI API key or Ollama (for AI features)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ipcrawler (Rust App)                     │
├─────────────────────────────────────────────────────────────┤
│  1. INDEXING PIPELINE                                       │
│     File Watcher → Load Content → Chunk Text               │
│     → Create Embeddings → Store in Qdrant                   │
│                                                             │
│  2. QUERY PIPELINE                                          │
│     User Question → Embed Question → Vector Search          │
│     → Retrieve Context → LLM Completion → Answer            │
└─────────────────────────────────────────────────────────────┘
                          ↕ HTTP API
┌─────────────────────────────────────────────────────────────┐
│         Qdrant (Docker Container)                           │
│  • Stores vectors (embeddings)                              │
│  • Performs similarity search                               │
└─────────────────────────────────────────────────────────────┘
                          ↕ API calls
┌─────────────────────────────────────────────────────────────┐
│         OpenAI API / Ollama (Local LLM)                     │
│  • Creates embeddings from text                             │
│  • Generates AI responses                                   │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure

```
src/
├── indexer/          # Real-time file indexing with Swiftide
├── query/            # RAG query engine
├── setup/            # Interactive setup wizard
│   ├── config.rs     # Configuration management
│   ├── models.rs     # Model detection
│   └── wizard.rs     # Interactive prompts
├── template/         # Template system
└── watcher/          # File watching
```

---

## Setup & Installation

### Option 1: Local Setup (Ollama - Recommended)

**Pros:** Free, private, offline-capable
**Cons:** Requires ~8GB RAM, disk space

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3.1          # 4.7 GB - LLM
ollama pull nomic-embed-text  # 274 MB - Embeddings

# Start Qdrant
docker run -d -p 6333:6333 --name ipcrawler-qdrant qdrant/qdrant

# Run setup wizard
ipcrawler setup
# Select: Ollama → llama3.1 → nomic-embed-text → Confirm Qdrant
```

### Option 2: Cloud Setup (OpenAI)

**Pros:** Easy setup, best quality
**Cons:** Costs money, data sent to OpenAI

```bash
# Get API key from https://platform.openai.com/api-keys

# Start Qdrant (optional)
docker run -d -p 6333:6333 qdrant/qdrant

# Run setup wizard
ipcrawler setup
# Select: OpenAI → Enter API key → gpt-4o → text-embedding-3-small
```

### Recommended Models

| Model | Provider | Size | Use Case |
|-------|----------|------|----------|
| llama3.1 | Ollama | 4.7GB | General use ⭐ |
| gpt-4o | OpenAI | Cloud | Best quality ⭐ |
| nomic-embed-text | Ollama | 274MB | Local embeddings ⭐ |
| text-embedding-3-small | OpenAI | Cloud | Cloud embeddings ⭐ |

---

## Configuration

### Config File Locations

- **macOS/Linux:** `~/.config/ipcrawler/config.yaml`
- **Windows:** `%APPDATA%\ipcrawler\config.yaml`

### Config Structure

```yaml
llm:
  provider: ollama          # or 'openai'
  model: llama3.1          # or 'gpt-4o'
  api_base: http://localhost:11434  # Ollama only

embeddings:
  provider: ollama          # or 'openai'
  model: nomic-embed-text  # or 'text-embedding-3-small'

vector_db:
  provider: qdrant
  url: http://localhost:6333
  collection: pentest_data
```

### API Key Security

API keys are stored in **system keychain** (encrypted):

**Setup via wizard:**
```bash
ipcrawler setup  # Enter API key once
```

**Or via environment variable:**
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Keychain locations:**
- macOS: Keychain Access app
- Linux: GNOME Keyring / KWallet
- Windows: Credential Manager

---

## Templates

### Template Structure

```yaml
name: nmap-simple
description: Basic port scan
enabled: true

command:
  binary: nmap
  args:
    - "-sT"              # TCP connect (no sudo)
    - "-p"
    - "22,80,443"
    - "{{target}}"
    - "-oN"
    - "{{output_dir}}/nmap-simple/scan.txt"

depends_on: []

outputs:
  - pattern: "{{output_dir}}/nmap-simple/*.txt"

timeout: 300

env: {}
```

### Available Variables

- `{{target}}` - Target IP/domain from CLI
- `{{output_dir}}` - Output directory from CLI
- `{{template_name}}` - Current template name

### Creating Custom Templates

```bash
# Create new template
cat > templates/my-tool.yaml << 'EOF'
name: my-tool
description: Custom reconnaissance tool
enabled: true
command:
  binary: mytool
  args:
    - "{{target}}"
    - "-o"
    - "{{output_dir}}/my-tool/results.txt"
depends_on: []
outputs:
  - pattern: "{{output_dir}}/my-tool/*.txt"
timeout: 600
EOF

# Use it
ipcrawler run -t 192.168.1.1 -o ./scan --templates-dir ./templates
```

---

## RAG Pipeline

### How It Works

**Indexing (Automatic):**
```
Scan runs → Files created → Watcher detects
→ Load file → Chunk text → Create embeddings
→ Store in Qdrant → Ready for queries
```

**Querying:**
```
User question → Embed question → Vector search
→ Retrieve top-k chunks → Build prompt
→ LLM completion → Formatted answer
```

### Implementation Details

**Embedding Model:** text-embedding-3-small (1536 dims)
**Vector Storage:** Qdrant collections
**LLM:** gpt-4o-mini or llama3.1
**Chunking:** Swiftide automatic chunking

### Usage Examples

```bash
# Run scan (auto-indexes)
ipcrawler run -t 192.168.1.1 -o ./scan --templates-dir ./templates

# Ask questions
ipcrawler ask "what ports are open?" -o ./scan
ipcrawler ask "summarize findings" -o ./scan
ipcrawler ask "any vulnerabilities?" -o ./scan
```

### Cost Estimation (OpenAI)

**Typical pentest:**
- 100 files indexed: ~$0.003
- 50 queries: ~$0.03
- **Total: ~$0.03 (3 cents)**

Extremely affordable for reconnaissance use cases.

---

## Database Organization

### Per-Target Collections

Each target gets its own Qdrant collection:

```
Qdrant Database:
├── ipcrawler_192_168_1_1      (Target: 192.168.1.1)
├── ipcrawler_10_0_0_50        (Target: 10.0.0.50)
└── ipcrawler_example_com      (Target: example.com)
```

**Benefits:**
- Perfect separation between targets
- Easy cleanup per target
- No cross-contamination in queries
- Scalable to hundreds of targets

### Collection Naming

**Pattern:** `ipcrawler_{sanitized_target}`

**Examples:**
```
192.168.1.1  →  ipcrawler_192_168_1_1
example.com  →  ipcrawler_example_com
server:8080  →  ipcrawler_server_8080
```

### Managing Collections

```bash
# List all collections
ipcrawler clean

# Clean specific target
ipcrawler clean --target 192.168.1.1

# Clean all (requires confirmation)
ipcrawler clean --all
```

---

## Testing

### Manual Testing

```bash
# 1. Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# 2. Set API key
export OPENAI_API_KEY="sk-..."

# 3. Create test data
mkdir -p ./test-scan
echo "Port 22 open - SSH
Port 80 open - HTTP
Found directory: /admin" > ./test-scan/results.txt

# 4. Index
ipcrawler run -t 127.0.0.1 -o ./test-scan --templates-dir ./templates

# 5. Query
ipcrawler ask "what ports are open?" -o ./test-scan
```

### Verification

```bash
# Check Qdrant has data
curl http://localhost:6333/collections/ipcrawler_127_0_0_1 | jq

# Should show vectors_count > 0
```

### Test Results

**Status:** Production ready ✅
- Template execution: Working
- File watching: Working
- Indexing pipeline: Working
- Vector storage: Working
- RAG queries: Working
- Fallback search: Working

---

## Troubleshooting

### Docker Issues

**Problem:** Docker daemon not running

**Solution:**
```bash
# Start Docker Desktop (macOS)
open -a Docker

# Verify
docker info
```

### Qdrant Connection Failed

**Problem:** Can't connect to Qdrant

**Solution:**
```bash
# Check if running
docker ps | grep qdrant

# Start container
docker start ipcrawler-qdrant

# Or create new one
docker run -d -p 6333:6333 --name ipcrawler-qdrant qdrant/qdrant
```

### API Key Issues

**Problem:** "Failed to call OpenAI API"

**Solution:**
```bash
# Check API key
echo $OPENAI_API_KEY

# Or check config
cat ~/.config/ipcrawler/config.yaml

# Set correct key
export OPENAI_API_KEY="sk-your-real-key"

# Or use setup wizard
ipcrawler setup
```

### Permission Denied on Config

**Problem:** Can't write config file

**Solution:**
```bash
# Fix ownership (macOS)
sudo chown -R $USER:staff "$HOME/Library/Application Support/ipcrawler"

# Fix permissions (Linux)
mkdir -p ~/.config/ipcrawler
chmod 755 ~/.config/ipcrawler
```

### No Embeddings Created

**Problem:** Files indexed but no vectors in Qdrant

**Check:**
1. API key set? `echo $OPENAI_API_KEY`
2. Qdrant running? `curl http://localhost:6333`
3. Check logs for errors

### Template Execution Failed

**Problem:** Tool not found or permission denied

**Solutions:**
```bash
# Install missing tools
brew install nmap gobuster nikto  # macOS
sudo apt install nmap gobuster nikto  # Linux

# For sudo-required tools, use as root or modify templates
# Change: enabled: false for templates that need sudo
```

### Query Returns No Results

**Problem:** "No relevant context found"

**Solutions:**
1. Re-index with API key set
2. Check collection exists in Qdrant
3. Verify files were indexed (check logs)
4. Try fallback search (works without RAG)

---

## Contributing

### Reporting Bugs

1. Check existing issues on GitHub
2. Provide clear reproduction steps
3. Include system information
4. Attach relevant logs

### Adding Templates

1. Create YAML in `templates/` directory
2. Follow naming convention: `tool-name.yaml`
3. Test thoroughly
4. Document in PR
5. Update README

### Code Contributions

```bash
# Fork repository
git checkout -b feature/my-feature

# Make changes
cargo fmt
cargo clippy
cargo test

# Submit PR
```

### Template Guidelines

- Use non-sudo commands when possible
- Provide clear descriptions
- Include timeout values
- Document dependencies
- Test with multiple targets

---

## Best Practices

### Scanning

- Start with quick scans (nmap-quick, ping)
- Enable deep scans only when needed
- Use descriptive output directories
- Monitor disk space for large scans

### Querying

- Be specific in questions
- Use natural language
- Reference specific findings
- Try multiple phrasings

### Organization

- One directory per target
- Name directories clearly
- Clean old scans regularly
- Backup important results

### Security

- Don't commit API keys
- Use keychain for storage
- Rotate keys periodically
- Review scan data sensitivity

---

## Performance Tips

### For Limited Resources (< 8GB RAM)

- Use phi3 model (2.3GB)
- Or use OpenAI gpt-3.5-turbo
- Close other applications
- Smaller embedding models

### For Standard Systems (8-16GB RAM)

- Use llama3.1 (4.7GB) ⭐
- Use nomic-embed-text embeddings
- Enable multiple templates

### For High-End Systems (16GB+ RAM)

- Use llama3.1:70b (40GB)
- Use mxbai-embed-large embeddings
- Run parallel scans

---

## Workflows

### Single Target Assessment

```bash
# Scan
ipcrawler run -t 192.168.1.100 -o ./target1 --templates-dir ./templates

# Query
ipcrawler ask "security summary" -o ./target1

# Clean when done
ipcrawler clean --target 192.168.1.100
```

### Multiple Targets

```bash
# Scan each target
for ip in 192.168.1.{1..10}; do
  ipcrawler run -t $ip -o ./scan-$ip --templates-dir ./templates
done

# Query each
for ip in 192.168.1.{1..10}; do
  ipcrawler ask "findings?" -o ./scan-$ip
done
```

### Periodic Rescans

```bash
# Initial scan
ipcrawler run -t target.com -o ./scan-$(date +%Y%m%d) --templates-dir ./templates

# 1 month later
ipcrawler run -t target.com -o ./scan-$(date +%Y%m%d) --templates-dir ./templates

# All scans go to same collection - historical data available
```

---

## Command Reference

### Run Command

```bash
ipcrawler run -t <target> -o <output_dir> --templates-dir <dir> [flags]

Options:
  -t, --target <IP/DOMAIN>      Target to scan
  -o, --output <DIR>            Output directory
  --templates-dir <DIR>         Templates directory
  -v, --verbose                 Verbose output
```

### Ask Command

```bash
ipcrawler ask <question> -o <output_dir>

Options:
  -o, --output <DIR>            Scan output directory
```

### Clean Command

```bash
ipcrawler clean [options]

Options:
  --target <IP/DOMAIN>          Clean specific target
  --all                         Clean all collections
  --list                        List collections only
```

### Setup Command

```bash
ipcrawler setup

# Interactive wizard for configuration
```

---

## Additional Resources

### Documentation

- GitHub: https://github.com/neur0map/ipcrawler
- Issues: https://github.com/neur0map/ipcrawler/issues

### External Tools

- Ollama: https://ollama.ai
- Qdrant: https://qdrant.tech
- OpenAI: https://platform.openai.com
- Swiftide: https://swiftide.rs

### Dependencies

```toml
# Core
tokio = "1.42"           # Async runtime
clap = "4.5"             # CLI framework
serde = "1.0"            # Serialization

# RAG Pipeline
swiftide = "0.13"        # RAG framework
qdrant-client = "1.12"   # Vector database

# Setup Wizard
dialoguer = "0.11"       # Interactive prompts
indicatif = "0.17"       # Progress bars
colored = "2.1"          # Terminal colors

# Security
keyring = "2.3"          # API key storage
```

---

## License

MIT License - See LICENSE file for details

---

**Version:** 1.0.0
**Last Updated:** October 2025
**Status:** Production Ready ✅
