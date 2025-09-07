#!/usr/bin/env ./venv/bin/python
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

# Ensure unbuffered output for Docker
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Load environment files
if Path("/.dockerenv").exists():  # Running in Docker
    # In Docker, load environment files
    load_dotenv(".env.graphiti")
    load_dotenv(".env", override=True)  # Override with mounted .env for OPENAI_API_KEY

    # OrbStack uses custom domains for container-to-container communication
    # AI-CONTEXT: Neo4j graph database via OrbStack domain
    # Connection: bolt://neo4j.graphiti.local:7687
    # Database: "neo4j" (Community Edition requirement)
    logger_msg = "Running in Docker with OrbStack networking"

    # Verify Neo4j configuration
    neo4j_host = os.getenv("NEO4J_HOST")
    neo4j_port = os.getenv("NEO4J_PORT")

    # Log configuration for debugging
    sys.stderr.write(f"Neo4j configuration: {neo4j_host}:{neo4j_port}\n")
    sys.stderr.flush()
else:
    # Local development
    load_dotenv(".env.graphiti")
    load_dotenv(Path.home() / ".env", override=True)
    logger_msg = "Running locally"

# Configure logging for MCP
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ],  # Log to stderr to keep stdout clean for MCP
)
logger = logging.getLogger(__name__)


async def main():
    """Run the MCP server with stdio transport"""
    try:
        # Import after environment is configured
        import mcp.server.stdio
        from mcp.server.models import InitializationOptions
        from mcp.server import NotificationOptions

        # Test Neo4j connectivity before starting server
        if Path("/.dockerenv").exists():
            logger.info("Testing Neo4j connectivity...")
            try:
                from neo4j import GraphDatabase

                uri = f"bolt://{os.getenv('NEO4J_HOST')}:{os.getenv('NEO4J_PORT')}"
                driver = GraphDatabase.driver(
                    uri,
                    auth=(
                        os.getenv("NEO4J_USER"),
                        os.getenv("NEO4J_PASSWORD"),
                    ),
                )
                # Quick connectivity test
                driver.verify_connectivity()
                driver.close()
                logger.info("✅ Neo4j connection successful")
            except Exception as e:
                logger.warning(f"⚠️ Neo4j connection test failed: {e}")
                logger.warning(
                    "Server will start but may have issues with memory operations"
                )

        # Import our server and instructions (this will use the configured environment)
        from mcp_server import server, INSTRUCTIONS

        logger.info("Starting Graphiti MCP Server (stdio transport)")
        logger.info(logger_msg)
        logger.info(f"Neo4j Host: {os.getenv('NEO4J_HOST')}")
        logger.info(f"Neo4j Port: {os.getenv('NEO4J_PORT')}")
        logger.info(f"Group ID: {os.getenv('GRAPHITI_GROUP_ID')}")

        # Flush logs before starting stdio server
        sys.stderr.flush()

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
                    instructions=INSTRUCTIONS,
                ),
            )
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure all dependencies are installed")
        sys.stderr.flush()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Server error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.stderr.flush()
        sys.exit(1)


if __name__ == "__main__":
    # Ensure unbuffered output for Docker
    os.environ["PYTHONUNBUFFERED"] = "1"

    # Handle command-line arguments if needed
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Graphiti MCP Server - stdio wrapper for Docker deployment")
        print("Usage: python mcp_stdio_wrapper.py [--transport stdio]")
        print(
            "\nThis wrapper ensures proper stdio transport for Claude Code integration"
        )
        sys.exit(0)

    # Default to stdio transport (ignore other transport args for Docker deployment)
    if "--transport" in sys.argv:
        transport_idx = sys.argv.index("--transport")
        if transport_idx + 1 < len(sys.argv):
            transport = sys.argv[transport_idx + 1]
            if transport != "stdio":
                logger.warning(
                    f"Ignoring transport '{transport}', using stdio for Docker deployment"
                )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
