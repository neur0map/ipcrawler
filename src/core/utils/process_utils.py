"""Process management utilities for IPCrawler"""

import sys
import signal
import subprocess
from typing import List, Optional
from src.core.ui.console.base import console


class ProcessManager:
    """Manages subprocess lifecycle and cleanup"""
    
    def __init__(self):
        self.running_processes: List[subprocess.Popen] = []
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C and other signals"""
        console.print("\n⚠ Scan interrupted. Cleaning up...")
        self.cleanup_all()
        sys.exit(0)
    
    def add_process(self, process: subprocess.Popen):
        """Add a process to be managed"""
        self.running_processes.append(process)
    
    def cleanup_all(self):
        """Clean up all running processes"""
        for process in self.running_processes:
            try:
                if process and process.returncode is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
            except:
                pass
        self.running_processes.clear()
    
    def cleanup_existing_nmap_processes(self):
        """Kill any existing nmap processes to prevent conflicts"""
        try:
            # Kill any existing nmap processes
            subprocess.run(['pkill', '-f', 'nmap'], capture_output=True, check=False)
        except:
            pass  # Ignore errors


# Global process manager instance
process_manager = ProcessManager()


# Convenience functions for backward compatibility
def cleanup_processes():
    """Clean up any running processes"""
    process_manager.cleanup_all()


def cleanup_existing_nmap_processes():
    """Kill any existing nmap processes to prevent conflicts"""
    process_manager.cleanup_existing_nmap_processes()


def signal_handler(signum, frame):
    """Handle Ctrl+C and other signals"""
    process_manager._signal_handler(signum, frame)