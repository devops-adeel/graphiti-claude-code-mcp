#!/usr/bin/env python3
"""Simple test to check if memory operations work"""

import asyncio
import os

# Set NO_PROXY to ensure localhost connections bypass any proxy
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"

# Set environment variables
os.environ["TIKTOKEN_CACHE_DIR"] = "/tmp/.tiktoken_cache"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"
os.environ["OLLAMA_EMBEDDING_MODEL"] = "mxbai-embed-large"
os.environ["OLLAMA_EMBEDDING_DIM"] = "1024"
os.environ["USE_OLLAMA"] = "true"
os.environ["OLLAMA_MODEL"] = "llama3.2:3b"


async def test_simple():
    """Simple test without capture"""

    print("🔄 Loading memory system...")
    from graphiti_memory import get_shared_memory

    memory = await get_shared_memory()
    print(f"✅ Memory connected to group: {memory.group_id}")

    # Just do a simple search without capture
    print("\n🔍 Searching memory...")
    results = await memory.search_with_temporal_weight("docker environment variables")

    if results:
        print(f"✅ Found {len(results)} results")
        for i, result in enumerate(results[:3], 1):
            if "node" in result:
                node = result["node"]
                print(f"   {i}. {node.get('name', 'N/A')}")
    else:
        print("⚠️  No results found (this is OK if memory is empty)")

    print("\n✅ Test completed!")
    return True


if __name__ == "__main__":
    asyncio.run(test_simple())
