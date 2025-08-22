# Testing Configurations

This directory contains YAML configuration files used for development and testing purposes. These are not production-ready reconnaissance profiles but rather test scenarios to validate tool functionality.

## Test Files

### Concurrency & Performance Tests
- **`many_tools_test.yaml`** - Tests dynamic concurrency with 8 tools and 3 parallel slots
- **`chain_test.yaml`** - Tests tool chaining functionality
- **`fast_chain.yaml`** - Quick chaining test for development

### Error Handling Tests  
- **`error_test.yaml`** - Tests error handling and recovery
- **`invalid.yaml`** - Invalid YAML syntax for parser testing
- **`invalid_chain.yaml`** - Invalid chain configuration testing
- **`test_missing.yaml`** - Tests missing tool dependencies

### Development Tests
- **`test.yaml`** - General development testing configuration

## Usage

Use these test configs with full path specification (extension optional):

```bash
# Test concurrency management (both work)
ipcrawler -t example.com -c testing/many_tools_test --dry-run
ipcrawler -t example.com -c testing/many_tools_test.yaml --dry-run

# Test chaining functionality  
ipcrawler -t example.com -c testing/chain_test --verbose

# Test error handling
ipcrawler -t example.com -c testing/error_test --debug

# Mix testing and production configs
ipcrawler -t example.com -c testing/chain_test,quick-scan --list-tools
```

## Production Configs

For actual reconnaissance work, use the production configs in the `/config` directory:
- `default.yaml` - Basic reconnaissance
- `quick-scan.yaml` - Fast scanning
- `network-scan.yaml` - Network-focused
- `web-scan.yaml` - Web application focused
- `enterprise-scan.yaml` - Large-scale enterprise scanning

## Note

These test configurations use simple echo commands and sleep timers to simulate tool execution without requiring actual security tools to be installed.