# Development Guide

## Getting Started

### Prerequisites

- Rust 1.70 or later
- Git
- Code editor with Rust support (VS Code, IntelliJ IDEA, etc.)

### Setting Up Development Environment

1. Clone the repository:
```bash
git clone <repository-url>
cd ipcrawler
```

2. Build the project:
```bash
cargo build
```

3. Run tests:
```bash
cargo test
```

4. Run with development profile:
```bash
cargo run -- -t 192.168.1.1 -p 80
```

## Development Workflow

### Building

```bash
# Development build (with debug symbols)
cargo build

# Release build (optimized)
cargo build --release

# Check for compilation errors without building
cargo check
```

### Testing

```bash
# Run all tests
cargo test

# Run specific test
cargo test test_parse_ports

# Run tests with output
cargo test -- --nocapture

# Run tests for specific module
cargo test --lib config
```

### Code Quality

```bash
# Run clippy (linter)
cargo clippy

# Run clippy with all warnings
cargo clippy -- -W clippy::all

# Format code
cargo fmt

# Check formatting without changing files
cargo fmt -- --check
```

### Running

```bash
# Run with cargo
cargo run -- -t 192.168.1.1 -p 80

# Run with LLM analysis
cargo run -- -t 192.168.1.1 -p 80 --use-llm

# Run release build
cargo run --release -- -t 192.168.1.1 -p 80

# Run with environment variables
RUST_LOG=debug cargo run -- -t 192.168.1.1 -p 80

# Dry-run mode for testing parsing
cargo run -- -t 192.168.1.1 -p 80 --dry-run

# Verbose mode with detailed output
cargo run -- -t 192.168.1.1 -p 80 --verbose --use-llm
```

## Project Structure

```
ipcrawler/
├── src/                    # Source code
│   ├── main.rs            # Entry point with LLM integration
│   ├── cli.rs             # CLI handling with new options
│   ├── config/            # Configuration
│   ├── system/            # System utilities
│   ├── tools/             # Tool management
│   ├── executor/          # Task execution
│   ├── llm/               # LLM integration module
│   │   ├── client.rs      # LLM client for multiple providers
│   │   └── prompts.rs     # Security analysis prompts
│   ├── output/            # Enhanced output handling
│   │   ├── universal.rs   # Universal Output Parser
│   │   └── test_universal.rs # Tests for universal parser
│   └── ui/                # Terminal UI
├── tools/                 # Tool YAML definitions
│   ├── nmap.yaml
│   ├── dig.yaml
│   └── scripts/           # Custom shell scripts
├── config/                # Configuration files
│   ├── wordlists.yaml
│   └── ports.yaml
├── docs/                  # Documentation
├── tests/                 # Integration tests
├── .env.example           # Environment variables template
├── Cargo.toml             # Dependencies
└── README.md              # Main documentation
```

## Adding a New Tool

### 1. Create Tool YAML

Create `tools/newtool.yaml`:

```yaml
name: "newtool"
description: "Description of the tool"
command: "newtool {{target}} -p {{port}} -o {{output_file}}"
sudo_command: "newtool {{target}} -p {{port}} --privileged -o {{output_file}}"
installer:
  apt: "apt install -y newtool"
  dnf: "dnf install -y newtool"
  pacman: "pacman -S --noconfirm newtool"
  brew: "brew install newtool"
timeout: 300
output:
  type: "json"  # or "xml" or "regex"
  patterns:
    - name: "finding_pattern"
      regex: "PATTERN: (.+)"
      severity: "medium"
```

### 2. Test the Tool

```bash
# Dry run to verify YAML parsing
cargo run -- -t 127.0.0.1 -p 80

# Check if tool is discovered
cargo build && ./target/debug/ipcrawler -t 127.0.0.1 -p 80
```

### 3. Add Tests (Optional)

Create test in `tests/tools_test.rs`:

```rust
#[test]
fn test_newtool_parsing() {
    // Test YAML parsing
    // Test command rendering
    // Test output parsing
}

#[tokio::test]
async fn test_newtool_llm_integration() {
    // Test LLM analysis of tool output
    // Test prompt template rendering
    // Test context-aware analysis
}
```

## Adding New Features

### 1. Plan the Feature

- Document requirements
- Design API/interfaces
- Consider backward compatibility
- Write tests first (TDD)

### 2. Implement

- Follow existing code patterns
- Use Rust idioms
- Add error handling
- Document public APIs

