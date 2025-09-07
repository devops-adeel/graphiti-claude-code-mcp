#!/usr/bin/env python3
"""
Simple test for batch processing with proper port configuration
"""

import asyncio
import os
import sys
from pathlib import Path

# Set correct Neo4j port
os.environ["NEO4J_PORT"] = "7687"
os.environ["NEO4J_HOST"] = "neo4j.graphiti.local"

sys.path.insert(0, str(Path(__file__).parent))

from graphiti_memory import SharedMemory


async def test_simple():
    """Simple test of batch processing"""
    print("Testing batch processing with Neo4j on port 7687...")

    # Create memory instance directly
    memory = SharedMemory()

    # Print configuration
    print(f"Configured with:")
    print(f"  - Host: {os.getenv('NEO4J_HOST')}")
    print(f"  - Port: {os.getenv('NEO4J_PORT')}")
    print(f"  - Database: {memory.database}")
    print(f"  - Batch size: {memory.batch_size}")

    try:
        # Initialize
        await memory.initialize()
        print("✓ Connected to Neo4j")

        # Test adding a single memory
        content = {"title": "Test Memory", "description": "Testing batch processing"}

        result = await memory.add_memory(content, source="test")
        print(f"✓ Added memory to buffer: {result}")

        # Force flush
        await memory.force_flush()
        print("✓ Flushed buffer successfully")

        # Clean close
        await memory.close()
        print("✓ Closed connection")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_simple())
    sys.exit(0 if result else 1)
