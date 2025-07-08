# ipcrawler JSON Plugin Creation Guide

## Overview

This guide provides comprehensive instructions for creating successful JSON plugin templates for ipcrawler. JSON plugins enable you to add new security tools without modifying any code in the main application.

## Quick Start

1. Place your JSON file in the appropriate folder under `templates/`
2. Follow the schema structure defined in `tool-plugin-schema.json`
3. Test your plugin with `ipcrawler run category/plugin-name target`

## Schema Structure

Every JSON plugin must follow this basic structure:

```json
{
  "name": "plugin-name",
  "tool": "executable-name",
  "args": ["{{target}}"],
  "description": "Brief description of what this tool does",
  "author": "Your Name",
  "version": "1.0.0",
  "tags": ["recon", "network"],
  "env": {},
  "timeout": 60
}
```

## Field Reference

### Required Fields

#### `name` (string)
- **Purpose**: Unique identifier for the plugin
- **Requirements**: Alphanumeric, hyphens, underscores only
- **Example**: `"nmap-quick-scan"`

#### `tool` (string)
- **Purpose**: The executable tool to run
- **Requirements**: Must be a valid executable name or path
- **Examples**: `"nmap"`, `"curl"`, `"ping"`, `"dig"`

#### `args` (array of strings)
- **Purpose**: Arguments to pass to the tool
- **Requirements**: Array of string arguments
- **Target Substitution**: Use `{{target}}` where the target should be inserted
- **Examples**:
  ```json
  ["-sT", "-p", "80,443", "{{target}}"]
  ["-s", "-I", "http://{{target}}"]
  ["-c", "4", "{{target}}"]
  ```

### Optional Fields

#### `description` (string)
- **Purpose**: Human-readable description of what the tool does
- **Best Practice**: Keep it concise but informative
- **Example**: `"Fast TCP connect scan on common ports"`

#### `author` (string)
- **Purpose**: Plugin creator identification
- **Example**: `"Security Team"`

#### `version` (string)
- **Purpose**: Plugin version tracking
- **Format**: Semantic versioning recommended
- **Example**: `"1.2.0"`

#### `tags` (array of strings)
- **Purpose**: Categorization and filtering
- **Common Tags**: `"recon"`, `"vuln-scan"`, `"network"`, `"web"`, `"fast"`, `"thorough"`
- **Example**: `["network", "port-scan", "fast"]`

#### `dependencies` (array of strings)
- **Purpose**: List of required tools/packages
- **Example**: `["nmap", "curl"]`

#### `env` (object)
- **Purpose**: Environment variables to set during execution
- **Example**: 
  ```json
  {
    "NMAP_PRIVILEGED": "0",
    "CURL_CA_BUNDLE": "/etc/ssl/certs/ca-certificates.crt"
  }
  ```

#### `timeout` (integer)
- **Purpose**: Maximum execution time in seconds
- **Default**: 60 seconds
- **Range**: 1-3600 seconds
- **Example**: `120`

#### `output_mode` (string)
- **Purpose**: Expected output format
- **Values**: `"text"`, `"json"`, `"xml"`
- **Default**: `"text"`

#### `target_types` (array of strings)
- **Purpose**: Supported target types
- **Values**: `"ip"`, `"domain"`, `"url"`, `"file"`
- **Example**: `["ip", "domain"]`

#### `severity` (string)
- **Purpose**: Impact level of the scan
- **Values**: `"low"`, `"medium"`, `"high"`
- **Default**: `"medium"`

#### `stealth` (boolean)
- **Purpose**: Indicates if the tool is designed to be stealthy
- **Default**: `false`

#### `parallel_safe` (boolean)
- **Purpose**: Whether this tool can run safely in parallel with others
- **Default**: `true`

#### `output_format` (string)
- **Purpose**: Specific output format details
- **Example**: `"json-lines"`

## Privilege Requirements

### ⚠️ IMPORTANT: Root/Sudo Required Commands

Some security tools require elevated privileges to function properly. ipcrawler **does not** automatically handle privilege escalation. If your plugin requires root access:

