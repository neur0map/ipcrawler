#!/usr/bin/env python3
"""
ipcrawler - Entry point for the security tool orchestration CLI.

Run this script to use ipcrawler:
  python3 ipcrawler.py list
  python3 ipcrawler.py run --template default 127.0.0.1
  python3 ipcrawler.py schema
"""

from ipcrawler.cli.main import main

if __name__ == "__main__":
    main() 