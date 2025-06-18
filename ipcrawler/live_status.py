#!/usr/bin/env python3
"""
Clean live status display for ipcrawler
Provides a single-line status that updates in place without creating new lines
"""

import time
import sys
import threading
from datetime import datetime, timedelta
from ipcrawler.config import config

try:
    from rich.console import Console
    from rich.text import Text
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class LiveStatus:
    """Single-line live status display that updates in place"""
    
    def __init__(self):
        self.active = False
        self.console = None
        self.live = None
        self.current_status = "Ready"
        self.current_tool = ""
        self.current_target = ""
        self.start_time = None
        self.scan_count = 0
        self.completed_count = 0
        self.findings_count = 0
        self.active_scans = {}
        self._lock = threading.Lock()
        self._timer = None
        
    def start(self):
        """Start the live status display"""
        if not RICH_AVAILABLE or config.get("accessible", False):
            self.active = True
            self.start_time = time.time()
            return
            
        try:
            # Set start time immediately
            self.start_time = time.time()
            
            self.console = Console(
                file=sys.stderr,
                force_terminal=True,
                width=120,
                height=1,
                legacy_windows=False
            )
            
            # Create a simple live display that stays in one place
            self.live = Live(
                Text("● Ready to scan...", style="dim green"),
                console=self.console,
                refresh_per_second=1,  # Reduce refresh rate to prevent flickering
                auto_refresh=True,
                transient=False,  # Keep display visible
                redirect_stdout=False,
                redirect_stderr=False
            )
            
            self.live.start()
            self.active = True
            
            # Start a timer to update time display every second
            self._start_timer()
            
        except Exception as e:
            # Fallback to simple text mode
            self.active = True
            self.start_time = time.time()
            self._start_timer()
            
    def update(self, status=None, tool=None, target=None, action=None):
        """Update the live status display"""
        if not self.active:
            return
            
        with self._lock:
            if status:
                self.current_status = status
            if tool:
                self.current_tool = tool
            if target:
                self.current_target = target
                
            self._refresh_display()
    
    def add_scan(self, tool, target):
        """Add a running scan"""
        with self._lock:
            scan_key = f"{tool}:{target}"
            # Only refresh if this is a new scan
            if scan_key not in self.active_scans:
                self.active_scans[scan_key] = {
                    "tool": tool,
                    "target": target,
                    "start_time": time.time()
                }
                self.scan_count += 1
                self._refresh_display()
    
    def complete_scan(self, tool, target):
        """Mark a scan as completed"""
        with self._lock:
            scan_key = f"{tool}:{target}"
            if scan_key in self.active_scans:
                del self.active_scans[scan_key]
            self.completed_count += 1
            self._refresh_display()
    
    def add_finding(self):
        """Increment findings counter"""
        with self._lock:
            self.findings_count += 1
            self._refresh_display()
    
    def _start_timer(self):
        """Start periodic timer to update time display"""
        if self.active:
            self._refresh_display()
            self._timer = threading.Timer(1.0, self._start_timer)
            self._timer.daemon = True
            self._timer.start()
    
    def _stop_timer(self):
        """Stop the periodic timer"""
        if self._timer:
            self._timer.cancel()
            self._timer = None
    
    def _refresh_display(self):
        """Refresh the live display with current status"""
        if not self.live or not self.active:
            return
            
        try:
            # Calculate elapsed time with proper fallback
            if self.start_time:
                elapsed = time.time() - self.start_time
            else:
                elapsed = 0
            minutes, seconds = divmod(int(elapsed), 60)
            elapsed_str = f"{minutes:02d}:{seconds:02d}"
            
            # Status indicator with slower animation to reduce flickering
            if self.active_scans:
                # Slower animation - update every 0.5 seconds instead of multiple times per second
                spinner_chars = ["●", "○", "◐", "◑", "◒", "◓"]
                spinner_idx = int(time.time() * 1) % len(spinner_chars)  # Slower: *1 instead of *2
                status_char = spinner_chars[spinner_idx]
                status_color = "cyan"
            else:
                status_char = "●"
                status_color = "green"
            
            # Build status components
            components = [
                (status_char, f"bold {status_color}"),
                (" ", ""),
            ]
            
            # Current activity - always show the latest/current scan
            if self.active_scans:
                active_count = len(self.active_scans)
                # Get the most recently started scan (latest)
                latest_scan = max(self.active_scans.values(), key=lambda x: x.get("start_time", 0))
                tool_name = latest_scan["tool"][:12]  # Slightly longer for better info
                target_name = latest_scan["target"][:15] if ":" not in latest_scan["target"] else latest_scan["target"].split(":")[0][:12]
                
                if active_count == 1:
                    components.extend([
                        (f"Running {tool_name}", "white"),
                        (" on ", "dim"),
                        (target_name, "yellow"),
                    ])
                else:
                    components.extend([
                        (f"Running {tool_name}", "white"),
                        (" on ", "dim"),
                        (target_name, "yellow"),
                        (f" (+{active_count-1} more)", "dim"),
                    ])
            else:
                components.extend([
                    ("Idle", "dim"),
                ])
            
            # Separator and stats
            components.extend([
                (" │ ", "dim"),
                (f"Time: {elapsed_str}", "blue"),
            ])
            
            if self.completed_count > 0:
                components.extend([
                    (" │ ", "dim"),
                    (f"Completed: {self.completed_count}", "green"),
                ])
            
            if self.findings_count > 0:
                components.extend([
                    (" │ ", "dim"),
                    (f"Findings: {self.findings_count}", "red"),
                ])
            
            # Create the status text
            status_text = Text()
            for text, style in components:
                status_text.append(text, style=style)
            
            # Update the live display
            self.live.update(status_text)
            
        except Exception as e:
            # Silent fallback - don't spam errors
            pass
    
    def stop(self):
        """Stop the live status display"""
        if self.active:
            self.active = False
            self._stop_timer()
            
            if self.live:
                try:
                    # Show final status
                    final_text = Text.assemble(
                        ("✓", "bold green"),
                        (" Scan complete", "green"),
                        (f" │ Completed: {self.completed_count}", "dim"),
                        (f" │ Findings: {self.findings_count}", "red" if self.findings_count > 0 else "green")
                    )
                    self.live.update(final_text)
                    time.sleep(0.5)  # Brief pause to show final status
                    self.live.stop()
                except:
                    pass
            
            # Clean up
            self.live = None
            self.console = None
            self.active_scans.clear()


# Global instance
live_status = LiveStatus()


def start_live_status():
    """Start the live status display"""
    if config.get("verbose", 0) >= 1:  # Only show in verbose mode
        live_status.start()


def stop_live_status():
    """Stop the live status display"""
    live_status.stop()


def update_status(status=None, tool=None, target=None, action=None):
    """Update the live status"""
    live_status.update(status=status, tool=tool, target=target, action=action)


def add_scan(tool, target):
    """Add a running scan to the live status"""
    live_status.add_scan(tool, target)


def complete_scan(tool, target):
    """Mark a scan as completed in the live status"""
    live_status.complete_scan(tool, target)


def add_finding():
    """Add a finding to the live status counter"""
    live_status.add_finding()