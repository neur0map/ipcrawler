# Wordlist Legacy Code Audit Manifest

## Overview
This document catalogs all references to legacy wordlist management code found in the ipcrawler codebase. The goal is to remove all manual wordlist flags, helper functions, and configuration while preserving the auto-selection logic.

## Files with Wordlist References

### 1. Core Python Files

| File | Type | References | Lines | Description |
|------|------|------------|--------|-------------|
| `ipcrawler/main.py` | Core | 64 references | 1192-1588 | CLI args, wordlist manager init, overrides |
| `ipcrawler/config.py` | Config | 4 references | 36-98 | Config keys for smart wordlists |
| `ipcrawler/wordlists.py` | Module | Entire file | 1-400+ | **PRESERVE** - Auto-selection logic |
| `ipcrawler/smart_wordlist_selector.py` | Module | Entire file | N/A | **PRESERVE** - Auto-selection logic |
| `ipcrawler/technology_detector.py` | Module | Limited refs | N/A | **PRESERVE** - Auto-selection logic |
| `ipcrawler/io.py` | Utils | 1 reference | N/A | Debug/info messages |
| `ipcrawler/consolidator.py` | Utils | 1 reference | N/A | Report consolidation |

### 2. Configuration Files

| File | Type | References | Lines | Description |
|------|------|------------|--------|-------------|
| `ipcrawler/config.toml` | Config | 3 references | 38-44 | Smart wordlist settings - **PRESERVE** |
| `ipcrawler/global.toml` | Config | 1 reference | 4 | Comment about wordlist management |
| `data/wordlists/wordlists.toml` | Config | File exists | N/A | WordlistManager config - **PRESERVE** |

### 3. Documentation Files

| File | Type | References | Lines | Description |
|------|------|------------|--------|-------------|
| `README.md` | Doc | 12 references | Various | CLI examples, feature descriptions |
| `CLAUDE.md` | Doc | 17 references | Various | Development guidelines, commands |

### 4. YAML Plugin Files

| File | Type | References | Lines | Description |
|------|------|------------|--------|-------------|
| `yaml-plugins/03-bruteforce/bruteforce-http.yaml` | Plugin | 6 references | 24-96 | Wordlist placeholders - **PRESERVE** |
| `yaml-plugins/03-bruteforce/bruteforce-ssh.yaml` | Plugin | 6 references | Similar | Wordlist placeholders - **PRESERVE** |
| `yaml-plugins/02-service-enumeration/web-services/dirbuster.yaml` | Plugin | 47 references | Various | Wordlist resolution logic - **PRESERVE** |
| `yaml-plugins/02-service-enumeration/authentication-services/winrm-detection.yaml` | Plugin | 1 reference | N/A | Wordlist placeholder - **PRESERVE** |
| `yaml-plugins/02-service-enumeration/authentication-services/nmap-kerberos.yaml` | Plugin | 1 reference | N/A | Wordlist placeholder - **PRESERVE** |

### 5. Data Files

| File | Type | References | Lines | Description |
|------|------|------------|--------|-------------|
| `ipcrawler/data/technology_aliases.yaml` | Data | 2 references | N/A | Technology detection - **PRESERVE** |
| `ipcrawler/data/unified_wordlists_catalog.yaml` | Data | 2 references | N/A | Wordlist catalog - **PRESERVE** |

### 6. Scripts

| File | Type | References | Lines | Description |
|------|------|------------|--------|-------------|
| `scripts/generate_seclists_catalog.py` | Script | 5 references | N/A | SecLists catalog generation - **PRESERVE** |

## Legacy Code to Remove

### 1. CLI Arguments (main.py lines 1192-1200)
- `--wordlist-usernames`
- `--wordlist-passwords`
- `--wordlist-web-directories`
- `--wordlist-web-files`
- `--wordlist-subdomains`
- `--wordlist-snmp-communities`
- `--wordlist-dns-servers`
- `--wordlist-vhosts`
- `--wordlist-size` (fast/default/comprehensive)

### 2. Processing Logic (main.py lines 1545-1588)
- `wordlist_overrides` dictionary processing
- CLI override validation and setting
- Wordlist size mode processing
- All manual wordlist path validation

### 3. Configuration Keys (config.py)
- CLI argument processing for wordlist overrides
- Wordlist size configuration processing

### 4. Documentation References
- CLI usage examples with manual wordlist flags
- Configuration examples with manual wordlist paths

## Code to Preserve (Auto-Selection Logic)

### 1. Core Auto-Selection Modules
- `ipcrawler/wordlists.py` - **ENTIRE FILE** (WordlistManager class)
- `ipcrawler/smart_wordlist_selector.py` - **ENTIRE FILE**
- `ipcrawler/technology_detector.py` - **ENTIRE FILE**
- `scripts/generate_seclists_catalog.py` - **ENTIRE FILE**

### 2. Auto-Selection Configuration
- `smart-wordlists = true` in config.toml
- `smart-wordlists-confidence = 0.7` in config.toml
- `data/wordlists/wordlists.toml` - **ENTIRE FILE**
- `data/technology_aliases.yaml` - **ENTIRE FILE**
- `data/unified_wordlists_catalog.yaml` - **ENTIRE FILE**

### 3. YAML Plugin Wordlist Logic
- All YAML plugin wordlist resolution and usage
- Wordlist placeholders in plugin commands
- Auto-detection logic in dirbuster.yaml

### 4. WordlistManager Initialization
- `init_wordlist_manager()` function call
- Smart wordlist detection and configuration
- Auto-update and path detection logic

## Expected Behavior After Removal

1. **Removed Features:**
   - All manual wordlist CLI flags
   - Manual wordlist path configuration
   - Wordlist size selection (fast/default/comprehensive)
   - Manual wordlist validation

2. **Preserved Features:**
   - Automatic SecLists detection
   - Technology-based wordlist selection
   - Smart wordlist confidence scoring
   - YAML plugin wordlist resolution
   - WordlistManager auto-configuration

3. **Error Handling:**
   - Should still warn if SecLists not found
   - Should still provide installation hints
   - Should gracefully fallback to built-in logic

## Validation Criteria

1. **No CLI wordlist flags** should be accepted
2. **Smart wordlist selection** should continue working
3. **YAML plugins** should continue using wordlists via auto-selection
4. **No regression** in auto-detection functionality
5. **Clean removal** of all manual wordlist code paths

## Files Requiring Changes

1. `ipcrawler/main.py` - Remove CLI args and processing logic
2. `ipcrawler/config.py` - Remove manual wordlist configuration keys
3. `README.md` - Remove CLI examples with manual wordlist flags
4. `CLAUDE.md` - Update development guidelines

## Files to Preserve Unchanged

1. `ipcrawler/wordlists.py` - Core auto-selection logic
2. `ipcrawler/smart_wordlist_selector.py` - Technology detection
3. `ipcrawler/technology_detector.py` - Detection algorithms
4. All YAML plugin files - Wordlist resolution logic
5. All data files - Wordlist catalogs and configurations
6. Scripts - WordlistManager utilities

---

**Status**: Ready for Phase 1.2 - Code & Config Removal