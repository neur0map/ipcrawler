# Custom Tool Picker — Design

## Problem

huh's MultiSelect does not truncate option labels or expose cursor position.
Two-line labels (description + command hint) interact poorly with huh's viewport,
which assumes each option is one terminal line. When lines wrap, scrolling breaks
(charmbracelet/huh#429). Our budget-based truncation is fragile — it can't precisely
predict huh's rendering chrome at every terminal width.

## Solution

Replace huh's MultiSelect for tool selection with a purpose-built Bubble Tea
component (`toolpicker.Model`). Single-line labels with ANSI-aware hard truncation.
Command hint shown as a "tooltip" below the list for the focused item only.

## Wizard Flow (Before → After)

**Before:** One big huh form (3 groups, LayoutColumns(2)) → port form → summary → confirm

**After:**
1. `collectSettings()` — huh form, 2 groups: Target + Workers/Display
2. `runToolPicker()` — custom Bubble Tea component, returns selected tool names
3. `collectNmapPorts()` — existing huh form (if nmap selected)
4. `buildConfig()` + summary + confirm

Outer loop restarts from step 1 if user declines at confirmation.

## Tool Picker Component

**File:** `internal/wizard/toolpicker.go`

### State

```go
type toolPickerModel struct {
    tools     []config.Template
    target    string
    cursor    int
    selected  map[int]bool
    filtering bool
    filter    string
    filtered  []int   // indices into tools
    done      bool
    aborted   bool
    width     int
    height    int
    offset    int     // scroll offset
}
```

### Key Handling

| Mode    | Key           | Action                              |
|---------|---------------|-------------------------------------|
| Normal  | ↑/k           | Cursor up (wraps)                   |
| Normal  | ↓/j           | Cursor down (wraps)                 |
| Normal  | space/x       | Toggle selection                    |
| Normal  | a             | Select all / deselect all           |
| Normal  | /             | Enter filter mode                   |
| Normal  | enter         | Confirm (requires >= 1 selected)    |
| Normal  | esc/ctrl+c    | Abort → outer loop restarts         |
| Filter  | typing        | Update filter, re-filter list       |
| Filter  | esc           | Exit filter, clear filter text      |
| Filter  | backspace     | Delete last char                    |

### Rendering

```
│ Tools
│ Space toggle · ↑↓ navigate · / filter · Enter confirm
│
│ > ✓ [DNS]      Dig Comprehensive : Perform a comprehensive DNS scan using dig
│   ✓ [DNS]      Whois             : Query domain/IP registration and ownersh…
│   · [NETWORK]  Nmap SV Scan      : SYN scan + service detection (top 100) [SUDO]
│   · [NETWORK]  Ping              : ICMP echo request to verify host is alive
│   · [WEB]      Curl Headers      : Fetch HTTP response headers from target
│
│   $ dig {target} ANY +noall +answer
```

- Single-line labels: `tag(10) + name(maxName) + " : " + desc + sudoTag`
- Each line hard-truncated with `ansi.Truncate(line, availWidth, "…")`
- Command hint at bottom shows `t.Command` for the focused item (raw placeholders)
- Selector: `"> "` (focused) / `"  "` (not focused)
- Prefix: `"✓ "` (selected, green) / `"· "` (unselected, gray)

### Scrolling

- Viewport height = terminal height - header(3) - hint(2) - help(1) - padding(2)
- If items exceed viewport, show a visible window and scroll with cursor
- Cursor wraps at list boundaries

## Files Modified

| File | Change |
|------|--------|
| `internal/wizard/toolpicker.go` | NEW — custom Bubble Tea component |
| `internal/wizard/wizard.go` | Refactor `Run()` into multi-step pipeline; extract `collectSettings()`, `runToolPicker()`; remove `buildToolOptions()` |

## No Changes Needed

- `internal/config/` — unchanged
- `internal/report/` — unchanged
- `internal/runner/` — unchanged
- `main.go` — unchanged
- `templates/` — unchanged
