# Contributing to IPCrawler

Thank you for your interest in contributing to IPCrawler! This document provides guidelines and information for contributors.

## About IPCrawler

IPCrawler is a comprehensive IP reconnaissance and network scanning tool developed under the [prowl.sh](https://prowl.sh) umbrella brand. It provides a unified interface for various network security tools and scanning capabilities.

## Getting Started

### Prerequisites

- Rust 1.70+ (latest stable recommended)
- Git
- Basic knowledge of network security concepts

### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ipcrawler.git
   cd ipcrawler
   ```
3. Install dependencies:
   ```bash
   cargo build
   ```
4. Run tests to ensure everything works:
   ```bash
   make check
   ```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Follow the existing code style and conventions
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass: `make check`

### 3. Commit Changes

Use clear, descriptive commit messages:

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
- `feat(cli): add CIDR notation support`
- `fix(scanner): resolve timeout handling issue`
- `docs(readme): update installation instructions`

### 4. Test Your Changes

```bash
# Run all quality checks
make check

# Run specific tests
make test

# Build release version
make build
```

### 5. Submit a Pull Request

1. Push your branch to your fork
2. Create a pull request against the main branch
3. Fill out the pull request template
4. Wait for review and address any feedback

## Code Style Guidelines

### Rust Code

- Use `cargo fmt` for formatting
- Follow `cargo clippy` recommendations
- Write clear, documented code
- Include unit tests for new functionality

### Tool Definitions

When adding new security tools:

1. Create YAML definitions in the `tools/` directory
2. Follow the existing schema and naming conventions
3. Include proper error handling and output parsing
4. Add tests for the new tool integration

### Documentation

- Update relevant documentation files
- Add inline documentation for complex code
- Update the README if adding user-facing features
- Consider adding examples to `tools/scripts/`

## Project Structure

```
ipcrawler/
├── src/                    # Main source code
│   ├── cli/               # Command-line interface
│   ├── config/            # Configuration management
│   ├── executor/          # Task execution engine
│   ├── output/            # Result processing
│   ├── system/            # System detection and utilities
│   ├── tools/             # Tool registry and management
│   └── ui/                # User interface components
├── tools/                 # External tool definitions
│   ├── *.yaml            # Tool configuration files
│   └── scripts/          # Example scripts
├── config/               # Configuration files
├── docs/                 # Documentation
└── tests/                # Integration tests
```

## Testing

### Running Tests

```bash
# All tests
make test

# Specific test categories
cargo test --lib
cargo test --bin ipcrawler

# Verbose output
make test-verbose
```

### Writing Tests

- Unit tests should be placed in the same module as the code they test
- Integration tests go in the `tests/` directory
- Mock external dependencies when necessary
- Test both success and failure cases

## Release Process

Releases are automated through the Makefile:

```bash
# Full release workflow
make release

# Individual steps
make clean
make check
make build
```

## Security Considerations

- This tool deals with network security scanning
- Ensure proper input validation
- Handle sensitive data appropriately
- Follow responsible disclosure practices
- Never commit credentials or sensitive information

## Getting Help

- Check the [documentation](docs/)
- Review existing issues and pull requests
- Join discussions in GitHub Issues
- Contact the maintainer: neur0map@prowl.sh

## License

By contributing to IPCrawler, you agree that your contributions will be licensed under the Apache License 2.0.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Recognition

Contributors are recognized in:
- The AUTHORS file
- Release notes
- Commit history (with proper attribution)

Thank you for contributing to IPCrawler and the prowl.sh ecosystem!