# Workflow Execution Order

IP Crawler executes workflows in a specific order to maximize efficiency and accuracy.

## DEFAULT BEHAVIOR: TARGETED SCANNING

**By default, IP Crawler ONLY scans ports that are discovered to be open.**

## Scan Workflow Order

### 1. `nmap_fast_01` - Fast Port Discovery (Default: ENABLED)
- **Purpose**: ONLY discovers which ports are open (does NOT perform vulnerability scanning)
- **When**: Runs first when `fast_port_discovery: true` in config.yaml (DEFAULT)
- **Tool**: Fast nmap scan (`-p- -T4 --min-rate 1000 --open -Pn -n`)
- **Duration**: ~10-60 seconds (privileged: faster, unprivileged: slower)
- **Output**: List of open port numbers ONLY
- **Accuracy**: 100% - scans all 65535 ports quickly
- **IMPORTANT**: If no ports are found, the scan stops here

### 2. `nmap_02` - Detailed Vulnerability Scanning
- **Purpose**: Comprehensive vulnerability and service scanning
- **When**: Always runs after port discovery
- **Modes**:
  - **DEFAULT - Targeted scan**: ONLY scans the specific ports found by nmap_fast_01
  - **Full scan**: ONLY when `fast_port_discovery: false` (scans all 65535 ports)
- **Duration**: 
  - Targeted: ~30 seconds to 2 minutes (depends on number of open ports)
  - Full scan: ~5-10 minutes (parallel batch scanning)

## Workflow Naming Convention

Workflows are numbered with the pattern: `tool_XX`
- `XX` represents the execution order (01, 02, etc.)
- This ensures workflows run in the correct sequence
- Makes it easy to add new workflows in the future

## Configuration

Control workflow behavior in `config.yaml`:

```yaml
scan:
  fast_port_discovery: true  # Enable/disable nuclei_01 workflow
  max_detailed_ports: 1000   # Limit ports for nmap_02 if too many found
```

## Why This Order?

1. **Efficiency**: Fast port discovery takes ~30 seconds vs detailed scan taking 10+ minutes
2. **Accuracy**: 100% accurate port discovery using nmap, then focused detailed scanning
3. **Speed**: Privileged scans are significantly faster than unprivileged
4. **Flexibility**: Can disable discovery for comprehensive scanning when needed