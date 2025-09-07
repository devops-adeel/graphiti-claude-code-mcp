#!/usr/bin/env python3
"""
Step 4: Add an episode and check if vector indices are created
Following: https://help.getzep.com/graphiti/core-concepts/adding-episodes
"""

import asyncio
from datetime import datetime, timezone
from neo4j import AsyncGraphDatabase
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient


async def add_episode_and_check():
    print("\n" + "=" * 60)
    print("STEP 4: ADD EPISODE AND CHECK FOR VECTOR INDICES")
    print("=" * 60)

    # Initialize Graphiti
    print("\n1. Initializing Graphiti...")
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
                embedding_model="mxbai-embed-large",
                embedding_dim=768,
                base_url="http://localhost:11434/v1",
            )
        ),
        cross_encoder=OpenAIRerankerClient(
            client=OpenAIClient(config=llm_config), config=llm_config
        ),
    )
    print("   ✅ Graphiti initialized")

    # Add episode (from official docs)
    print("\n2. Adding episode from official documentation...")
    try:
        result = await graphiti.add_episode(
            name="User Feedback",
            episode_body="Alice really likes the new search feature. Bob thinks the UI needs improvement. The search uses advanced vector similarity algorithms.",
            source=EpisodeType.text,
            source_description="User survey response",
            reference_time=datetime.now(timezone.utc),
        )
        print("   ✅ Episode added successfully")

        # Check result
        if hasattr(result, "nodes") and result.nodes:
            print(f"\n   📊 Extracted {len(result.nodes)} entities:")
            for i, node in enumerate(result.nodes, 1):
                print(f"      {i}. {node.name} ({getattr(node, 'label', 'Entity')})")

        if hasattr(result, "edges") and result.edges:
            print(f"\n   📊 Created {len(result.edges)} relationships")

    except Exception as e:
        print(f"   ❌ Error adding episode: {e}")
        import traceback

        traceback.print_exc()
        return

    # Check for vector indices
    print("\n3. Checking for vector indices AFTER episode...")
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688", auth=("neo4j", "password")
    )

    async with driver.session(database="neo4j") as session:
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        vector_indices = await result.data()

        if vector_indices:
            print("   🎉 VECTOR INDICES FOUND!")
            for idx in vector_indices:
                print(f"      Name: {idx['name']}")
                print(f"      Labels: {idx['labelsOrTypes']}")
                print(f"      Properties: {idx['properties']}")
                config = idx.get("indexConfig", {})
                if config:
                    print(f"      Dimensions: {config.get('vector.dimensions')}")
                    print(
                        f"      Similarity: {config.get('vector.similarity_function')}"
                    )
        else:
            print("   ⚠️ Still NO vector indices after adding episode")

        # Check for embeddings
        print("\n4. Checking for embeddings...")
        result = await session.run(
            """
            MATCH (n)
            WHERE n.embedding IS NOT NULL
               OR n.name_embedding IS NOT NULL
               OR n.fact_embedding IS NOT NULL
            WITH labels(n)[0] as label,
                 n.name as name,
                 CASE
                    WHEN n.embedding IS NOT NULL THEN 'embedding'
                    WHEN n.name_embedding IS NOT NULL THEN 'name_embedding'
                    WHEN n.fact_embedding IS NOT NULL THEN 'fact_embedding'
                 END as embed_type,
                 CASE
                    WHEN n.embedding IS NOT NULL THEN size(n.embedding)
                    WHEN n.name_embedding IS NOT NULL THEN size(n.name_embedding)
                    WHEN n.fact_embedding IS NOT NULL THEN size(n.fact_embedding)
                 END as dim
            RETURN label, name, embed_type, dim
            ORDER BY label
            LIMIT 10
        """
        )
        embeddings = await result.data()

        if embeddings:
            print("   ✅ EMBEDDINGS FOUND:")
            for emb in embeddings:
                print(
                    f"      {emb['label']}: {emb['name']} has {emb['embed_type']} [{emb['dim']} dims]"
                )
        else:
            print("   ❌ No embeddings found")

        # Check edges for embeddings
        result = await session.run(
            """
            MATCH ()-[r:RELATES_TO]->()
            WHERE r.fact_embedding IS NOT NULL
            RETURN type(r) as type, r.fact as fact, size(r.fact_embedding) as dim
            LIMIT 5
        """
        )
        edge_embeddings = await result.data()

        if edge_embeddings:
            print("\n   ✅ EDGE EMBEDDINGS FOUND:")
            for edge in edge_embeddings:
                print(
                    f"      {edge['type']}: '{edge['fact'][:50]}...' [{edge['dim']} dims]"
                )

    await driver.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(add_episode_and_check())
