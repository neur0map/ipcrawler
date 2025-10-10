# Development Guide

Guidelines for developing and contributing to IPCrawler.

## Setup

### Prerequisites

- Rust 1.70+ with Cargo
- Git
- Security tools (nmap, nikto, etc.) for testing

### Clone and Build

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
cargo build --release
```

### Development Build

```bash
# Debug build (faster compilation, slower execution)
cargo build

# Run without installing
cargo run -- <target> -o ./scan -v

# Run tests
cargo test --all-features

# Run specific test
cargo test test_name
```

## Code Quality

### Formatting

```bash
# Format code
cargo fmt

# Check formatting without modifying
cargo fmt --check
```

### Linting

```bash
# Run clippy
cargo clippy

# Run clippy with all features
cargo clippy --all-features

# Auto-fix some issues
cargo clippy --fix
```

### Testing

```bash
# Run all tests
cargo test --all-features

# Run with output
cargo test -- --nocapture

# Run tests matching pattern
cargo test nmap

# Run integration tests
cargo test --test '*'
```

## Project Structure

```
ipcrawler/
├── src/
│   ├── main.rs              # CLI entry point
│   ├── scanner/             # Core scanning logic
│   ├── templates/           # Template loading and parsing
│   ├── llm/                 # LLM integration
│   ├── parsers/             # Output parsers
│   ├── reporters/           # Report generation
│   └── config/              # Configuration management
├── templates/               # YAML tool templates
├── docs/                    # Documentation
└── tests/                   # Integration tests
```

## Adding New Features

### Adding a New Tool Template

No code changes required! See [Template Guide](../templates/README.md).

### Adding a New LLM Provider

1. Implement the `LLMProvider` trait in `src/llm/`
2. Add provider to `src/llm/factory.rs`
3. Update config schema
4. Add tests

### Adding a New Report Format

1. Create new reporter in `src/reporters/`
2. Implement the `Reporter` trait
3. Add to CLI arguments
4. Update output logic

## Debugging

### Verbose Output

```bash
# Enable verbose logging
cargo run -- <target> -o ./scan -v

# Enable debug logging
RUST_LOG=debug cargo run -- <target> -o ./scan
```

### Common Issues

**TTY Warning During Setup**

Build the release binary first:
```bash
cargo build --release
./target/release/ipcrawler setup
```

**Template Not Loading**

Check template syntax:
```bash
cargo run -- show <template_name>
```

**LLM Parsing Errors**

Test with `--no-parse` to isolate issue:
```bash
cargo run -- <target> -o ./scan --no-parse
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full guidelines.

### Quick Contribution Checklist

- [ ] Code follows existing style (run `cargo fmt`)
- [ ] No clippy warnings (run `cargo clippy`)
- [ ] Tests pass (run `cargo test`)
- [ ] Documentation updated if needed
- [ ] Commit messages are clear and descriptive

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit PR with clear description
6. Wait for review

## Release Process

1. Update version in `Cargo.toml`
2. Update changelog
3. Create git tag
4. Build release binaries
5. Update install script

## Architecture

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).