1. **Document the requirement clearly** in the plugin description
2. **Test the plugin without privileges first** to ensure graceful failure
3. **Run ipcrawler with sudo** when using privileged plugins

#### Common Privileged Operations

**Network Scanning:**
- SYN scans (`nmap -sS`)
- UDP scans (`nmap -sU`) 
- OS detection (`nmap -O`)
- Advanced scans (`nmap -A`)

**Raw Packet Operations:**
- Custom packet crafting
- ICMP operations beyond basic ping
- Network interface manipulation

#### Non-Privileged Alternatives

Always prefer non-privileged alternatives when possible:

```json
// ❌ Requires root
"tool": "nmap",
"args": ["-sS", "-p", "80,443", "{{target}}"]

// ✅ No privileges needed
"tool": "nmap",
"args": ["-sT", "-p", "80,443", "{{target}}"]
```

## Template Examples

### Basic Network Scan
```json
{
  "name": "tcp-connect-scan",
  "tool": "nmap",
  "args": ["-sT", "-p", "80,443,8080,8443", "{{target}}"],
  "description": "TCP connect scan on common web ports",
  "author": "Security Team",
  "version": "1.0.0",
  "tags": ["network", "port-scan", "fast"],
  "timeout": 30,
  "target_types": ["ip", "domain"],
  "severity": "low",
  "stealth": true,
  "parallel_safe": true
}
```

### Web Application Testing
```json
{
  "name": "http-headers",
  "tool": "curl",
  "args": ["-s", "-I", "-L", "http://{{target}}"],
  "description": "Fetch HTTP headers and follow redirects",
  "author": "Web Team",
  "version": "1.1.0",
  "tags": ["web", "recon", "headers"],
  "timeout": 15,
  "target_types": ["domain", "url"],
  "severity": "low",
  "output_mode": "text"
}
```

### Vulnerability Scanning
```json
{
  "name": "nuclei-quick",
  "tool": "nuclei",
  "args": ["-u", "{{target}}", "-t", "exposures/", "-silent"],
  "description": "Quick vulnerability scan for common exposures",
  "author": "SecOps",
  "version": "2.0.0",
  "tags": ["vuln-scan", "web", "quick"],
  "dependencies": ["nuclei"],
  "timeout": 120,
  "target_types": ["url", "domain"],
  "severity": "medium",
  "parallel_safe": true
}
```

### Custom Environment Example
```json
{
  "name": "custom-nmap",
  "tool": "nmap",
  "args": ["--max-rate", "1000", "-p-", "{{target}}"],
  "description": "Full port scan with rate limiting",
  "tags": ["network", "thorough"],
  "env": {
    "NMAP_PRIVILEGED": "0",
    "TIMING_TEMPLATE": "4"
  },
  "timeout": 300,
  "severity": "medium",
  "stealth": false
}
```

## Best Practices

### 1. Command Design

**✅ DO:**
- Use absolute paths for unusual tools
- Include necessary flags for non-interactive operation
- Use `{{target}}` placeholder appropriately
- Test commands manually first

**❌ DON'T:**
- Use interactive flags (`-i`, `--interactive`)
- Rely on shell features (pipes, redirects)
- Include hardcoded IP addresses or domains

### 2. Timeout Configuration

**Guidelines:**
- **Fast scans**: 15-60 seconds
- **Medium scans**: 60-300 seconds  
- **Thorough scans**: 300-1800 seconds
- **Never exceed**: 3600 seconds (1 hour)

### 3. Tagging Strategy

**Recommended Tags:**
- **Speed**: `fast`, `medium`, `slow`, `thorough`
- **Category**: `recon`, `vuln-scan`, `web`, `network`, `dns`
- **Impact**: `safe`, `intrusive`, `noisy`
- **Purpose**: `discovery`, `enumeration`, `exploitation`

### 4. Error Handling

Your commands should:
- Exit with code 0 on success
- Exit with non-zero code on failure
- Provide meaningful error messages to stderr
- Handle timeouts gracefully

## Testing Your Plugin

### 1. Syntax Validation
```bash
# Validate JSON syntax
python -m json.tool your-plugin.json

# Validate against schema (if you have jsonschema installed)
jsonschema -i your-plugin.json tool-plugin-schema.json
```

