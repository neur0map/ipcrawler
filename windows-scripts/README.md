# IPCrawler Windows Scripts

This directory contains Windows batch files for managing IPCrawler on Windows systems using Docker.

## 📁 Files Overview

### `ipcrawler-windows.bat`
**Main launcher script for IPCrawler on Windows**

- **Purpose**: Sets up and runs IPCrawler in a Docker container
- **What it does**:
  - Checks Docker installation and daemon status
  - Builds IPCrawler Docker image (first run only)
  - Creates results directory for scan outputs
  - Tests container functionality
  - Launches interactive IPCrawler session
- **Safe to run**: ✅ Yes - only creates Docker resources and directories

### `ipcrawler-clean.bat`
**Complete cleanup and uninstall script**

- **Purpose**: Removes ALL IPCrawler components and Docker resources
- **What it does**:
  - Stops all IPCrawler containers
  - Removes Docker images, containers, volumes, networks
  - Cleans Docker Compose resources
  - Deletes local results directory
  - Performs aggressive Docker cleanup
- **Safe to run**: ⚠️ **DESTRUCTIVE** - permanently deletes all IPCrawler data

## 🚀 Quick Start

### Option 1: Using Batch Scripts (Recommended)
1. Ensure Docker Desktop is installed and running
2. Open Command Prompt as Administrator (recommended)
3. Navigate to the IPCrawler root directory (not this folder)
4. Run: `windows-scripts\ipcrawler-windows.bat`

### Option 2: Universal Docker Commands
```cmd
# Build the container (one-time setup)
docker build -t ipcrawler .

# Run IPCrawler interactively
docker run -it --rm -v "%cd%\results:/scans" -w /scans ipcrawler

# Inside container: run scans
ipcrawler --help
ipcrawler 192.168.1.1
```

### Regular Usage
```batch
# Launch IPCrawler (automated)
windows-scripts\ipcrawler-windows.bat

# Launch IPCrawler (manual)
docker run -it --rm -v "%cd%\results:/scans" -w /scans ipcrawler

# Clean everything (when needed)
windows-scripts\ipcrawler-clean.bat
```

## 📋 Prerequisites

- **Windows 10/11** with Command Prompt or PowerShell
- **Docker Desktop** installed and running
- **Administrator privileges** (recommended for Docker operations)
- **Internet connection** (for first-time Docker image build)

## 🔧 How to Use

### Running IPCrawler

1. **From IPCrawler root directory**:
   ```batch
   windows-scripts\ipcrawler-windows.bat
   ```

2. **The script will**:
   - Check Docker installation
   - Build image (first run takes 5-10 minutes)
   - Launch interactive container
   - Mount `results/` directory for outputs

3. **Inside the container**:
   ```bash
   # Show available tools
   /show-tools.sh
   
   # Get help
   ipcrawler --help
   
   # Run a scan
   ipcrawler 192.168.1.1
   
   # Exit container
   exit
   ```

### Cleaning Up

1. **Complete removal**:
   ```batch
   windows-scripts\ipcrawler-clean.bat
   ```

2. **The script will**:
   - Ask for confirmation (type `y` to proceed)
   - Remove all Docker components
   - Delete scan results
   - Free up disk space

## ⚠️ Important Safety Notes

### For `ipcrawler-windows.bat`:
- ✅ **Safe to run multiple times**
- ✅ **Non-destructive** - only creates resources
- ✅ **Preserves existing scan results**
- ⚠️ **Requires Docker** - will fail gracefully if not available

### For `ipcrawler-clean.bat`:
- ❌ **DESTRUCTIVE** - permanently deletes data
- ❌ **Cannot be undone** - removes all scan results
- ⚠️ **Asks for confirmation** before proceeding
- ✅ **Safe to cancel** - type anything other than `y` to abort

## 🗂️ File Locations

When running from IPCrawler root directory:

```
ipcrawler/
├── windows-scripts/
│   ├── README.md                 ← This file
│   ├── ipcrawler-windows.bat     ← Main launcher
│   └── ipcrawler-clean.bat       ← Cleanup script
├── results/                      ← Scan outputs (created by launcher)
├── Dockerfile                    ← Docker build instructions
└── docker-compose.yml           ← Docker Compose config
```

## 🛠️ Troubleshooting

### Common Issues

**"Docker command not found"**
- Install Docker Desktop
- Restart Command Prompt after installation
- Add Docker to PATH if needed

**"Docker daemon not accessible"**
- Start Docker Desktop
- Wait for whale icon in system tray
- Check Docker Desktop is running (not just installed)

**"Dockerfile not found"**
- Make sure you're running from IPCrawler root directory
- Don't run from inside `windows-scripts/` folder

**Build fails with exit code 100**
- Check internet connection
- Try running cleanup script first
- Restart Docker Desktop

### Getting Help

1. **Check Docker status**: `docker --version` and `docker ps`
2. **Run cleanup script** to reset everything
3. **Restart Docker Desktop** if issues persist
4. **Run as Administrator** if permission errors occur

## 🔄 Workflow Examples

### Development Workflow
```batch
# Build and test
windows-scripts\ipcrawler-windows.bat

# Make changes to code...

# Clean and rebuild
windows-scripts\ipcrawler-clean.bat
windows-scripts\ipcrawler-windows.bat
```

### Regular Usage
```batch
# Daily scanning
windows-scripts\ipcrawler-windows.bat
# ... perform scans ...
# Results saved to results/ directory

# Weekly cleanup (optional)
windows-scripts\ipcrawler-clean.bat
```

## 📊 What Gets Installed/Removed

### Tools Installed (in Docker container):
- **Network**: nmap, netcat, curl, wget
- **DNS**: dig, nslookup (dnsutils)
- **SMB**: smbclient
- **SSL**: sslscan  
- **Brute Force**: hydra
- **Windows**: impacket suite
- **Python**: IPCrawler + dependencies

### Resources Created:
- Docker image (~500MB)
- Docker containers (temporary)
- `results/` directory (persistent)
- Docker volumes (if any)

### Complete Removal:
- All Docker images and containers
- All Docker volumes and networks
- Local results directory
- Docker build cache

## 🚀 Quick Reference

### Universal Docker Commands (No batch files needed)
```cmd
# One-time build
docker build -t ipcrawler .

# Run scan (Command Prompt)
docker run -it --rm -v "%cd%\results:/scans" -w /scans ipcrawler 10.10.10.1

# Run scan (PowerShell)
docker run -it --rm -v "${PWD}\results:/scans" -w /scans ipcrawler 10.10.10.1

# Interactive session
docker run -it --rm -v "%cd%\results:/scans" -w /scans ipcrawler bash

# Complete cleanup
docker rmi ipcrawler && docker system prune -f
```

### Batch Script Commands (Automated)
```cmd
# Full setup and launch
windows-scripts\ipcrawler-windows.bat

# Complete cleanup
windows-scripts\ipcrawler-clean.bat
```

---

**💡 Tip**: Keep this README handy for reference when using IPCrawler on Windows! 