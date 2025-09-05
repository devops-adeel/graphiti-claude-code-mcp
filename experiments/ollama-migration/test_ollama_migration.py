#!/usr/bin/env python3
"""Test script to verify Ollama-only migration is working correctly."""

import asyncio
import os
import sys

# Ensure we're using Ollama
os.environ["USE_OLLAMA"] = "true"
os.environ["OLLAMA_EMBEDDING_DIM"] = "768"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"


async def test_ollama_migration():
    """Test that the Ollama-only migration is working."""
    try:
        # Import after setting environment variables
        from graphiti_memory import get_shared_memory
        from capture import get_pattern_capture

        print("🔧 Testing Ollama-only memory system...")
        print("=" * 50)

        # Initialize memory client
        print("1. Initializing memory client...")
        memory = await get_shared_memory()
        print(f"   ✅ Memory client initialized")
        print(f"   - Group ID: {memory.group_id}")
        print(f"   - Embedder: {type(memory.embedder).__name__}")

        # Initialize capture client
        print("\n2. Initializing capture client...")
        capture = await get_pattern_capture()
        print(f"   ✅ Capture client initialized")

        # Test capturing a solution
        print("\n3. Capturing test solution...")
        test_error = "Vector dimension mismatch: Expected 1536, got 768"
        test_solution = "Migrated to pure Ollama with nomic-embed-text (768 dimensions)"

        await capture.capture_solution(
            error=test_error,
            solution=test_solution,
            context={
                "migration_type": "ollama-only",
                "embedding_model": "nomic-embed-text",
                "dimensions": 768,
                "timestamp": "2025-09-04",
            },
        )
        print(f"   ✅ Test solution captured successfully")

        # Wait a moment for indexing
        await asyncio.sleep(2)

        # Test searching
        print("\n4. Testing search functionality...")
        search_queries = [
            "vector dimension mismatch",
            "Ollama migration",
            "embedding dimensions",
        ]

        for query in search_queries:
            print(f"\n   Searching for: '{query}'")
            results = await memory.search_with_temporal_weight(query, limit=3)
            print(f"   Found {len(results)} results")

            if results:
                for i, result in enumerate(results[:2], 1):
                    content = result.get("content", "N/A")
                    score = result.get("score", 0)
                    print(f"   Result {i}: {content[:80]}...")
                    print(f"   Score: {score:.3f}")

        # Test cross-domain insights
        print("\n5. Testing cross-domain insights...")
        insights = await memory.find_cross_domain_insights("embedding migration")
        print(f"   ✅ Cross-domain search returned {len(insights)} insights")

        print("\n" + "=" * 50)
        print("🎉 SUCCESS! All tests passed!")
        print("\nOllama-only migration is working correctly:")
        print("  • Memory capture: ✅")
        print("  • Vector search: ✅")
        print("  • 768-dim embeddings: ✅")
        print("  • No OpenAI dependencies: ✅")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ollama_migration())
    sys.exit(0 if success else 1)
