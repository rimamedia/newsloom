"""
Management command to run the MCP server.

This command starts the MCP server for Newsloom, which exposes tools and resources
for interacting with the Newsloom database and functionality.
"""

import asyncio
import logging
import signal
import sys
from django.core.management.base import BaseCommand

from mcp.server import NewsloomMCPServer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to run the MCP server.

    This command starts the MCP server for Newsloom, which exposes tools and resources
    for interacting with the Newsloom database and functionality.
    """

    help = "Run the MCP server for Newsloom"

    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument(
            "--log-level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set the logging level",
        )

    def handle(self, *args, **options):
        """Handle the command."""
        # Configure logging
        log_level = getattr(logging, options["log_level"])
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Run the server
        self.stdout.write(self.style.SUCCESS("Starting MCP server..."))

        try:
            asyncio.run(self._run_server())
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("MCP server stopped"))
            sys.exit(0)

    async def _run_server(self):
        """Run the MCP server."""
        server = NewsloomMCPServer()
        await server.start()

        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda: asyncio.create_task(self._shutdown(server))
            )

        try:
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def _shutdown(self, server):
        """Shutdown the server gracefully."""
        self.stdout.write(self.style.WARNING("Shutting down MCP server..."))
        await server.stop()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        asyncio.get_running_loop().stop()
