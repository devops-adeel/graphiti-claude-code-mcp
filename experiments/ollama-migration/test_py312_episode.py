#!/usr/bin/env python3
"""
Test with Python 3.12: Add episode and check for vector indices
"""

import asyncio
from datetime import datetime, timezone
from neo4j import AsyncGraphDatabase


async def test_with_py312():
    print("\n" + "=" * 60)
    print("PYTHON 3.12 TEST: ADD EPISODE WITH GRAPHITI")
    print("=" * 60)

    import sys

    print(f"\nPython version: {sys.version}")

    # Initialize Graphiti
    print("\n1. Initializing Graphiti...")
    try:
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_client import OpenAIClient
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )

        llm_config = LLMConfig(
            api_key="abc",
            model="llama3.2:3b",
            base_url="http://localhost:11434/v1",
        )

        graphiti = Graphiti(
            "bolt://localhost:7688",
            "neo4j",
            "password",
            llm_client=OpenAIClient(config=llm_config),
            embedder=OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key="abc",
                    embedding_model="nomic-embed-text",
                    embedding_dim=768,
                    base_url="http://localhost:11434/v1",
                )
            ),
            cross_encoder=OpenAIRerankerClient(
                client=OpenAIClient(config=llm_config), config=llm_config
            ),
        )
        print("   ✅ Graphiti initialized")
    except Exception as e:
        print(f"   ❌ Init error: {e}")
        return

    # Build indices (if not already done)
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
            episode_body="Alice likes the new search feature. Bob thinks the UI needs improvement.",
            source=EpisodeType.text,
            source_description="User feedback",
            reference_time=datetime.now(timezone.utc),
        )
        print("   ✅ Episode added successfully!")

        if hasattr(result, "nodes") and result.nodes:
            print(f"   📊 Extracted {len(result.nodes)} entities:")
            for node in result.nodes[:5]:
                print(f"      - {node.name}")

    except Exception as e:
        print(f"   ❌ Error adding episode: {e}")
        import traceback

        traceback.print_exc()
        return

    # Check results
    print("\n4. Checking database state...")
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688", auth=("neo4j", "password")
    )

    async with driver.session(database="neo4j") as session:
        # Check vector indices
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        vector_indices = await result.data()

        if vector_indices:
            print(f"   🎉 Found {len(vector_indices)} vector indices!")
            for idx in vector_indices:
                print(f"      - {idx['name']} on {idx['properties']}")
        else:
            print("   ⚠️ No vector indices found")

        # Check embeddings
        result = await session.run(
            """
            MATCH (n)
            WHERE n.embedding IS NOT NULL
               OR n.name_embedding IS NOT NULL
            RETURN labels(n)[0] as label,
                   count(n) as count,
                   CASE
                      WHEN n.embedding IS NOT NULL THEN size(n.embedding)
                      WHEN n.name_embedding IS NOT NULL THEN size(n.name_embedding)
                   END as dim
            ORDER BY label
        """
        )
        embeddings = await result.data()

        if embeddings:
            print("\n   ✅ Embeddings found:")
            for emb in embeddings:
                print(
                    f"      - {emb['label']}: {emb['count']} nodes with {emb['dim']}-dim embeddings"
                )
        else:
            print("   ❌ No embeddings found")

    await driver.close()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_with_py312())
