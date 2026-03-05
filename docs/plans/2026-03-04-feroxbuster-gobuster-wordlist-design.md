# Feroxbuster + Gobuster VHost Templates with Wordlist Picker

## Problem
ipcrawler has no web content discovery or vhost enumeration tools. Users need directory brute-forcing (feroxbuster) and vhost discovery (gobuster vhost) with interactive wordlist selection defaulting to SecLists paths.

## Templates
- `templates/web/feroxbuster.yaml` — recursive dir brute-force, `{wordlist}` placeholder, priority 25
- `templates/web/gobuster_vhost.yaml` — vhost discovery with `--append-domain`, `{wordlist}` placeholder, priority 25

## Wordlist Picker
Conditional wizard step (like nmap ports) — only appears if feroxbuster or gobuster is selected. Each tool gets its own picker with use-case-appropriate presets.

### Feroxbuster presets (dir busting)
1. `raft-medium-directories.txt` (~30k) — recommended
2. `directory-list-2.3-medium.txt` (~220k) — thorough
3. `common.txt` (~4.7k) — quick
4. Custom path

### Gobuster VHost presets (subdomain/vhost)
1. `subdomains-top1million-5000.txt` (~5k) — recommended
2. `subdomains-top1million-20000.txt` (~20k) — deeper
3. `namelist.txt` (~1.9k) — lightweight
4. Custom path

## SecLists Path Resolution
Check in order: `/usr/share/seclists`, `/usr/share/SecLists`, `/opt/homebrew/share/seclists`. If none found, show only custom path input with error message.

## Validation
`os.Stat()` on resolved path before proceeding. Re-prompt on missing file.

## Runner Fix
`depends_on` treats unselected deps as satisfied (skip silently) instead of failing the dependent tool.

## Files Changed
- `templates/web/feroxbuster.yaml` (new)
- `templates/web/gobuster_vhost.yaml` (new)
- `internal/wizard/wizard.go` — wordlist picker step, RunConfig fields, buildConfig resolution
- `internal/wizard/preflight.go` — install hints
- `internal/runner/runner.go` — depends_on fix
- `internal/config/template.go` — no changes
