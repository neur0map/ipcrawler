# ipcrawler

A simple, modern CLI that orchestrates external recon tools via a typed, compile-time plugin model and a strict, bounded-concurrency scheduler.

## Features

- Dev-local containment: all binaries, artifacts, outputs, logs live inside the repo folder
- Minimal CLI: only `-t|--target`, `-v|--verbose`, `-d|--debug`, `-h|--help`
- Fail-fast behavior with precise error reporting
- Bounded concurrency scheduler with separate pools for port and service scans
- Atomic report generation with mandatory validation

## Quickstart

```bash
# Verify environment
make verify

# Run a scan
make run RUN_ARGS="-t scanme.nmap.org -v"
# or with GNU make:
make run -- -t scanme.nmap.org -v
```

## Outputs

All outputs are stored under `./artifacts/`:
- `./artifacts/logs/` - Application logs
- `./artifacts/runs/<run-id>/` - Per-run artifacts
- `./artifacts/runs/<run-id>/report/` - Summary reports (required for successful run)

## Development

```bash
make build      # Build the binary
make fmt        # Format code
make clippy     # Run linter
make check      # Run tests
make clean      # Clean artifacts
```

## Configuration & Defaults

### Concurrency Settings
- **Max Total Scans**: 50 concurrent operations
- **Port Scan Pool**: 10 concurrent nmap processes  
- **Service Scan Pool**: 40 concurrent service probes
- **Port Range**: nmap default (top 1000 most common ports)
- **File Descriptors Required**: 1024 minimum (2048 recommended)

### Tools & Timeouts
- **nmap**: Configurable via global.toml (default: TCP connect scan -sT -sV -T4), 5 minute timeout
- **curl**: Configurable via global.toml (default: -s -L -I), 15 second timeout  
- **Parallelism**: Currently SEQUENTIAL execution (not truly parallel)
- **Configuration**: Override any tool command/args in global.toml

### Default Scan Scope
- **Ports Scanned**: ~1000 (nmap's default top ports list)
- **Protocols**: TCP only
- **Service Detection**: HTTP services on discovered ports

## Requirements

### External Tools
External tools (must be installed manually):
- nmap
- curl

Run `make tools` to check tool availability.

### System Requirements
- **File Descriptors**: Minimum 1024 (for concurrent scanning)

## Troubleshooting

### "File descriptor limit too low" Error
If you see this error:
```
fatal: Preflight checks failed:
File descriptors: File descriptor limit too low: 256 (minimum: 1024)
```

**Quick Fix (current session):**
```bash
ulimit -n 2048
./artifacts/bin/ipcrawler -t target.com -v
```

**Permanent Fix:**
Add to your `~/.zshrc` or `~/.bash_profile`:
```bash
# Increase file descriptor limit for ipcrawler
ulimit -n 2048
```

**Why this is required:** ipcrawler uses bounded concurrency (up to 50 concurrent scans) and needs sufficient file descriptors to avoid mid-scan failures.