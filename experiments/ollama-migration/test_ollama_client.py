#!/usr/bin/env python3
"""
Test Graphiti with custom Ollama client that handles JSON schemas correctly
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from neo4j import AsyncGraphDatabase

# Add current directory to path to import our custom client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ollama_graphiti_client import OllamaGraphitiClient


async def test_with_custom_client():
    print("\n" + "=" * 60)
    print("TEST WITH CUSTOM OLLAMA CLIENT")
    print("=" * 60)

    print(f"\nPython version: {sys.version}")

    # Initialize Graphiti with our custom client
    print("\n1. Initializing Graphiti with custom OllamaGraphitiClient...")
    try:
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )

        llm_config = LLMConfig(
            api_key="abc",
            model="llama3.1:8b",
            base_url="http://localhost:11434/v1",
        )

        # Use our custom Ollama client
        llm_client = OllamaGraphitiClient(config=llm_config)

        graphiti = Graphiti(
            "bolt://localhost:7688",
            "neo4j",
            "password",
            llm_client=llm_client,  # Using custom client
            embedder=OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key="abc",
                    embedding_model="mxbai-embed-large",
                    embedding_dim=1024,
                    base_url="http://localhost:11434/v1",
                )
            ),
            cross_encoder=OpenAIRerankerClient(
                client=llm_client, config=llm_config  # Using custom client
            ),
        )
        print("   ✅ Graphiti initialized with custom OllamaGraphitiClient")
    except Exception as e:
        print(f"   ❌ Init error: {e}")
        return

    # Build indices
    print("\n2. Building indices...")
    try:
        await graphiti.build_indices_and_constraints()
        print("   ✅ Indices built")
    except Exception as e:
        print(f"   ⚠️ Indices may already exist: {e}")

    # Add episode
    print("\n3. Adding episode...")
    try:
        result = await graphiti.add_episode(
            name="Test Episode",
            episode_body="Alice really likes the new search feature. Bob thinks the UI needs improvement. The search uses advanced vector similarity algorithms.",
            source=EpisodeType.text,
            source_description="User feedback",
            reference_time=datetime.now(timezone.utc),
        )
        print("   ✅ Episode added successfully!")

        if hasattr(result, "nodes") and result.nodes:
            print(f"\n   📊 Extracted {len(result.nodes)} entities:")
            for i, node in enumerate(result.nodes[:5], 1):
                print(f"      {i}. {node.name} ({getattr(node, 'label', 'Entity')})")

        if hasattr(result, "edges") and result.edges:
            print(f"\n   📊 Created {len(result.edges)} relationships:")
            for i, edge in enumerate(result.edges[:3], 1):
                print(f"      {i}. {edge.fact[:60]}...")

    except Exception as e:
        print(f"   ❌ Error adding episode: {e}")
        import traceback

        traceback.print_exc()
        return

    # Check database state
    print("\n4. Checking database state...")
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688", auth=("neo4j", "password")
    )

    async with driver.session(database="neo4j") as session:
        # Check vector indices
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        vector_indices = await result.data()

        if vector_indices:
            print(f"\n   🎉 Found {len(vector_indices)} vector indices!")
            for idx in vector_indices:
                print(f"      - {idx['name']}")
                print(
                    f"        Dimensions: {idx.get('indexConfig', {}).get('vector.dimensions')}"
                )
        else:
            print("\n   ⚠️ No vector indices found - will need to create manually")

        # Check embeddings
        result = await session.run(
            """
            MATCH (n)
            WHERE n.embedding IS NOT NULL
               OR n.name_embedding IS NOT NULL
            RETURN labels(n)[0] as label,
                   COUNT(*) as count,
                   CASE
                      WHEN n.embedding IS NOT NULL THEN size(n.embedding)
                      WHEN n.name_embedding IS NOT NULL THEN size(n.name_embedding)
                   END as dim
            ORDER BY label
        """
        )
        embeddings = await result.data()

        if embeddings:
            print("\n   ✅ Embeddings generated:")
            for emb in embeddings:
                print(
                    f"      - {emb['label']}: {emb['count']} nodes with {emb['dim']} dims"
                )
        else:
            print("\n   ❌ No embeddings found")

    # Try a search (will fail without vector indexes)
    print("\n5. Testing vector similarity search...")
    try:
        results = await graphiti.search("search feature", num_results=5)
        if results:
            print(f"   ✅ Search returned {len(results)} results")
        else:
            print("   ⚠️ No search results")
    except Exception as e:
        if "Invalid input for 'vector.similarity.cosine()'" in str(e):
            print(f"   ⚠️ Expected error - vector indexes need to be created manually")
        else:
            print(f"   ❌ Unexpected error: {e}")

    await driver.close()

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("1. If entities were extracted, the custom client works!")
    print("2. Create vector indexes manually (see create_vector_indexes.py)")
    print("3. Then search will work")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_with_custom_client())
