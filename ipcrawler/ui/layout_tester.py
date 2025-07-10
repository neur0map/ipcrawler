"""
Layout tester for previewing Rich TUI layouts.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from .layout_base import BaseLayoutRenderer
from .layout_executive import ExecutiveDashboardLayout
from .plugin_tracker import PluginTracker, PluginInfo, PluginState


class LayoutTester:
    """Test harness for previewing Rich TUI layouts."""
    
    def __init__(self):
        self.console = Console()
        self.available_layouts = {
            "executive": ExecutiveDashboardLayout
        }
        self.mock_config = {
            "theme": "minimal",
            "enable_rich_ui": True,
            "fullscreen_mode": False,
            "refresh_rate": 2
        }
    
    def create_mock_plugin_tracker(self) -> PluginTracker:
        """Create a mock plugin tracker with realistic data."""
        tracker = PluginTracker()
        
        # Mock templates and tools
        mock_templates = [
            ("ping-test", "ping"),
            ("curl-headers", "curl"),
            ("nmap-quick", "nmap"),
            ("robots-txt", "curl"),
            ("dns-info", "dig"),
            ("ssl-cert", "openssl"),
            ("ferox-dirs", "feroxbuster"),
            ("gobuster-dirs", "gobuster"),
            ("nuclei-scan", "nuclei"),
            ("whatweb-scan", "whatweb"),
            ("nikto-scan", "nikto"),
            ("dirb-scan", "dirb"),
            ("wpscan-check", "wpscan"),
            ("enum4linux", "enum4linux"),
            ("smbclient-check", "smbclient")
        ]
        
        template_names = [name for name, _ in mock_templates]
        tools = [tool for _, tool in mock_templates]
        
        # Initialize scan
        tracker.initialize_scan("example.com", template_names, tools)
        tracker.scan_start_time = datetime.now() - timedelta(seconds=45)
        
        return tracker
    
    def simulate_scan_progress(self, tracker: PluginTracker, progress_stage: str) -> None:
        """Simulate different stages of scan progress."""
        if progress_stage == "start":
            # Just started - most queued, few active
            tracker.start_plugin("ping-test")
            tracker.start_plugin("curl-headers")
            
        elif progress_stage == "early":
            # Early stage - some completed, some active
            tracker.start_plugin("ping-test")
            tracker.complete_plugin("ping-test", success=True)
            
            tracker.start_plugin("curl-headers")
            tracker.complete_plugin("curl-headers", success=True)
            
            tracker.start_plugin("nmap-quick")
            tracker.start_plugin("robots-txt")
            
        elif progress_stage == "middle":
            # Middle stage - mix of all states
            tracker.complete_plugin("ping-test", success=True)
            tracker.complete_plugin("curl-headers", success=True)
            tracker.complete_plugin("nmap-quick", success=True)
            tracker.complete_plugin("robots-txt", success=True)
            tracker.complete_plugin("dns-info", success=True)
            
            tracker.start_plugin("ssl-cert")
            tracker.complete_plugin("ssl-cert", success=False, error="timeout")
            
            tracker.start_plugin("ferox-dirs")
            tracker.start_plugin("gobuster-dirs")
            tracker.start_plugin("nuclei-scan")
            
        elif progress_stage == "late":
            # Late stage - most completed, few remaining
            completed = ["ping-test", "curl-headers", "nmap-quick", "robots-txt", 
                        "dns-info", "whatweb-scan", "nikto-scan", "dirb-scan", 
                        "wpscan-check", "enum4linux"]
            
            for plugin in completed:
                tracker.complete_plugin(plugin, success=True)
            
            tracker.complete_plugin("ssl-cert", success=False, error="timeout")
            tracker.complete_plugin("gobuster-dirs", success=False, error="exit code 1")
            
            tracker.start_plugin("ferox-dirs")
            tracker.start_plugin("nuclei-scan")
            tracker.start_plugin("smbclient-check")
    
    def create_demo_layout(self, layout_name: str, progress_stage: str = "middle") -> BaseLayoutRenderer:
        """Create a demo layout with mock data."""
        if layout_name not in self.available_layouts:
            raise ValueError(f"Unknown layout: {layout_name}")
        
        # Create layout with mock data
        tracker = self.create_mock_plugin_tracker()
        self.simulate_scan_progress(tracker, progress_stage)
        
        layout_class = self.available_layouts[layout_name]
        layout = layout_class(self.mock_config, tracker)
        layout.set_scan_active(True)
        
        return layout
    
    def preview_layout(self, layout_name: str, theme: str = "minimal", 
                      progress_stage: str = "middle", duration: int = 10) -> None:
        """Preview a layout with live updates."""
        if layout_name not in self.available_layouts:
            self.console.print(f"[red]Error:[/red] Unknown layout '{layout_name}'")
            self.console.print(f"Available layouts: {', '.join(self.available_layouts.keys())}")
            return
        
        # Update config with theme
        self.mock_config["theme"] = theme
        
        # Create layout
        layout = self.create_demo_layout(layout_name, progress_stage)
        
        # Show preview
        self.console.print(f"\n[bold]Preview: {layout.get_layout_name()} Layout[/bold]")
        self.console.print(f"Theme: {theme} | Progress: {progress_stage} | Duration: {duration}s")
        self.console.print("\n[dim]Press Ctrl+C to exit preview...[/dim]\n")
        
        try:
            with Live(layout.get_layout(), console=self.console, refresh_per_second=2) as live:
                import time
                for i in range(duration * 2):  # 2 updates per second
                    layout.update_display()
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    
    def compare_layouts(self, theme: str = "minimal", progress_stage: str = "middle") -> None:
        """Compare all available layouts side by side."""
        self.console.print(f"\n[bold]Layout Comparison[/bold]")
        self.console.print(f"Theme: {theme} | Progress: {progress_stage}")
        self.console.print("\n[dim]Press Ctrl+C to exit comparison...[/dim]\n")
        
        # Create layouts
        layouts = {}
        for name in self.available_layouts.keys():
            self.mock_config["theme"] = theme
            layouts[name] = self.create_demo_layout(name, progress_stage)
        
        # Show comparison
        try:
            for name, layout in layouts.items():
                self.console.print(f"\n[bold blue]▶ {layout.get_layout_name()}[/bold blue]")
                layout.update_display()
                self.console.print(layout.get_layout())
                self.console.print("─" * 80)
                
        except KeyboardInterrupt:
            pass
    
    def list_layouts(self) -> None:
        """List all available layouts with descriptions."""
        self.console.print("\n[bold]Available Rich TUI Layouts[/bold]\n")
        
        for name, layout_class in self.available_layouts.items():
            # Create temporary instance to get description
            temp_layout = layout_class(self.mock_config, PluginTracker())
            description = temp_layout.get_layout_name()
            
            self.console.print(f"[bold cyan]{name}[/bold cyan]: {description}")
        
        self.console.print(f"\n[dim]Total layouts: {len(self.available_layouts)}[/dim]")
    
    def test_themes(self, layout_name: str = "executive") -> None:
        """Test a layout with all available themes."""
        themes = ["minimal", "dark", "matrix", "cyber", "hacker", "corporate"]
        
        self.console.print(f"\n[bold]Theme Testing: {layout_name}[/bold]\n")
        
        for theme in themes:
            self.console.print(f"[bold]{theme.upper()} THEME[/bold]")
            
            # Create layout with theme
            self.mock_config["theme"] = theme
            layout = self.create_demo_layout(layout_name, "middle")
            layout.update_display()
            
            # Show preview
            self.console.print(layout.get_layout())
            self.console.print("─" * 80)


def main():
    """Main function for layout testing."""
    if len(sys.argv) < 2:
        print("Usage: python -m ipcrawler.ui.layout_tester <command> [options]")
        print("\nCommands:")
        print("  list                          - List all available layouts")
        print("  preview <layout>              - Preview a layout")
        print("  compare                       - Compare all layouts")
        print("  themes <layout>               - Test all themes with a layout")
        print("\nOptions:")
        print("  --theme <theme>               - Set theme (minimal, dark, matrix, cyber, hacker, corporate)")
        print("  --progress <stage>            - Set progress stage (start, early, middle, late)")
        print("  --duration <seconds>          - Preview duration in seconds")
        print("\nExamples:")
        print("  python -m ipcrawler.ui.layout_tester list")
        print("  python -m ipcrawler.ui.layout_tester preview executive")
        print("  python -m ipcrawler.ui.layout_tester preview cards --theme cyber")
        print("  python -m ipcrawler.ui.layout_tester compare --theme matrix")
        return
    
    tester = LayoutTester()
    command = sys.argv[1]
    
    # Parse options
    theme = "minimal"
    progress_stage = "middle"
    duration = 10
    
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--theme" and i + 1 < len(sys.argv):
            theme = sys.argv[i + 1]
            i += 2
        elif arg == "--progress" and i + 1 < len(sys.argv):
            progress_stage = sys.argv[i + 1]
            i += 2
        elif arg == "--duration" and i + 1 < len(sys.argv):
            duration = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    # Execute command
    if command == "list":
        tester.list_layouts()
    elif command == "preview":
        if len(sys.argv) < 3:
            print("Error: preview command requires layout name")
            return
        layout_name = sys.argv[2]
        tester.preview_layout(layout_name, theme, progress_stage, duration)
    elif command == "compare":
        tester.compare_layouts(theme, progress_stage)
    elif command == "themes":
        if len(sys.argv) < 3:
            print("Error: themes command requires layout name")
            return
        layout_name = sys.argv[2]
        tester.test_themes(layout_name)
    else:
        print(f"Error: Unknown command '{command}'")


if __name__ == "__main__":
    main()