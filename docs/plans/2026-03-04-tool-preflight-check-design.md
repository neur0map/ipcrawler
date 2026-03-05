# Tool Pre-flight Check

## Problem
When a user selects tools that aren't installed, the runner fires `sh -c <command>` and the binary fails with a cryptic "command not found" buried in error logs. No upfront feedback.

## Design
Pre-flight check after wizard confirmation, before execution. Parses binary names from command strings, checks via `exec.LookPath`, and prompts the user to continue without missing tools or return to the wizard.

## Binary extraction
Split command on `|`, `&&`, `||`. Take the first token of each segment. Skip a hardcoded set of shell builtins/coreutils (`sudo`, `sh`, `bash`, `[`, `test`, `echo`, `cat`, `tee`, `awk`, `sed`, `grep`, `sort`, `head`, `tail`, `cut`, `tr`, `wc`, `uniq`). For `sudo`, take the next token instead. Deduplicate results.

## Install hints
A `map[string]string` covering tools referenced by shipped templates. macOS-oriented (brew for system tools, go install for Go tools). No platform detection.

## Wizard integration
After confirmation, before `needsSudo`:
1. `checkTools()` returns missing binaries
2. If empty, proceed normally
3. If non-empty, print formatted list with install hints, prompt "Continue without these tools?"
4. Yes: filter out affected templates + their dependents, proceed
5. No: return to wizard loop

## Files changed
- `internal/wizard/preflight.go` (new) — `extractBinaries()`, `checkTools()`, `filterMissing()`, `installHints`
- `internal/wizard/wizard.go` (modified) — ~15 lines after confirmation

## Not in scope
- Platform detection for hints
- Greying out tools in wizard UI
- Runtime "command not found" detection in runner
