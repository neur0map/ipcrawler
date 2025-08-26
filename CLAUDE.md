# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## This file was created in version 0.1.0-alpha of IPCrawler.

## Build and Development Commands

```bash
# Primary commands
make build          # Complete setup: compile, check tools, create symlinks, install config
make test           # Run full validation: formatting, linting, unit tests
make clean          # Remove all artifacts, symlinks, and user config
make verbose-build  # Build with detailed output

# Direct cargo commands
cargo build --release       # Production build
cargo build                # Debug build
cargo fmt --all            # Format all code
cargo clippy -- -D warnings # Run linter
cargo test                 # Run unit tests
cargo test -- --nocapture  # Run tests with println! output

# Running the tool
./target/debug/ipcrawler --target 127.0.0.1 --skip-checks --verbose
./target/release/ipcrawler -t google.com
ipcrawler --help
```

## Architecture Overview

### Core Plugin System
IPCrawler uses a **concurrent plugin architecture** where all plugins execute simultaneously:

1. **Plugin Types** (src/plugins/types.rs):
   - `PortScan` trait - DNS/network discovery plugins (nslookup, dig, hosts_discovery, port_scanner)
   - `ServiceScan` trait - Service enumeration plugins (unused currently)
   - All plugins run in parallel via `tokio::spawn` in scheduler.rs

2. **Two-Phase Port Scanning**:
   - **RustScan** performs fast port discovery (1-3 seconds)
   - **Nmap** receives ONLY discovered ports for service detection (60-90 seconds)
   - RustScan passes discovered ports via `-p` flag to Nmap, no static port lists

3. **Configuration Philosophy** (CRITICAL):
   - **Built-in defaults** are hardcoded in each plugin
   - **global.toml** contains ONLY commented-out overrides
   - Plugins MUST work without any configuration file
   - Users uncomment sections to override specific settings
   - See `src/plugins/PLUGIN_IMPLEMENTATION_SPEC.md` for implementation guide

### Key Architectural Components

**State Management** (src/core/state.rs):
- `RunState` tracks execution across all plugins
- Services discovered by plugins accumulate in `state.services`
- UI events flow through `state.ui_sender`

**Concurrent Execution** (src/core/scheduler.rs):
- `execute_all_phases()` starts ALL plugins simultaneously
- Each plugin runs in its own `tokio::spawn` task
- Results are collected via `Arc<Mutex<Vec<Service>>>`

**Dashboard/TUI** (src/dashboard/):
- Real-time terminal UI with crossterm
- Runs in separate task, communicates via mpsc channels
- Falls back to CLI mode if terminal doesn't support raw mode
- Press 'q' to quit, arrow keys to navigate tabs

**Plugin Registry** (src/plugins/registry.rs):
- Conditionally loads plugins based on tool availability
- Validates all plugin dependencies before execution
- Tools like dnsx/httpx are optional and checked at runtime

### File Organization

```
src/
├── plugins/           # All reconnaissance plugins
│   ├── types.rs      # Trait definitions
│   ├── registry.rs   # Plugin loading and validation
│   └── {plugin}.rs   # Individual plugin implementations
├── core/             # Core execution logic
│   ├── scheduler.rs  # Parallel plugin execution
│   ├── state.rs      # Shared state management
│   └── models.rs     # Data structures (Service, Target)
├── dashboard/        # Terminal UI
├── config/           # Configuration handling
└── executors/        # Command execution utilities
```

### Output Structure

```
artifacts/runs/run_{target}_{timestamp}/
├── scans/            # Raw tool outputs
│   ├── {plugin}_results.txt
│   └── {plugin}_comprehensive.txt
└── report/           # Formatted reports
    ├── summary.txt   # Human-readable
    ├── summary.md    # Markdown format
    └── summary.json  # Machine-readable
```

## Plugin Development

To add a new plugin:
1. Follow `src/plugins/PLUGIN_IMPLEMENTATION_SPEC.md` exactly
2. Ensure plugin works WITHOUT configuration
3. Add COMMENTED config to global.toml for overrides
4. Update registry.rs for conditional loading if tools are optional
5. Use `Option<YourPluginConfig>` in config/types.rs

## Critical Implementation Notes

- **Configuration**: Never put active defaults in global.toml - only commented overrides
- **Tool Detection**: Optional tools must have availability checks in registry.rs
- **Stdin Tools**: dnsx/httpx require stdin input via `tokio::process::Command`
- **Parallel Execution**: All plugins start immediately, no sequential phases
- **Error Handling**: Plugins should gracefully handle partial failures
- **UI Communication**: Use `send_log()` for progress, `UiEvent::PortDiscovered` for results

## Testing Patterns

```bash
# Test specific functionality
cargo test test_target_validation
cargo test --package ipcrawler --lib -- plugins::tests

# Debug plugin execution
RUST_LOG=debug cargo run -- --target 127.0.0.1 --verbose

# Check what's being executed
timeout 20s ./target/debug/ipcrawler --target 127.0.0.1 --verbose 2>&1 | grep "Executing"
```

## Common Issues and Solutions

1. **Port scanner not finding services**: Check Nmap timeout settings in global.toml
2. **Terminal breaks on quit**: Terminal cleanup issue in dashboard/mod.rs teardown_terminal()
3. **Plugin not loading**: Verify tool availability check in registry.rs
4. **Config not working**: Ensure it's uncommented in global.toml and properly formatted
5. **Slow scans**: Adjust timeouts and intensity in global.toml overrides