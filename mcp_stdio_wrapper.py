#!/usr/bin/env python3
"""
MCP stdio wrapper for Docker deployment
Ensures proper stdio transport and handles Docker-specific networking
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment files
if Path("/.dockerenv").exists():  # Running in Docker
    # In Docker, update FalkorDB host to use Docker networking
    load_dotenv(".env.graphiti")
    load_dotenv(".env", override=True)  # Override with mounted .env
    
    # Update FalkorDB host for Docker networking
    if sys.platform == "darwin" or sys.platform == "win32":
        os.environ["FALKORDB_HOST"] = "host.docker.internal"
else:
    # Local development
    load_dotenv(".env.graphiti")
    load_dotenv(Path.home() / ".env", override=True)

# Configure logging for MCP
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]  # Log to stderr to keep stdout clean for MCP
)
logger = logging.getLogger(__name__)

async def main():
    """Run the MCP server with stdio transport"""
    try:
        # Import after environment is configured
        import mcp.server.stdio
        from mcp.server.models import InitializationOptions
        from mcp.server import NotificationOptions
        
        # Import our server (this will use the configured environment)
        from mcp_server import server
        
        logger.info("Starting Graphiti MCP Server (stdio transport)")
        logger.info(f"FalkorDB Host: {os.getenv('FALKORDB_HOST', 'localhost')}")
        logger.info(f"FalkorDB Port: {os.getenv('FALKORDB_PORT', '6380')}")
        logger.info(f"Group ID: {os.getenv('GRAPHITI_GROUP_ID', 'shared_gtd_knowledge')}")
        
        # Run server with stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="graphiti-claude-code-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure all dependencies are installed")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure unbuffered output for Docker
    os.environ["PYTHONUNBUFFERED"] = "1"
    
    # Handle command-line arguments if needed
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Graphiti MCP Server - stdio wrapper for Docker deployment")
        print("Usage: python mcp_stdio_wrapper.py [--transport stdio]")
        print("\nThis wrapper ensures proper stdio transport for Claude Code integration")
        sys.exit(0)
    
    # Default to stdio transport (ignore other transport args for Docker deployment)
    if "--transport" in sys.argv:
        transport_idx = sys.argv.index("--transport")
        if transport_idx + 1 < len(sys.argv):
            transport = sys.argv[transport_idx + 1]
            if transport != "stdio":
                logger.warning(f"Ignoring transport '{transport}', using stdio for Docker deployment")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)