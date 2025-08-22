# ipcrawler Scripts

This directory contains utility scripts for ipcrawler installation, updates, and validation.

## Scripts

### update.sh
**Purpose:** Updates existing ipcrawler installations to the latest version  
**Usage:**
```bash
./update.sh
# or
curl -sSL https://install.ipcrawler.io/update.sh | bash
```

**Features:**
- Detects installation type (system/cargo/development)
- Creates backup before updating
- Verifies successful update
- Automatic rollback on failure

### validate_install.sh
**Purpose:** Pre-installation validation to check system compatibility  
**Usage:**
```bash
./validate_install.sh
```

**Checks:**
- Bash syntax validation of install.sh
- OS detection (macOS/Linux)
- Package manager availability
- Core dependency detection
- Required tools status

### test_install.sh
**Purpose:** Tests installation script components without making system changes  
**Usage:**
```bash
./test_install.sh
```

**Tests:**
- Script syntax
- Tool detection logic
- OS compatibility
- Package manager detection

## Main Installer

The primary installation script `install.sh` remains in the project root for easy access:

```bash
# From project root
./install.sh

# One-line installation
curl -sSL https://install.ipcrawler.io | bash
```

## Script Maintenance

These scripts are part of the ipcrawler distribution and should be:
- Kept executable (`chmod +x`)
- Tested on both macOS and Linux
- Updated when new dependencies are added
- Version-controlled with the main project

## Security Notes

- All scripts require appropriate permissions for system-wide installation
- Scripts create backups before making changes
- Update scripts verify signatures/checksums when available
- No sensitive data is transmitted or logged

For more information, see the [installation documentation](../installation.md).