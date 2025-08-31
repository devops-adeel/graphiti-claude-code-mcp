#!/usr/bin/env python3
"""Quick test of Neo4j migration for graphiti_memory.py"""

import asyncio
import logging
from graphiti_memory import get_shared_memory

logging.basicConfig(level=logging.INFO)


async def test_memory():
    """Test the memory connection with Neo4j"""
    try:
        print("Testing graphiti_memory.py with Neo4j...")
        memory = await get_shared_memory()
        print("✅ Memory initialized successfully with Neo4j!")

        # Test adding a memory
        result = await memory.add_memory(
            {"test": "Neo4j migration test", "type": "validation"}, source="test_script"
        )
        print(f"✅ Memory added: {result}")

        # Force flush to ensure it's saved
        await memory.force_flush()
        print("✅ Memory flushed to Neo4j")

        # Test search
        results = await memory.search_with_temporal_weight("Neo4j migration")
        print(f"✅ Search returned {len(results)} results")

        await memory.close()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_memory())
