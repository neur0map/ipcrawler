# Configuration Guide

Complete configuration instructions for IPCrawler.

## Quick Setup

```bash
# Interactive setup wizard
ipcrawler setup

# View current config
ipcrawler config
```

## LLM Providers

IPCrawler supports multiple LLM providers for parsing tool outputs:

### Groq (Recommended)

Fast, reliable, and generous free tier.

1. Get API key: https://console.groq.com
2. Configure:
```bash
ipcrawler setup
# or
export LLM_PROVIDER="groq"
export LLM_API_KEY="your-key-here"
```

### OpenAI

High quality, paid service.

1. Get API key: https://platform.openai.com
2. Configure:
```bash
export LLM_PROVIDER="openai"
export LLM_API_KEY="your-key-here"
```

### Anthropic

Claude models, paid service.

1. Get API key: https://console.anthropic.com
2. Configure:
```bash
export LLM_PROVIDER="anthropic"
export LLM_API_KEY="your-key-here"
```

### Ollama (Local)

Run models locally, completely free and private.

1. Install Ollama: https://ollama.ai
2. Pull a model:
```bash
ollama pull llama3
```
3. Configure:
```bash
export LLM_PROVIDER="ollama"
# No API key needed
```

## Configuration Files

### Config Location

```
~/.config/ipcrawler/config.toml    # Main configuration (0600 permissions)
./templates/                       # YAML tool templates
./templates/wordlists.toml         # Wordlist definitions
```

### Config File Format

```toml
[llm]
provider = "groq"
api_key = "your-encrypted-key-here"
model = "llama3-70b-8192"  # Provider-specific model

[scan]
default_ports = "1-1000"
default_wordlist = "common"
consistency_passes = 3
```

## Environment Variables

You can override config file settings using environment variables:

```bash
# LLM configuration
export LLM_PROVIDER="groq"
export LLM_API_KEY="your-key"
export LLM_MODEL="llama3-70b-8192"

# Scan settings
export IPCRAWLER_PORTS="1-65535"
export IPCRAWLER_WORDLIST="big"
export IPCRAWLER_CONSISTENCY_PASSES="5"
```

## Security

- Config files stored with `0600` permissions (read/write for owner only)
- API keys are masked in all output
- Hidden password-style input during setup
- No credentials in logs or reports
- Keys encrypted at rest (depending on OS keyring support)

## Template Configuration

Templates are configured via YAML files in the `./templates/` directory.

See [Template Guide](../templates/README.md) for complete documentation.

## Wordlist Configuration

Wordlists are defined in `./templates/wordlists.toml`:

```toml
[wordlists.common]
path = "/usr/share/seclists/Discovery/Web-Content/common.txt"
description = "Common files and directories"

[wordlists.medium]
path = "/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt"
description = "Medium-sized directory list"
```

### Adding Custom Wordlists

Edit `./templates/wordlists.toml`:

```toml
[wordlists.mylist]
path = "/path/to/my/wordlist.txt"
description = "My custom wordlist"
```

Then use it:
```bash
ipcrawler <target> -w mylist -o <output>
```
