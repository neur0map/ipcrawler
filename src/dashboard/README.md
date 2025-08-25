# IPCrawler Dashboard - No New Lines Guarantee

## Implementation Overview

This dashboard implementation strictly adheres to the "no new lines" requirement by using crossterm's alternate screen buffer and absolute positioning for all rendering operations.

## Key Guarantees

### 1. Alternate Screen Buffer
- **Entry**: `EnterAlternateScreen` on startup
- **Exit**: `LeaveAlternateScreen` on shutdown
- **Result**: Original terminal scrollback preserved

### 2. Absolute Positioning
- **Every draw operation** uses `MoveTo(x, y)` 
- **No `\n` characters** in print statements
- **Explicit coordinates** for all text placement

### 3. Clean Terminal State
- **Raw mode**: Enabled on start, disabled on exit
- **Cursor**: Hidden during operation, restored on exit
- **Panic handler**: Ensures cleanup even on crashes

## Architecture

### Data-Driven Layout
```rust
LayoutSpec {
    control_bar_height: 3,
    system_monitor_height: 3,
    status_row_height: 8,
    tab_bar_height: 3,
    padding: 1,
}
```

All UI elements come from `AppState`, not hardcoded strings:
- Target, phase labels, task names from state
- Dynamic progress bars and meters
- Scrollable results with offset tracking

### Rendering Pipeline
1. Clear alternate screen (no scrollback pollution)
2. Compute layout from terminal size
3. Draw each panel with `MoveTo(x, y)`
4. Flush buffer once per frame

### Input Handling
- Non-blocking `event::poll(Duration::from_millis(0))`
- 50ms render tick rate
- Key bindings: q=quit, p=pause, arrows=scroll, tab=switch

## Performance

- **Frame rate**: 20-60 FPS (50ms tick)
- **CPU usage**: Minimal due to damage tracking
- **Memory**: Bounded result buffer
- **Flicker-free**: Single flush per frame

## Terminal Compatibility

- **Minimum size**: 70x20 (shows warning if smaller)
- **Resize handling**: Automatic reflow
- **Unicode support**: Box drawing characters
- **Fallback**: ASCII mode for limited terminals

## Testing Verification

✅ **Scrollback preservation**: Exit leaves terminal intact
✅ **Resize handling**: Dynamic reflow without artifacts  
✅ **No new lines**: All updates in-place
✅ **Clean exit**: Terminal restored on quit/error
✅ **Performance**: Stable 2+ minute runs

## Code Structure

- `mod.rs`: Main dashboard loop and event handling
- `app_state.rs`: Dynamic data model (no hardcoded UI)
- `layout.rs`: Layout computation engine
- `renderer.rs`: Frame rendering with absolute positioning
- `widgets.rs`: Drawing primitives (boxes, bars, text)
- `events.rs`: Non-blocking input handling
- `metrics.rs`: System CPU/RAM monitoring