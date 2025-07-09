"""
Main CLI entry point for IPCrawler (Refactored)
Minimal entry point that delegates to the application controller.
"""

import asyncio

from ..core.app import IPCrawlerApp


class IPCrawlerCLI:
    """Minimal CLI entry point that delegates to the application controller."""
    
    def __init__(self):
        self.app = IPCrawlerApp()
    
    async def main(self) -> None:
        """Main entry point that delegates to the application controller."""
        await self.app.run()


def main():
    """Entry point for the application."""
    cli = IPCrawlerCLI()
    asyncio.run(cli.main())