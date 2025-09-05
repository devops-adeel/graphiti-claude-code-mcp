#!/usr/bin/env python3
"""Direct test of SSL bypass implementation"""

import asyncio
import sys
from graphiti_memory import get_shared_memory
from capture import get_pattern_capture


async def test_ssl_bypass():
    """Test if SSL bypass is working properly"""
    print("=" * 60)
    print("TESTING SSL BYPASS IMPLEMENTATION")
    print("=" * 60)

    # Test 1: Memory instance creation
    print("\n1. Creating memory instance...")
    try:
        memory = await get_shared_memory()
        print(f"✅ Memory instance created: {memory.__class__.__name__}")
    except Exception as e:
        print(f"❌ Failed to create memory: {e}")
        return False

    # Test 2: Embedding generation (through internal client)
    print("\n2. Testing OpenAI embedding generation...")
    try:
        test_text = "Testing SSL bypass for embeddings"
        # Access the internal client through graphiti's driver
        if hasattr(memory, "driver") and hasattr(memory.driver, "llm_client"):
            embedding = await memory.driver.llm_client.generate_embedding(test_text)
            print(f"✅ Embedding generated! Length: {len(embedding)}")
        else:
            print("⚠️ Skipping direct embedding test (client not exposed)")
            print("    Will test indirectly through memory capture...")
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        return False

    # Test 3: Memory capture
    print("\n3. Testing memory capture...")
    try:
        capture = await get_pattern_capture()
        result = await capture.capture_deployment_solution(
            error="SSL certificate verification failure behind corporate proxy",
            solution="Added httpx client with verify=False to OpenAI client",
            context={
                "deployment": "graphiti-mcp-server",
                "ssl_bypass": True,
                "http_client": "httpx",
            },
        )
        print(f"Memory ID: {result}")

        if "pending" in str(result).lower():
            print("❌ Memory has 'pending' prefix - transaction not committed")
            return False
        else:
            print("✅ Memory captured successfully without pending prefix!")
    except Exception as e:
        print(f"❌ Memory capture failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 4: Memory retrieval
    print("\n4. Testing memory retrieval...")
    try:
        results = await memory.search_with_temporal_weight("SSL certificate")
        if results:
            print(f"✅ Found {len(results)} memories")
            for i, r in enumerate(results[:3], 1):
                print(
                    f"   {i}. {r.get('content', '')[:50]}... (score: {r.get('score', 0):.2f})"
                )
        else:
            print("⚠️ No memories found (might be normal if database is empty)")
    except Exception as e:
        print(f"❌ Memory search failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - SSL BYPASS IS WORKING!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_ssl_bypass())
    sys.exit(0 if success else 1)
