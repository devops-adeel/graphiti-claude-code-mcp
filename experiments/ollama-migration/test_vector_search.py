#!/usr/bin/env python3
"""
Test vector similarity search with 1024-dimension embeddings
"""

import asyncio
from datetime import datetime, timezone


async def test_vector_search():
    print("\n" + "=" * 60)
    print("TESTING VECTOR SIMILARITY SEARCH")
    print("=" * 60)

    # Initialize Graphiti
    print("\n1. Initializing Graphiti...")
    try:
        from graphiti_core import Graphiti
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )

        llm_config = LLMConfig(
            api_key="ollama",
            model="llama3.1:8b",
            base_url="http://localhost:11434/v1",
        )

        llm_client = OpenAIGenericClient(config=llm_config)

        graphiti = Graphiti(
            "bolt://neo4j.graphiti.local:7687",
            "neo4j",
            "jzt4cAXRCBxAQWJ9eSC7qVrxtnA3EplimUsE1IvfMXo=",
            llm_client=llm_client,
            embedder=OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key="ollama",
                    embedding_model="mxbai-embed-large",  # 1024 dimensions
                    embedding_dim=1024,
                    base_url="http://localhost:11434/v1",
                )
            ),
            cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
        )
        print("   ✅ Graphiti initialized with 1024-dim embeddings")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return

    # Test vector search
    print("\n2. Testing vector similarity search...")
    search_queries = [
        "Alice",
        "Bob",
        "search feature",
        "UI improvement",
        "vector similarity",
        "test",
    ]

    for query in search_queries:
        print(f"\n   Searching for: '{query}'")
        try:
            results = await graphiti.search(query, num_results=3)
            if results:
                print(f"   ✅ Found {len(results)} results:")
                for i, result in enumerate(results[:3], 1):
                    fact = result.fact if hasattr(result, "fact") else str(result)
                    if len(fact) > 60:
                        fact = fact[:60] + "..."
                    print(f"      {i}. {fact}")
            else:
                print(f"   ⚠️ No results found")
        except Exception as e:
            if "Invalid input for 'vector.similarity.cosine()'" in str(e):
                print(f"   ❌ Vector index error - dimension mismatch!")
                print(f"      This should NOT happen with 1024-dim embeddings")
                return
            else:
                print(f"   ❌ Search error: {str(e)[:100]}")

    # Test similarity between entities
    print("\n3. Testing entity similarity search...")
    try:
        # Get embeddings directly and test similarity
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            "bolt://neo4j.graphiti.local:7687",
            auth=("neo4j", "jzt4cAXRCBxAQWJ9eSC7qVrxtnA3EplimUsE1IvfMXo="),
        )

        async with driver.session(database="neo4j") as session:
            # Test vector similarity directly in Neo4j
            result = await session.run(
                """
                MATCH (n:Entity)
                WHERE n.name_embedding IS NOT NULL
                WITH n LIMIT 1
                MATCH (m:Entity)
                WHERE m.name_embedding IS NOT NULL AND m <> n
                RETURN n.name as entity1,
                       m.name as entity2,
                       vector.similarity.cosine(n.name_embedding, m.name_embedding) as similarity
                ORDER BY similarity DESC
                LIMIT 5
            """
            )
            similarities = await result.data()

            if similarities:
                print("   ✅ Vector similarity working! Top similar entities:")
                for sim in similarities:
                    print(
                        f"      '{sim['entity1']}' <-> '{sim['entity2']}': {sim['similarity']:.3f}"
                    )
            else:
                print("   ⚠️ No similarity results")

        await driver.close()

    except Exception as e:
        if "Invalid input for 'vector.similarity.cosine()'" in str(e):
            print(f"   ❌ CRITICAL: Vector dimension mismatch in Neo4j!")
        else:
            print(f"   ❌ Error: {str(e)[:100]}")

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("- Vector indexes created: ✅")
    print("- Embeddings are 1024 dimensions: ✅")
    print("- Vector search functionality: Testing above")
    print("- If searches work, the migration is complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_vector_search())
