<div align="center">

# IPCrawler

**CLI orchestrator for network reconnaissance workflows**

A high-performance network reconnaissance tool that intelligently combines fast port discovery with detailed vulnerability scanning.

</div>

---

## Overview

IPCrawler is a Python-based reconnaissance orchestrator designed for security professionals, penetration testers, and network administrators. It implements a two-phase scanning approach that dramatically reduces scan time while maintaining comprehensive coverage.

<table>
<tr>
<td width="50%">

**Phase 1: Fast Discovery**
- Rapid port enumeration across all 65,535 ports
- Optimized nmap parameters for speed
- Duration: 10-60 seconds
- Identifies open ports only

</td>
<td width="50%">

**Phase 2: Detailed Analysis**
- Comprehensive service detection
- Vulnerability scanning on discovered ports
- Duration: 30 seconds - 2 minutes (targeted)
- Full service fingerprinting

</td>
</tr>
</table>

> 🚧 **More workflows coming soon** - Additional reconnaissance and vulnerability scanning workflows are currently in development and will be added to expand the tool's capabilities.

## Key Features

| Feature | Description |
|---------|-------------|
| **Smart Scanning** | Two-phase approach reduces scan time by 80-90% |
| **Parallel Processing** | Configurable concurrent scanning with batching |
| **Live Results** | Real-time progress updates and file generation |
| **Multiple Outputs** | JSON, TXT, and HTML reports with styling |
| **Privilege Aware** | Adapts techniques based on user permissions |
| **Organized Storage** | Timestamped workspaces with proper permissions |

## Installation

### Prerequisites

<table>
<tr>
<td align="center" width="33%">

**Python 3.8+**
```bash
python3 --version
```

</td>
<td align="center" width="33%">

**nmap**
```bash
# macOS
brew install nmap

# Ubuntu/Debian  
sudo apt install nmap
```

</td>
<td align="center" width="33%">

**Dependencies**
```bash
pip install -r requirements.txt \
    --break-system-packages
```

</td>
</tr>
</table>

### Setup

```bash
git clone https://github.com/neur0map/ipcrawler.git
cd ipcrawler
pip install -r requirements.txt --break-system-packages
```

## Usage

### Basic Scanning

```bash
# Standard scan with smart discovery
python3 ipcrawler.py 192.168.1.100

# Hostname scanning
python3 ipcrawler.py example.com
```

### Advanced Options

<table>
<tr>
<td width="50%">

**Quick Assessment**
```yaml
# config.yaml
scan:
  fast_port_discovery: true
  max_detailed_ports: 1000
```
- Best for: Initial recon, large networks
- Time: 1-2 minutes per host
- Coverage: Smart targeted scanning

</td>
<td width="50%">

**Comprehensive Audit**
```yaml
# config.yaml  
scan:
  fast_port_discovery: false
  max_detailed_ports: 65535
```
- Best for: Security assessments, compliance
- Time: 5-10 minutes per host  
- Coverage: Full 65,535 port analysis

</td>
</tr>
</table>

### Privilege Escalation

For enhanced scanning capabilities:

```bash
sudo python3 ipcrawler.py 192.168.1.100
```

**Benefits of elevated privileges:**
- SYN stealth scanning (faster, stealthier)
- OS detection capabilities  
- Advanced timing optimizations
- Raw socket access

## Configuration

The `config.yaml` file controls all scanning behavior:

<table>
<tr>
<td width="50%">

**Scan Settings**
```yaml
scan:
  fast_port_discovery: true
  max_detailed_ports: 1000
```

**Performance**
```yaml
parallel:
  batch_size: 10
  ports_per_batch: 6553
```

</td>
<td width="50%">

**Output Options**
```yaml
output:
  save_raw_xml: false
  verbose: false
  raw_output: false
  real_time_save: true
```

**Tool Paths**
```yaml
tools:
  nmap_path: ""
```

</td>
</tr>
</table>

## Output Formats

### Workspace Structure

Each scan creates a timestamped workspace:

```
workspaces/scan_192_168_1_100_20241231_143022/
├── scan_results.json      # Machine-readable data
├── scan_report.txt        # Human-readable report  
├── scan_report.html       # Web-viewable with dark theme
├── live_results.json      # Real-time updates (optional)
├── live_report.txt        # Live text format
└── live_report.html       # Live web format
```

### JSON Structure

```json
{
  "tool": "nmap",
  "target": "192.168.1.100", 
  "duration": 45.2,
  "hosts": [{
    "ip": "192.168.1.100",
    "hostname": "router.local",
    "state": "up",
    "ports": [{
      "port": 22,
      "protocol": "tcp", 
      "state": "open",
      "service": "ssh",
      "version": "OpenSSH 8.2"
    }]
  }]
}
```

## Integration

IPCrawler outputs integrate seamlessly with security workflows:

<table>
<tr>
<td width="50%">

**Extract Open Ports**
```bash
jq '.hosts[].ports[] | 
    select(.state=="open") | 
    .port' scan_results.json
```

**Generate Target Lists**
```bash
jq -r '.hosts[] | 
       select(.state=="up") | 
       .ip' scan_results.json > targets.txt
```

</td>
<td width="50%">

**Service Analysis**
```bash
jq '.hosts[].ports[].service' \
   scan_results.json | sort | uniq -c
```

**Port Counting**
```bash
jq '.hosts[].ports | length' \
   scan_results.json
```

</td>
</tr>
</table>

## Development

### Project Architecture

```
ipcrawler/
├── config/                 # Configuration management
├── workflows/              # Scanning implementations
│   ├── core/              # Base classes and utilities  
│   ├── nmap_fast_01/      # Fast port discovery
│   └── nmap_02/           # Detailed vulnerability scanning
├── utils/                 # Helper functions
├── workspaces/            # Result storage
├── config.yaml           # Main configuration
├── ipcrawler.py          # CLI entry point
└── requirements.txt      # Python dependencies
```

### Adding Workflows

1. Create workflow directory: `workflows/newtool_03/`
2. Implement `BaseWorkflow` interface
3. Register in execution chain

## Troubleshooting

<table>
<tr>
<td width="50%">

**Common Issues**

*ImportError: No module named 'typer'*
```bash
pip install -r requirements.txt \
    --break-system-packages
```

*Permission denied errors*
```bash
which nmap
sudo python3 ipcrawler.py <target>
```

</td>
<td width="50%">

**Performance Issues**

*No ports found*
- Verify target reachability: `ping <target>`
- Check firewall settings
- Try elevated privileges

*Slow scanning*
- Enable `fast_port_discovery: true`
- Reduce `batch_size` for low-resource systems

</td>
</tr>
</table>

## Contributing

We welcome contributions! Please:

1. Follow existing code structure and conventions
2. Add appropriate error handling  
3. Update documentation for new features
4. Test with both privileged and unprivileged execution

---

<div align="center">

**Built for speed, designed for accuracy, optimized for modern workflows**

[Report Issues](https://github.com/neur0map/ipcrawler/issues) • [Request Features](https://github.com/neur0map/ipcrawler/issues/new) • [Documentation](https://github.com/neur0map/ipcrawler/wiki)

</div> 