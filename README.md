# 🔍 IPCrawler

> **CLI orchestrator for network reconnaissance workflows**

A high-performance, Python-based network reconnaissance tool that intelligently combines fast port discovery with detailed vulnerability scanning. Built for security professionals, penetration testers, and network administrators.

## ✨ Features

- **🚀 Smart Scanning**: Two-phase approach - fast port discovery followed by targeted detailed analysis
- **⚡ Parallel Processing**: Optimized concurrent scanning with configurable batch sizes
- **📊 Live Results**: Real-time scan progress with live file updates
- **📋 Multiple Output Formats**: JSON, TXT, and HTML reports with dark-themed styling
- **🔧 Highly Configurable**: YAML-based configuration for all scanning parameters
- **🛡️ Privilege-Aware**: Automatically adapts scanning techniques based on user privileges
- **📁 Organized Workspaces**: Timestamped result directories with proper file permissions
- **🎨 Rich CLI Interface**: Beautiful terminal UI with progress indicators and color coding

## 🏗️ Architecture

### Scanning Workflow

1. **Fast Port Discovery** (`nmap_fast_01`)
   - Quickly identifies open ports across all 65,535 ports
   - Uses optimized nmap parameters for speed
   - Duration: ~10-60 seconds

2. **Detailed Analysis** (`nmap_02`)  
   - Performs comprehensive service detection and vulnerability scanning
   - **Default**: Only scans ports discovered in phase 1 (efficient)
   - **Optional**: Full port range scanning when discovery is disabled
   - Duration: ~30 seconds to 2 minutes (targeted) or 5-10 minutes (full)

   > 🚧 **More workflows coming soon** - Additional reconnaissance and vulnerability scanning workflows are currently in development and will be added to expand the tool's capabilities.


### Key Benefits

- **Efficiency**: Targeted scanning reduces scan time by 80-90%
- **Accuracy**: 100% port coverage with detailed service analysis
- **Flexibility**: Configurable for both quick assessments and thorough audits

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **nmap** - Network exploration tool
  ```bash
  # macOS
  brew install nmap
  
  # Ubuntu/Debian
  sudo apt-get install nmap
  
  # Red Hat/CentOS
  sudo yum install nmap
  ```

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/neur0map/ipcrawler.git
   cd ipcrawler
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

### Basic Usage

```bash
# Scan a single IP address
python3 ipcrawler.py 192.168.1.100

# Scan a hostname
python3 ipcrawler.py example.com

# The tool will automatically:
# 1. Discover open ports (fast)
# 2. Perform detailed analysis on discovered ports
# 3. Generate comprehensive reports
```

## 📖 Usage Examples

### Standard Network Scan
```bash
python3 ipcrawler.py 10.0.0.50
```
**Output**: Discovers open ports, then performs detailed service detection and vulnerability analysis.

### Full Port Range Scan
```bash
# Edit config.yaml: set fast_port_discovery: false
python3 ipcrawler.py 192.168.1.1
```
**Output**: Comprehensive scan of all 65,535 ports with detailed analysis.

### Understanding the Output

When you run a scan, IPCrawler creates a timestamped workspace:
```
workspaces/
└── scan_192_168_1_100_20241231_143022/
    ├── scan_results.json      # Machine-readable results
    ├── scan_report.txt        # Human-readable detailed report
    ├── scan_report.html       # Web-viewable report with dark theme
    ├── live_results.json      # Real-time progress (if enabled)
    ├── live_report.txt        # Live text report
    └── live_report.html       # Live HTML report
```

## ⚙️ Configuration

IPCrawler uses `config.yaml` for all configuration options:

```yaml
# Scan Settings
scan:
  fast_port_discovery: true    # Enable 2-phase scanning (recommended)
  max_detailed_ports: 1000     # Limit detailed scan if too many ports found

# Performance Settings  
parallel:
  batch_size: 10              # Concurrent scan processes
  ports_per_batch: 6553       # Ports per batch for full scans

# Output Settings
output:
  save_raw_xml: false         # Save raw nmap XML output
  verbose: false              # Detailed console output
  raw_output: false           # Include binary data in reports
  real_time_save: true        # Enable live result updates

# Tool Paths (optional)
tools:
  nmap_path: ""              # Custom nmap binary path
```

