#!/usr/bin/env python3
"""
Test with OpenAIGenericClient which uses regular chat completions (Ollama-compatible)
"""

import asyncio
from datetime import datetime, timezone
from neo4j import AsyncGraphDatabase


async def test_with_generic_client():
    print("\n" + "=" * 60)
    print("TEST WITH OpenAIGenericClient (OLLAMA COMPATIBLE)")
    print("=" * 60)

    import sys

    print(f"\nPython version: {sys.version}")

    # Initialize Graphiti with Generic client
    print("\n1. Initializing Graphiti with OpenAIGenericClient...")
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
            api_key="abc",
            model="llama3.1:8b",  # Using larger model for better schema handling
            base_url="http://localhost:11434/v1",
        )

        # Use OpenAIGenericClient instead of OpenAIClient
        llm_client = OpenAIGenericClient(config=llm_config)

        graphiti = Graphiti(
            "bolt://localhost:7688",
            "neo4j",
            "password",
            llm_client=llm_client,  # Using generic client
            embedder=OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key="abc",
                    embedding_model="mxbai-embed-large",
                    embedding_dim=1024,
                    base_url="http://localhost:11434/v1",
                )
            ),
            cross_encoder=OpenAIRerankerClient(
                client=llm_client, config=llm_config  # Using same generic client
            ),
        )
        print("   ✅ Graphiti initialized with OpenAIGenericClient")
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
            print(f"\n   📊 Created {len(result.edges)} relationships")
            for i, edge in enumerate(result.edges[:3], 1):
                print(f"      {i}. {edge.fact[:60]}...")

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
            print(f"\n   🎉 Found {len(vector_indices)} vector indices!")
            for idx in vector_indices:
                print(f"      - {idx['name']}")
                print(f"        Labels: {idx['labelsOrTypes']}")
                print(f"        Properties: {idx['properties']}")
                config = idx.get("indexConfig", {})
                if config:
                    print(f"        Dimensions: {config.get('vector.dimensions')}")
        else:
            print("\n   ⚠️ No vector indices found")

        # Check embeddings on nodes
        result = await session.run(
            """
            MATCH (n)
            WHERE n.embedding IS NOT NULL
               OR n.name_embedding IS NOT NULL
            WITH labels(n)[0] as label,
                 n.name as name,
                 CASE
                    WHEN n.embedding IS NOT NULL THEN 'embedding'
                    WHEN n.name_embedding IS NOT NULL THEN 'name_embedding'
                 END as embed_type,
                 CASE
                    WHEN n.embedding IS NOT NULL THEN size(n.embedding)
                    WHEN n.name_embedding IS NOT NULL THEN size(n.name_embedding)
                 END as dim
            RETURN label, name, embed_type, dim
            ORDER BY label
            LIMIT 10
        """
        )
        embeddings = await result.data()

        if embeddings:
            print("\n   ✅ Node embeddings found:")
            for emb in embeddings:
                print(
                    f"      - {emb['label']}: {emb['name']} has {emb['embed_type']} [{emb['dim']} dims]"
                )
        else:
            print("\n   ❌ No node embeddings found")

        # Check embeddings on edges
        result = await session.run(
            """
            MATCH ()-[r:RELATES_TO]->()
            WHERE r.fact_embedding IS NOT NULL
            RETURN r.fact as fact, size(r.fact_embedding) as dim
            LIMIT 5
        """
        )
        edge_embeddings = await result.data()

        if edge_embeddings:
            print("\n   ✅ Edge embeddings found:")
            for edge in edge_embeddings:
                print(f"      - '{edge['fact'][:50]}...' [{edge['dim']} dims]")
        else:
            print("\n   ❌ No edge embeddings found")

    # Try a search
    print("\n5. Testing vector similarity search...")
    try:
        results = await graphiti.search("search feature", num_results=5)
        if results:
            print(f"   ✅ Search returned {len(results)} results:")
            for i, result in enumerate(results[:3], 1):
                print(f"      {i}. {result.fact[:60]}...")
        else:
            print("   ⚠️ No search results")
    except Exception as e:
        print(f"   ❌ Search failed: {e}")

    await driver.close()

    print("\n" + "=" * 60)
    print("CONCLUSIONS:")
    print("- OpenAIGenericClient works with Ollama")
    print("- Check if embeddings were generated")
    print("- Check if vector indices exist")
    print("- Check if search works")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_with_generic_client())