### 2. Functionality Testing
```bash
# Test individual plugin
ipcrawler run category/your-plugin 127.0.0.1

# Test in folder context
ipcrawler scan-folder templates/category/ 127.0.0.1

# Check results
ipcrawler results 127.0.0.1
```

### 3. Integration Testing
```bash
# Test with other plugins
ipcrawler scan-all 127.0.0.1

# Export readable results
ipcrawler export 127.0.0.1 --output test-results.txt
```

## File Organization

### Directory Structure
```
templates/
├── recon/          # Reconnaissance tools
│   ├── nmap-*.json
│   ├── dns-*.json
│   └── discovery-*.json
├── web/            # Web application testing
│   ├── spider-*.json
│   ├── headers-*.json
│   └── vuln-*.json
├── network/        # Network scanning
│   ├── port-*.json
│   └── service-*.json
├── default/        # Basic/general tools
│   ├── ping.json
│   └── curl.json
└── custom/         # Your custom plugins
    └── your-tool.json
```

### Naming Conventions

**File Names:**
- Use lowercase
- Separate words with hyphens
- Include tool name and purpose
- Examples: `nmap-quick.json`, `nuclei-cves.json`, `curl-headers.json`

**Plugin Names:**
- Match the filename (without .json)
- Use descriptive, unique names
- Examples: `nmap-quick`, `nuclei-cves`, `curl-headers`

## Troubleshooting

### Common Issues

**Plugin Not Found:**
- Check file location and naming
- Verify JSON syntax
- Ensure proper category folder

**Command Fails:**
- Test command manually outside ipcrawler
- Check tool installation and PATH
- Verify target substitution works

**Timeout Issues:**
- Increase timeout value
- Test command performance manually
- Consider breaking into smaller scans

**Permission Denied:**
- Check if tool requires root privileges
- Use non-privileged alternatives
- Run ipcrawler with sudo if necessary

### Debug Mode

Enable debug logging by setting silent mode to false in config.toml:

```toml
[logging]
silent = false
log_level = "DEBUG"
```

### Log Analysis

Check logs for detailed execution information:
```bash
tail -f logs/ipcrawler-$(date +%Y-%m-%d).log
```

## Contributing Templates

### Submission Guidelines

1. **Test thoroughly** on multiple targets
2. **Document requirements** clearly
3. **Follow naming conventions**
4. **Include example output** in description
5. **Tag appropriately**

### Quality Checklist

- [ ] JSON syntax is valid
- [ ] Schema validation passes
- [ ] Command executes successfully
- [ ] Timeout is appropriate
- [ ] Tags are relevant
- [ ] Description is clear
- [ ] No hardcoded values
- [ ] Handles errors gracefully
- [ ] Documented privilege requirements

## Advanced Topics

### Custom Target Substitution

Advanced users can implement custom target validation and substitution by modifying the ToolExecutor class in main.py. The `substitute_template_vars` method handles target replacement.

### Environment Variable Usage

Use environment variables for configuration that might vary between systems:

```json
{
  "tool": "nmap",
  "args": ["--source-port", "${SOURCE_PORT:-12345}", "{{target}}"],
  "env": {
    "SOURCE_PORT": "54321"
  }
}
```

### Output Processing

ipcrawler automatically captures stdout and stderr. For structured output, consider:

1. Using tools with JSON output modes
2. Adding output parsing in the ToolExecutor class
3. Implementing custom result processors

## Support and Community

### Getting Help

1. Check the logs first: `logs/ipcrawler-YYYY-MM-DD.log`
2. Test plugins manually outside ipcrawler
3. Validate JSON syntax and schema compliance
4. Review this guide for best practices

### Resources

- **Schema File**: `tool-plugin-schema.json` - Complete field definitions
- **Config File**: `config.toml` - Global settings and template flags
- **Example Templates**: `templates/` directory - Working examples
- **Log Files**: `logs/` directory - Execution details and errors

---

**Remember**: This system is designed for **defensive security research only**. Always ensure you have proper authorization before scanning any targets, and respect rate limits and terms of service.