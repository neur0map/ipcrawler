# ipcrawler

Interactive CLI tool that orchestrates security reconnaissance tools against a target. Pick your tools from a menu, configure concurrency, and get a structured markdown report when it's done.

**Status: Under active development. Not production-ready.**

## How it works

1. Launch the binary — no flags, no config files
2. Interactive wizard asks for target, tool selection, concurrency, and display mode
3. Tools run concurrently via a worker pool with live progress tracking
4. Results are saved to `scans/` with raw output, error logs, and a compiled markdown report

## Current state

- YAML-based tool templates compiled into the binary via `go:embed`
- Interactive wizard built on [charmbracelet/huh](https://github.com/charmbracelet/huh)
- Worker pool execution with configurable concurrency (1–10)
- Two display modes: live multi-spinner tracker or structured verbose logging
- Markdown report generation via `text/template` with resolved commands, status, and duration
- Per-tool timeout enforcement
- Graceful shutdown on Ctrl+C

## Tool templates

Templates are YAML files in `templates/`. Each defines a command with a `{target}` placeholder.

### Included (starter pack)

| Tool | Category | Command |
|------|----------|---------|
| Ping | network | `ping -c 4 {target}` |
| Nmap SV Scan | network | `nmap -sV {target}` |
| Whois | dns | `whois {target}` |
| Curl Headers | web | `curl -I -s -L {target}` |

### Planned

| Tool | Category | Command |
|------|----------|---------|
| Traceroute | network | `traceroute {target}` |
| Nmap Aggressive | network | `nmap -A -T4 {target}` |
| Nmap UDP Top 100 | network | `nmap -sU --top-ports 100 {target}` |
| Masscan Top 1000 | network | `masscan -p1-1000 --rate=1000 {target}` |
| Dig A | dns | `dig A {target}` |
| Dig MX | dns | `dig MX {target}` |
| Dig NS | dns | `dig NS {target}` |
| Dig ANY | dns | `dig ANY {target} +noall +answer` |
| Host Lookup | dns | `host {target}` |
| DNSRecon | dns | `dnsrecon -d {target}` |
| Nikto | web | `nikto -h {target}` |
| WhatWeb | web | `whatweb {target}` |
| Gobuster | web | `gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt` |
| SSLScan | web | `sslscan {target}` |
| Testssl | web | `testssl.sh {target}` |
| Wafw00f | web | `wafw00f {target}` |
| Subfinder | dns | `subfinder -d {target} -silent` |
| HTTPx | web | `echo {target} \| httpx -silent -status-code -title` |
| Amass Enum | dns | `amass enum -passive -d {target}` |
| Nuclei | web | `nuclei -u {target} -silent` |

## Template schema

```yaml
name: "Tool Name"
description: "What this tool does"
command: "tool-binary --flags {target}"
category: "network|dns|web"
timeout: "30s"
tags: ["optional", "metadata"]
```

## Build

```
go build -o ipcrawler .
```

## Usage

```
./ipcrawler
```

That's it. The wizard handles everything else.
