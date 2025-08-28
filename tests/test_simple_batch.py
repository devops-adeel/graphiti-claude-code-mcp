#!/usr/bin/env python3
"""
Simple test for batch processing with proper port configuration
"""

import asyncio
import os
import sys
from pathlib import Path

# Set correct FalkorDB port
os.environ["FALKORDB_PORT"] = "6379"
os.environ["FALKORDB_HOST"] = "localhost"

sys.path.insert(0, str(Path(__file__).parent))

from graphiti_memory import SharedMemory


async def test_simple():
    """Simple test of batch processing"""
    print("Testing batch processing with FalkorDB on port 6379...")

    # Create memory instance directly
    memory = SharedMemory()

    # Print configuration
    print(f"Configured with:")
    print(f"  - Host: {os.getenv('FALKORDB_HOST', 'localhost')}")
    print(f"  - Port: {os.getenv('FALKORDB_PORT', '6379')}")
    print(f"  - Database: {memory.database}")
    print(f"  - Batch size: {memory.batch_size}")

    try:
        # Initialize
        await memory.initialize()
        print("✓ Connected to FalkorDB")

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
