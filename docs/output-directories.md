# Output Directory Management

This document explains how ipcrawler manages output directories in different environments and how to customize output locations.

## Automatic Output Directory Selection

ipcrawler automatically selects appropriate output directories based on smart context detection:

### Development Context
**When:** Running from project directory (where `Cargo.toml` exists)  
**Output Directory:** `./recon-results/`  
**Purpose:** Local development, testing, and project-based scanning

### System Installation Context
**When:** Binary installed system-wide and run outside project directory  
**Output Directory:** User data directory (XDG-compliant)
- **macOS:** `~/Library/Application Support/io.recon-tool.recon-tool/results/`
- **Linux:** `~/.local/share/io.recon-tool.recon-tool/results/` 
- **Windows:** `%APPDATA%\io.recon-tool.recon-tool\results\`

**Note:** Both contexts have identical features and UI - only the output path differs.

## Custom Output Paths

You can override the default behavior using the `-o` or `--output` flag:

```bash
# Use custom directory
ipcrawler -t example.com -c quick-scan -o /path/to/custom/results

# Use relative path
ipcrawler -t example.com -c quick-scan -o ../scan-results

# Use absolute path  
ipcrawler -t example.com -c quick-scan --output /home/user/security-scans
```

## Output Structure

Within the base output directory, ipcrawler creates timestamped subdirectories:

```
{output_base}/
├── target_name_2025-08-21_14-30-45/
│   ├── scan_summary.json          # Machine-readable results
│   ├── scan_summary.html          # Human-readable report
│   ├── logs/
│   │   └── execution.log          # Execution logs
│   ├── raw/                       # Raw tool outputs
│   │   ├── nmap_results.xml
│   │   ├── naabu_ports.txt
│   │   └── ...
│   └── errors/                    # Error logs
└── another_scan_2025-08-21_15-45-30/
    └── ...
```

## Directory Information

Use the `--paths` flag to see current directory configuration:

```bash
ipcrawler --paths
```

This shows:
- Current default output directory
- Development vs production paths
- Directory creation status
- Existing scan count

## Examples

### Development Workflow
```bash
# Running from project directory
cd /path/to/ipcrawler-rust
./target/release/ipcrawler -t example.com -c quick-scan
# → Results in: ./recon-results/example_com_2025-08-21_14-30-45/
```

### Production Usage
```bash
# System-wide installed binary
ipcrawler -t example.com -c quick-scan  
# → Results in: ~/.local/share/ipcrawler/results/example_com_2025-08-21_14-30-45/
```

### Custom Output
```bash
# Custom location for specific project
ipcrawler -t client-site.com -c enterprise-scan -o /projects/client-pentest/results
# → Results in: /projects/client-pentest/results/client-site_com_2025-08-21_14-30-45/
```

### Multiple Configs with Custom Output
```bash
# Multiple configs, custom location
ipcrawler -t target.com -c quick-scan,network-scan,web-scan -o /tmp/multi-scan
# → Results in: /tmp/multi-scan/target_com_2025-08-21_14-30-45/
```

## Permissions and Security

### Development Mode
- Uses local project directory
- No special permissions required
- Results stay within project

### Production Mode  
- Uses user's data directory
- Respects XDG Base Directory specification
- No root/admin privileges required
- Results isolated per user

### Custom Paths
- ipcrawler will attempt to create the directory if it doesn't exist
- Requires write permissions to the specified path
- Parent directories must be accessible

## Troubleshooting

### Permission Denied
```bash
# Check directory permissions
ls -la /path/to/output/directory

# Try with different output location
ipcrawler -t example.com -c quick-scan -o ~/alternative-location
```

### Directory Not Created
```bash
# Check paths and permissions
ipcrawler --paths

# Use verbose mode to see path resolution
ipcrawler -t example.com -c quick-scan --verbose
```

### Multiple Scans Organization
```bash
# Organize by date
ipcrawler -t example.com -c quick-scan -o ~/scans/$(date +%Y-%m-%d)

# Organize by target
ipcrawler -t example.com -c quick-scan -o ~/scans/example-com

# Organize by client/project
ipcrawler -t client.com -c enterprise-scan -o ~/pentesting/client-name/scans
```

## Best Practices

1. **Use custom output paths for organized workflows:**
   ```bash
   # Client work
   ipcrawler -t client.com -c enterprise-scan -o ~/clients/acme-corp/scan-results
   
   # Bug bounty
   ipcrawler -t target.com -c web-scan -o ~/bug-bounty/target-name
   ```

2. **Leverage automatic timestamping:**
   - Each scan gets a unique timestamped directory
   - No need to manually organize by time
   - Easy to track scan history

3. **Use verbose mode for clarity:**
   ```bash
   ipcrawler -t example.com -c quick-scan -o /custom/path --verbose
   ```

4. **Check paths before important scans:**
   ```bash
   ipcrawler --paths
   ```

## Integration with CI/CD

For automated scanning in CI/CD pipelines:

```bash
# Jenkins/GitHub Actions
ipcrawler -t $TARGET -c $SCAN_PROFILE -o $WORKSPACE/scan-results

# Docker containers
ipcrawler -t example.com -c quick-scan -o /output/mounted-volume
```