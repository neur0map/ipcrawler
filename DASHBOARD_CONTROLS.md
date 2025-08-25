# IPCrawler Dashboard Controls

## Key Bindings

| Key | Action |
|-----|--------|
| `Q` | Quit application (sends SIGINT for clean exit) |
| `Ctrl+C` | Force quit application |
| `←` `→` | Switch between tabs (Overview, Ports, Services, Logs) |
| `↑` `↓` | Scroll results view up/down |
| `PgUp` `PgDn` | Page up/down in results (10 lines) |

## Interface Layout

```
┌─ IPCrawler ──────────────────────────────────────────────────────────────┐
│ Target: example.com                      [Q]uit | [←→] Switch Tabs | [↑↓] │
├─ System ─────────────────────────────────────────────────────────────────┤
│ CPU: ██████░░░░ 65.2% | RAM: 4.2GB | Time: 00:02:34                     │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌─ Scan Progress ──────┐ ┌─ Active Tasks ──────────────────────────────┐ │
│ │ Phase 1: Port Scan   │ │ • nmap_portscan                      [12s] │ │
│ │ ████████████░░ 85%   │ │ • dns_enum                           [8s]  │ │
│ │ 17/20 tasks          │ │ • httpx_probe                        [3s]  │ │
│ └──────────────────────┘ └─────────────────────────────────────────────┘ │
├─ Tabs (←→ to switch) ────────────────────────────────────────────────────┤
│ [Overview] | Ports | Services | Logs                                     │
├─ Results ────────────────────────────────────────────────────────────────┤
│ 22/tcp    SSH         OpenSSH 8.0                                        │
│ 80/tcp    HTTP        nginx/1.18.0                                       │
│ 443/tcp   HTTPS       nginx/1.18.0                                       │
│ 3306/tcp  MySQL       MySQL 5.7.31                                       │
│                                                           [Scroll: 15%]   │
└──────────────────────────────────────────────────────────────────────────┘
```

## Features

- **Live Updates**: CPU, RAM, elapsed time, and scan progress update in real-time
- **No Scrollback Pollution**: Uses alternate screen buffer - your terminal history is preserved
- **Dynamic Layout**: Adapts to terminal resize automatically
- **Minimum Size**: 70x20 characters (shows warning if smaller)
- **Clean Exit**: Always restores terminal to original state

## Tab Navigation

Use **Left/Right arrow keys** to switch between tabs:
- **Overview**: General scan progress and active tasks
- **Ports**: Discovered open ports and services  
- **Services**: Service enumeration results
- **Logs**: Scan execution logs and events

## Scrolling

Use **Up/Down arrows** or **PgUp/PgDn** to scroll through results in the active tab view.

## Exit Behavior

Both `Q` and `Ctrl+C` will:
1. Send graceful shutdown signal to running scans
2. Restore terminal cursor and raw mode
3. Leave alternate screen (preserving scrollback)
4. Exit with status code 0