### 3. Test

- Unit tests for new functions
- Integration tests for workflows
- Manual testing
- Performance testing

### 4. Document

- Update relevant documentation
- Add code comments
- Update CHANGELOG
- Update README if needed

## Code Style Guidelines

### Naming Conventions

- **Modules:** `snake_case` (e.g., `tool_registry`)
- **Types:** `PascalCase` (e.g., `ToolRegistry`)
- **Functions:** `snake_case` (e.g., `parse_targets`)
- **Constants:** `SCREAMING_SNAKE_CASE` (e.g., `MAX_CONCURRENT`)

### Code Organization

- One module per file
- Group related functionality
- Keep functions focused and small
- Use descriptive names

### Error Handling

```rust
// Use anyhow::Result for functions that can fail
fn load_config() -> Result<Config> {
    let content = fs::read_to_string("config.yaml")
        .context("Failed to read config file")?;

    let config: Config = serde_yaml::from_str(&content)
        .context("Failed to parse config YAML")?;

    Ok(config)
}
```

### Documentation

```rust
/// Parses target input into a list of IP addresses.
///
/// Supports single IPs, CIDR ranges, and file-based targets.
///
/// # Arguments
///
/// * `input` - Target specification string
///
/// # Returns
///
/// Vector of IP address strings
///
/// # Errors
///
/// Returns error if input format is invalid
pub fn parse_targets(input: &str) -> Result<Vec<String>> {
    // Implementation
}
```

## Testing Strategy

### Unit Tests

Test individual functions in isolation:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_single_ip() {
        let result = parse_targets("192.168.1.1").unwrap();
        assert_eq!(result, vec!["192.168.1.1"]);
    }
}
```

### Integration Tests

Test complete workflows in `tests/`:

```rust
#[tokio::test]
async fn test_full_scan_workflow() {
    // Setup
    // Execute scan
    // Verify results
}
```

### Manual Testing

```bash
# Test various scenarios
cargo run -- -t 192.168.1.1 -p 80
cargo run -- -t 192.168.1.0/24 -p common
sudo cargo run -- -t 192.168.1.1 -p top-1000
```

## Debugging

### Debug Logging

```rust
// Add debug statements
eprintln!("Debug: value = {:?}", value);

// Use structured logging (if implemented)
log::debug!("Processing target: {}", target);
```

### GDB/LLDB

```bash
# Build with debug symbols
cargo build

# Run with debugger
rust-gdb target/debug/ipcrawler
# or
rust-lldb target/debug/ipcrawler
```

### Print Debugging

```rust
dbg!(variable);  // Prints variable with source location
```

## Performance Profiling

### Flamegraph

```bash
cargo install flamegraph
cargo flamegraph -- -t 192.168.1.1 -p 80
```

### Benchmarking

```bash
cargo bench
```

## Contributing

### Before Submitting

1. Run tests: `cargo test`
2. Run clippy: `cargo clippy`
3. Format code: `cargo fmt`
4. Update documentation
5. Add tests for new features

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request
6. Address review comments

### Commit Messages

Follow conventional commits:

```
feat: add support for custom port ranges
fix: resolve timeout issue with large scans
docs: update configuration guide
test: add tests for wordlist resolution
```

## Release Process

### Version Bumping

1. Update `Cargo.toml` version
2. Update `CHANGELOG.md`
3. Commit changes
4. Tag release: `git tag v0.2.0`
5. Push: `git push --tags`

### Building Release

```bash
# Build optimized binary
cargo build --release

# Strip symbols (reduce size)
strip target/release/ipcrawler

# Create archive
tar -czf ipcrawler-v0.2.0-linux-x64.tar.gz target/release/ipcrawler
```

## Troubleshooting Development Issues

### Dependency Issues

```bash
# Update dependencies
cargo update

# Clean and rebuild
cargo clean
cargo build
```

### Compilation Errors

```bash
# Check specific error
cargo check

# Verbose output
cargo build --verbose
```

### Test Failures

```bash
# Run specific test with output
cargo test test_name -- --nocapture

# Run tests serially
cargo test -- --test-threads=1
```

## Resources

- [Rust Book](https://doc.rust-lang.org/book/)
- [Tokio Documentation](https://tokio.rs/)
- [Clap Documentation](https://docs.rs/clap/)
- [Serde Documentation](https://serde.rs/)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
