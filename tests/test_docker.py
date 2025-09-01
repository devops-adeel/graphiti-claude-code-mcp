#!/usr/bin/env python3
"""
Test batch processing in Docker environment
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from graphiti_memory import get_shared_memory


async def test_docker():
    """Test batch processing in Docker"""
    print("=" * 60)
    print("DOCKER BATCH PROCESSING TEST")
    print("=" * 60)

    # Get memory instance
    memory = await get_shared_memory()

    print(f"✓ Connected to Neo4j")
    print(f"  - Host: {os.getenv('NEO4J_HOST', 'neo4j.graphiti.local')}")
    print(f"  - Port: {os.getenv('NEO4J_PORT', '7687')}")
    print(f"  - Database: {memory.database}")
    print(f"  - Batch size: {memory.batch_size}")
    print(f"  - Group ID: {memory.group_id}")

    # Test batch processing
    print("\nTesting batch processing...")

    memories = []
    for i in range(3):
        content = {
            "title": f"Docker Test {i}",
            "description": f"Testing batch processing in Docker container {i}",
            "docker_test": True,
            "index": i,
        }
        result = await memory.add_memory(content, source="docker_test")
        memories.append(result)
        print(f"  Added memory {i}: {result}")

    # Force flush
    print("\nFlushing buffer...")
    await memory.force_flush()

    # Search for the memories
    print("\nSearching for Docker test memories...")
    results = await memory.search_with_temporal_weight("docker batch processing")
    print(f"  Found {len(results)} results")

    # Close
    await memory.close()

    print("\n" + "=" * 60)
    print("✅ DOCKER BATCH PROCESSING TEST PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_docker())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