### Key Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `fast_port_discovery` | `true` | Enable smart 2-phase scanning |
| `max_detailed_ports` | `1000` | Limit detailed scan scope |
| `real_time_save` | `true` | Save results during scanning |
| `batch_size` | `10` | Parallel process count |

## 📊 Output Formats

### JSON Report (`scan_results.json`)
```json
{
  "tool": "nmap",
  "target": "192.168.1.100",
  "duration": 45.2,
  "hosts": [
    {
      "ip": "192.168.1.100",
      "hostname": "router.local",
      "state": "up",
      "ports": [
        {
          "port": 22,
          "protocol": "tcp",
          "state": "open",
          "service": "ssh",
          "version": "OpenSSH 8.2"
        }
      ]
    }
  ]
}
```

### HTML Report Features
- 🌑 **Dark theme** optimized for terminal users
- 📱 **Responsive design** works on all devices  
- 🔍 **Searchable tables** for large result sets
- 🎨 **Syntax highlighting** for script outputs
- 📈 **Summary statistics** and scan metadata

## 🛠️ Advanced Usage

### Running with Elevated Privileges

For faster, more accurate scans:
```bash
sudo python3 ipcrawler.py 192.168.1.100
```

**Benefits of sudo/root access:**
- SYN stealth scanning (faster, more stealthy)
- OS detection capabilities
- Advanced timing optimizations
- Raw socket access for better performance

### Customizing Scan Scope

**Quick Assessment** (fast_port_discovery: true)
- Best for: Initial reconnaissance, large networks
- Time: ~1-2 minutes per host
- Coverage: All ports discovered, detailed analysis on open ports only

**Comprehensive Audit** (fast_port_discovery: false)  
- Best for: Thorough security assessments, compliance audits
- Time: ~5-10 minutes per host
- Coverage: Full 65,535 port scan with detailed analysis

### Integration with Other Tools

IPCrawler outputs can be easily integrated into security workflows:

```bash
# Extract open ports for further testing
jq '.hosts[].ports[] | select(.state=="open") | .port' scan_results.json

# Generate target list for other tools
jq -r '.hosts[] | select(.state=="up") | .ip' scan_results.json > targets.txt

# Count services by type
jq '.hosts[].ports[].service' scan_results.json | sort | uniq -c
```

## 🔧 Development

### Project Structure
```
ipcrawler/
├── config/                 # Configuration management
├── workflows/              # Scanning workflow implementations
│   ├── core/              # Base classes and utilities
│   ├── nmap_fast_01/      # Fast port discovery
│   └── nmap_02/           # Detailed vulnerability scanning
├── utils/                 # Utility functions
├── workspaces/            # Scan result storage
├── config.yaml           # Main configuration file
├── ipcrawler.py          # Main CLI entry point
└── requirements.txt      # Python dependencies
```

### Adding New Workflows

Workflows follow a numbered convention (`tool_XX`) to ensure proper execution order:

1. Create new workflow directory: `workflows/newtool_03/`
2. Implement `BaseWorkflow` interface
3. Add workflow to execution chain in `ipcrawler.py`

## 🐛 Troubleshooting

### Common Issues

**ImportError: No module named 'typer'**
```bash
pip install -r requirements.txt --break-system-packages
```

**Permission denied errors**
```bash
# Ensure nmap is installed and accessible
which nmap

# Run with sudo for advanced features
sudo python3 ipcrawler.py <target>
```

**No ports found**
- Verify target is reachable: `ping <target>`
- Check firewall settings
- Try with elevated privileges: `sudo python3 ipcrawler.py <target>`

**Slow scanning**
- Enable fast port discovery: Set `fast_port_discovery: true` in config.yaml
- Reduce batch size: Lower `batch_size` in config.yaml for resource-constrained systems

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests, report bugs, or suggest new features.

### Development Guidelines

1. Follow the existing code structure and naming conventions
2. Add appropriate error handling and logging
3. Update documentation for new features
4. Test with both privileged and unprivileged execution

## 🔗 Related Tools

- **nmap**: Network exploration and security auditing
- **nuclei**: Fast and customizable vulnerability scanner  
- **masscan**: High-speed port scanner
- **rustscan**: Modern port scanner built in Rust

---

**⚡ Built for speed, designed for accuracy, optimized for modern workflows.** 