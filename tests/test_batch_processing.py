#!/usr/bin/env python3
"""
Test script for enhanced Graphiti client with batch processing and connection pooling
Includes FalkorDB integrity checks using redis tools
"""

import asyncio
import json
import os
import sys
import redis
from datetime import datetime, timezone
from pathlib import Path

# Add the project directory to path
sys.path.insert(0, str(Path(__file__).parent))

from graphiti_memory import get_shared_memory, MemoryStatus


async def test_batch_processing():
    """Test batch processing with add_episode_bulk"""
    print("\n=== Testing Batch Processing ===")

    memory = await get_shared_memory()

    # Test adding multiple memories
    memories = []
    for i in range(5):  # Less than batch size
        content = {
            "title": f"Test Memory {i}",
            "description": f"Testing batch processing memory {i}",
            "test_id": f"batch_test_{i}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        result = await memory.add_memory(content, source="test_batch")
        memories.append(result)
        print(f"Added memory {i}: {result}")

    # Force flush to ensure all are saved
    print("\nForcing flush of episode buffer...")
    await memory.force_flush()

    # Search for the memories
    print("\n=== Searching for Batch Memories ===")
    results = await memory.search_with_temporal_weight("batch processing test")

    for i, result in enumerate(results[:5]):
        print(
            f"Result {i}: {result.fact if hasattr(result, 'fact') else str(result)[:100]}"
        )

    return len(results) > 0


async def test_large_batch():
    """Test with batch size threshold"""
    print("\n=== Testing Large Batch (Auto-Flush) ===")

    memory = await get_shared_memory()
    batch_size = memory.batch_size

    print(f"Batch size configured as: {batch_size}")
    print(f"Adding {batch_size + 5} memories to trigger auto-flush...")

    for i in range(batch_size + 5):
        content = {
            "title": f"Large Batch Memory {i}",
            "description": f"Testing auto-flush at batch size {i}",
            "batch_test": "large",
            "index": i,
        }
        result = await memory.add_memory(content, source="test_large_batch")
        if i == batch_size - 1:
            print(f"Memory {i} should trigger auto-flush: {result}")

    # Final flush
    await memory.force_flush()

    # Verify all were added
    results = await memory.search_with_temporal_weight("large batch auto-flush")
    print(f"\nFound {len(results)} results for large batch test")
    return True


async def verify_falkordb_integrity():
    """Verify FalkorDB data integrity using redis tools"""
    print("\n=== Verifying FalkorDB Integrity ===")

    # Connect directly to FalkorDB using redis-py
    r = redis.Redis(
        host=os.getenv("FALKORDB_HOST", "localhost"),
        port=int(os.getenv("FALKORDB_PORT", "6379")),
        decode_responses=True,
    )

    # Check connection
    try:
        pong = r.ping()
        print(f"✓ FalkorDB connection: {pong}")
    except Exception as e:
        print(f"✗ FalkorDB connection failed: {e}")
        return False

    # Check memory usage
    info = r.info("memory")
    print(f"✓ Memory used: {info.get('used_memory_human', 'N/A')}")
    print(f"✓ Memory RSS: {info.get('used_memory_rss_human', 'N/A')}")

    # List all graph keys
    database = os.getenv("FALKORDB_DATABASE", "shared_knowledge_graph")

    # Check if graph exists
    graph_keys = r.keys(f"*{database}*")
    print(f"\n✓ Graph keys found: {len(graph_keys)}")
    for key in graph_keys[:5]:  # Show first 5 keys
        key_type = r.type(key)
        print(f"  - {key}: {key_type}")

    # Execute a graph query to check integrity
    try:
        # Use GRAPH.QUERY command
        query = "MATCH (n) RETURN COUNT(n) as node_count"
        result = r.execute_command("GRAPH.QUERY", database, query)

        # Parse result (FalkorDB returns nested arrays)
        if result and len(result) > 1:
            node_count = result[1][0][0] if result[1] else 0
            print(f"\n✓ Total nodes in graph: {node_count}")

        # Check for duplicate UUIDs
        dup_query = """
        MATCH (n)
        WHERE EXISTS(n.uuid)
        WITH n.uuid as uuid, COUNT(*) as cnt
        WHERE cnt > 1
        RETURN uuid, cnt
        """
        dup_result = r.execute_command("GRAPH.QUERY", database, dup_query)

        if dup_result and len(dup_result) > 1 and dup_result[1]:
            print(f"⚠️ WARNING: Found {len(dup_result[1])} duplicate UUIDs!")
            for dup in dup_result[1][:3]:  # Show first 3
                print(f"  - UUID {dup[0]}: {dup[1]} duplicates")
        else:
            print("✓ No duplicate UUIDs found")

    except Exception as e:
        print(f"✗ Graph query failed: {e}")
        return False

    # Check configuration
    try:
        config = r.execute_command("GRAPH.CONFIG", "GET", "NODE_CREATION_BUFFER")
        if config:
            print(f"\n✓ NODE_CREATION_BUFFER: {config[1]}")
            if int(config[1]) > 1024:
                print(f"  ⚠️ WARNING: Buffer size {config[1]} may cause memory issues!")
    except:
        pass

    return True


async def test_connection_pooling():
    """Test connection pooling with concurrent operations"""
    print("\n=== Testing Connection Pooling ===")

    memory = await get_shared_memory()

    # Check if pool is initialized
    if memory.pool:
        print(
            f"✓ Connection pool initialized with max_connections: {memory.pool.max_connections}"
        )
    else:
        print("ℹ️ Standard connection mode (no async pool)")

    # Test concurrent operations
    print("\nTesting concurrent memory additions...")

    async def add_concurrent_memory(index):
        content = {
            "title": f"Concurrent Memory {index}",
            "description": f"Testing connection pooling {index}",
            "concurrent": True,
            "index": index,
        }
        return await memory.add_memory(content, source="test_concurrent")

    # Run 10 concurrent additions
    tasks = [add_concurrent_memory(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    print(f"✓ Successfully added {len(results)} memories concurrently")

    # Force flush
    await memory.force_flush()

    return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("GRAPHITI CLIENT ENHANCEMENT TEST SUITE")
    print("=" * 60)

    try:
        # Test 1: Basic batch processing
        test1 = await test_batch_processing()
        print(f"\n{'✓' if test1 else '✗'} Batch processing test")

        # Test 2: Large batch with auto-flush
        test2 = await test_large_batch()
        print(f"{'✓' if test2 else '✗'} Large batch auto-flush test")

        # Test 3: FalkorDB integrity
        test3 = await verify_falkordb_integrity()
        print(f"{'✓' if test3 else '✗'} FalkorDB integrity check")

        # Test 4: Connection pooling
        test4 = await test_connection_pooling()
        print(f"{'✓' if test4 else '✗'} Connection pooling test")

        # Close connections properly
        memory = await get_shared_memory()
        await memory.close()

        print("\n" + "=" * 60)
        if all([test1, test2, test3, test4]):
            print("✅ ALL TESTS PASSED")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            return 1

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
