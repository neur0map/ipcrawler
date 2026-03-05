# ipcrawler

Interactive CLI tool that orchestrates security reconnaissance tools against a target. Pick your tools from a menu, configure concurrency, and get a structured markdown report when it's done.

**Status: Under active development. Not production-ready.**

## How it works

1. Launch the binary — no flags, no config files
2. Interactive wizard asks for target (IP or domain), tool selection, wordlist, port config, and display mode
3. Tools run concurrently via a worker pool with priority ordering and dependency chains
4. Results are saved to `scans/<target>_<time>_<date>/` with raw output, error logs, engine log, and a compiled markdown report

## Features

- **YAML-based tool templates** compiled into the binary via `go:embed` — drop a YAML file in `templates/<category>/` and it's auto-discovered
- **Smart target detection** — auto-classifies IP vs domain, shows/hides tools by `target_type` compatibility (with `[DOMAIN]`/`[IP]` tags for incompatible tools)
- **Interactive wizard** built on [charmbracelet/huh](https://github.com/charmbracelet/huh) with custom Bubble Tea tool picker (search/filter, scroll, keyboard navigation)
- **Priority-based execution** — lower priority runs first, `depends_on` chains enforce ordering
- **Wordlist picker** — conditional huh Select for feroxbuster/gobuster with SecLists preset detection and custom path fallback
- **Nmap port override** — optional custom port spec when nmap is selected
- **Pre-flight tool checker** — detects missing binaries via `exec.LookPath`, shows install hints, offers to continue without them
- **Sudo credential caching** — detects `sudo` in both YAML field and inline commands, prompts once before execution
- **DNS recon → /etc/hosts pipeline** — subdomain/rDNS tools write to `dns_resolved.txt`, Hosts Updater injects IP→domain mappings with reversible markers
- **Worker pool** with configurable concurrency (1–10)
- **Two display modes** — live multi-spinner tracker or structured verbose logging
- **Markdown report** via `text/template` with resolved commands, status, and duration
- **Per-tool timeout** enforcement with process group kill
- **Graceful shutdown** on Ctrl+C

## Tool templates

Templates are YAML files in `templates/<category>/`. Each defines a command with `{target}`, `{raw_dir}`, and `{wordlist}` placeholders. New subdirectories are auto-discovered — no Go code changes needed.

### Included tools

| Tool | Category | Target | Priority | Description |
|------|----------|--------|----------|-------------|
| Ping | network | both | 10 | ICMP echo request to verify host is alive |
| Subdomain Resolver | recon | domain | 15 | Enumerate subdomains via subfinder + dnsx |
| Hakrevdns rDNS | recon | ip | 15 | Reverse DNS via passive sources |
| Amass Intel rDNS | recon | ip | 15 | Reverse DNS via OSINT APIs |
| DNSRecon PTR Lookup | recon | ip | 15 | Standard reverse PTR sweeps |
| Hosts Updater | recon | both | 17 | Inject resolved domains into /etc/hosts |
| Dig Comprehensive | dns | both | 20 | DNS records via dig ANY |
| Whois | dns | both | 20 | Domain/IP registration and ownership |
| Curl Headers | web | both | 20 | HTTP response headers |
| Feroxbuster Dir Scan | web | both | 25 | Recursive directory brute-force |
| Gobuster VHost Scan | web | both | 25 | Virtual host discovery |
| Nmap SV Scan | network | both | 50 | SYN scan + service detection |

### Execution flow

```
Priority 10: Ping                       (immediate)
Priority 15: Recon tools                (parallel — feed dns_resolved.txt)
Priority 17: Hosts Updater              (waits for selected recon tools)
Priority 20: Dig, Whois, Curl           (parallel)
Priority 25: Feroxbuster, Gobuster      (parallel)
Priority 50: Nmap SV Scan              (parallel)
```

Tools with `depends_on` wait only for dependencies that were selected — unselected deps are treated as satisfied.

## Template schema

```yaml
name: "Tool Name"
description: "What this tool does"
command: "tool-binary --flags {target}"
category: "network|dns|web|recon"
timeout: "30s"
target_type: "ip|domain|both"
tags: ["optional", "metadata"]
sudo: false
priority: 50
depends_on: ["Other Tool Name"]
```

### Placeholders

| Placeholder | Resolved to |
|-------------|-------------|
| `{target}` | User-provided target (IP or domain) |
| `{raw_dir}` | `scans/<target>_<time>_<date>/raw` |
| `{wordlist}` | User-selected wordlist path |

## Adding a new tool

1. Create `templates/<category>/your_tool.yaml`
2. Rebuild: `go build -o ipcrawler .`
3. The tool appears in the wizard automatically

No Go code changes required.

## Build

```
go build -o ipcrawler .
```

## Usage

```
./ipcrawler
```

The wizard handles everything else.

## Cleanup

Remove injected /etc/hosts entries:

```
sudo sed -i.bak '/^# ipcrawler START/,/^# ipcrawler END/d' /etc/hosts
```
