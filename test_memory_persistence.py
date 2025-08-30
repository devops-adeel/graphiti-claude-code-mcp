#!/usr/bin/env python3
"""
Test script to verify memory persistence is working correctly.
This tests the complete capture → storage → retrieval pipeline.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from graphiti_memory import get_shared_memory
from capture import get_pattern_capture


async def test_memory_persistence():
    """Test that memories are actually persisted to FalkorDB"""
    print("=" * 60)
    print("Memory Persistence Test")
    print("=" * 60)

    # Initialize components
    print("\n1. Initializing memory and capture systems...")
    memory = await get_shared_memory()
    capture = await get_pattern_capture()
    print("   ✓ Memory system initialized")
    print(f"   ✓ Group ID: {memory.group_id}")
    print(f"   ✓ Batch size: {memory.batch_size}")

    # Create unique test data
    timestamp = datetime.now().isoformat()
    test_error = f"Test error at {timestamp}"
    test_solution = f"Test solution for persistence verification"

    print(f"\n2. Capturing test memory...")
    print(f"   Error: {test_error}")
    print(f"   Solution: {test_solution}")

    # Capture a solution
    memory_id = await capture.capture_deployment_solution(
        error=test_error,
        solution=test_solution,
        context={"test": True, "timestamp": timestamp},
    )

    print(f"   ✓ Captured with ID: {memory_id}")

    # Check if it's a pending ID or real ID
    if memory_id.startswith("pending_"):
        print("   ⚠️  WARNING: Got pending ID - buffer may not have flushed!")
    else:
        print("   ✓ Got real UUID - memory should be persisted")

    # Small delay to ensure persistence
    await asyncio.sleep(1)

    # Search for the memory
    print(f"\n3. Searching for captured memory...")
    results = await memory.search_with_temporal_weight(
        test_error, include_historical=True
    )

    if results:
        print(f"   ✓ Found {len(results)} results!")
        for i, result in enumerate(results[:3], 1):
            print(f"\n   Result {i}:")
            if hasattr(result, "metadata"):
                print(f"     Error: {result.metadata.get('error', 'N/A')[:50]}...")
                print(
                    f"     Solution: {result.metadata.get('solution', 'N/A')[:50]}..."
                )
                print(f"     Score: {result.score:.3f}")
            elif hasattr(result, "fact"):
                print(f"     Fact: {result.fact[:100]}...")
                print(f"     Score: {result.score:.3f}")
    else:
        print("   ✗ No results found - memory not persisted!")

    # Try a broader search
    print(f"\n4. Trying broader search for 'Test'...")
    broad_results = await memory.search_with_temporal_weight(
        "Test", include_historical=True
    )

    if broad_results:
        print(f"   ✓ Found {len(broad_results)} results with 'Test'")
    else:
        print("   ✗ Still no results - persistence issue confirmed")

    # Force flush explicitly
    print(f"\n5. Forcing flush and retrying...")
    await memory.force_flush()
    await asyncio.sleep(1)

    final_results = await memory.search_with_temporal_weight(
        test_error, include_historical=True
    )

    if final_results:
        print(f"   ✓ After force flush: Found {len(final_results)} results")
    else:
        print("   ✗ Even after force flush: No results")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    if results or final_results:
        print("✅ SUCCESS: Memory persistence is working!")
        print(f"   - Batch size: {memory.batch_size}")
        print(f"   - Memory ID: {memory_id}")
        print(f"   - Results found: {len(results or final_results)}")
    else:
        print("❌ FAILURE: Memories are not being persisted")
        print("\nPossible issues:")
        print("   1. Buffer not flushing (check batch_size)")
        print("   2. FalkorDB connection issues")
        print("   3. Search query escaping problems")
        print("\nDebugging steps:")
        print("   1. Check docker logs: docker logs laughing_jones")
        print("   2. Query FalkorDB directly")
        print("   3. Verify GRAPHITI_BATCH_SIZE=5 in .env.graphiti")

    print("=" * 60)

    # Close connection
    await memory.close()

    return bool(results or final_results)


if __name__ == "__main__":
    success = asyncio.run(test_memory_persistence())
    sys.exit(0 if success else 1)
