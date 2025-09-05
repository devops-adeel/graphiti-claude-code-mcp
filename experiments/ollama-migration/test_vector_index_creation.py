#!/usr/bin/env python3
"""
Minimal test to verify 1024-dimension vector indexes are created automatically
"""

import asyncio
from datetime import datetime, timezone
from neo4j import AsyncGraphDatabase


async def test_vector_index_creation():
    print("\n" + "=" * 60)
    print("TESTING VECTOR INDEX CREATION WITH 1024 DIMENSIONS")
    print("=" * 60)

    # 1. Check initial state
    print("\n1. Checking initial Neo4j state...")
    driver = AsyncGraphDatabase.driver(
        "bolt://neo4j.graphiti.local:7687",
        auth=("neo4j", "jzt4cAXRCBxAQWJ9eSC7qVrxtnA3EplimUsE1IvfMXo="),
    )

    async with driver.session(database="neo4j") as session:
        # Check existing vector indexes
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        initial_indices = await result.data()

        if initial_indices:
            print(f"   Found {len(initial_indices)} existing vector indexes:")
            for idx in initial_indices:
                dims = idx.get("indexConfig", {}).get("vector.dimensions", "unknown")
                print(f"      - {idx['name']} ({dims} dimensions)")
        else:
            print("   No vector indexes found initially")

    # 2. Initialize Graphiti with 1024-dim embeddings
    print("\n2. Initializing Graphiti with 1024-dimension embeddings...")
    try:
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType
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
            temperature=0.1,  # Lower for consistency
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
                    embedding_dim=1024,  # Matching dimensions
                    base_url="http://localhost:11434/v1",
                )
            ),
            cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
        )
        print("   ✅ Graphiti initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        await driver.close()
        return

    # 3. Build indices
    print("\n3. Building standard indices...")
    try:
        await graphiti.build_indices_and_constraints()
        print("   ✅ Standard indices built")
    except Exception as e:
        print(f"   ⚠️ Indices may exist: {e}")

    # 4. Try to trigger vector index creation with a simple episode
    print("\n4. Adding minimal episode to trigger vector index creation...")
    try:
        # Use the simplest possible episode to minimize LLM confusion
        result = await graphiti.add_episode(
            name="Simple Test",
            episode_body="Test.",  # Extremely simple to minimize extraction errors
            source=EpisodeType.text,
            source_description="Test",
            reference_time=datetime.now(timezone.utc),
        )
        print("   ✅ Episode added (may have extraction errors, but that's okay)")
    except Exception as e:
        print(f"   ⚠️ Episode failed (expected): {str(e)[:100]}...")
        print("   This is okay - we're just checking if vector indexes were created")

    # 5. Check if vector indexes were created
    print("\n5. Checking for newly created vector indexes...")
    async with driver.session(database="neo4j") as session:
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        final_indices = await result.data()

        if final_indices:
            print(f"\n   🎉 Found {len(final_indices)} vector indexes:")
            for idx in final_indices:
                dims = idx.get("indexConfig", {}).get("vector.dimensions", "unknown")
                state = idx["state"]
                print(f"      - {idx['name']}")
                print(f"        State: {state}")
                print(f"        Dimensions: {dims}")
                print(f"        Labels/Types: {idx.get('labelsOrTypes', [])}")
                print(f"        Properties: {idx.get('properties', [])}")

                if dims == 1024:
                    print(f"        ✅ Correctly configured for 1024 dimensions!")
                else:
                    print(f"        ❌ Wrong dimensions: {dims}")
        else:
            print("   ❌ No vector indexes were created")
            print("   Graphiti may need at least one successful entity/edge creation")

    # 6. Check if any embeddings were created
    print("\n6. Checking for created embeddings...")
    async with driver.session(database="neo4j") as session:
        # Check for any nodes with embeddings
        result = await session.run(
            """
            MATCH (n)
            WHERE n.embedding IS NOT NULL OR n.name_embedding IS NOT NULL
            RETURN labels(n)[0] as label, COUNT(*) as count
        """
        )
        embeddings = await result.data()

        if embeddings:
            print("   Embeddings found:")
            for emb in embeddings:
                print(f"      - {emb['label']}: {emb['count']} nodes")
        else:
            print("   No embeddings found (extraction may have failed)")

    await driver.close()

    print("\n" + "=" * 60)
    print("CONCLUSIONS:")
    print("- If vector indexes were created with 1024 dimensions: SUCCESS!")
    print("- If not, Graphiti needs successful entity extraction first")
    print("- Next step: Fix LLM extraction with better prompting")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_vector_index_creation())
