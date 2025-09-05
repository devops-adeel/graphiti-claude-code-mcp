#!/usr/bin/env python3
"""
Step 3: Build indices and check what was created
"""

import asyncio
from neo4j import AsyncGraphDatabase
from graphiti_core import Graphiti
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient


async def build_and_check_indices():
    print("\n" + "=" * 60)
    print("STEP 3: BUILD INDICES AND CHECK WHAT'S CREATED")
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

    # Build indices
    print("\n2. Building indices and constraints...")
    try:
        await graphiti.build_indices_and_constraints()
        print("   ✅ build_indices_and_constraints() completed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Check what was created
    print("\n3. Checking what indices were created...")
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688", auth=("neo4j", "password")
    )

    async with driver.session(database="neo4j") as session:
        result = await session.run("SHOW INDEXES")
        indexes = await result.data()

        vector_indices = []
        fulltext_indices = []
        range_indices = []

        for idx in indexes:
            idx_type = idx.get("type", "")
            idx_name = idx.get("name", "unnamed")

            if idx_type == "VECTOR":
                vector_indices.append(idx)
            elif idx_type == "FULLTEXT":
                fulltext_indices.append(idx_name)
            elif idx_type == "RANGE":
                range_indices.append(idx_name)

        print(f"\n   📊 INDEX SUMMARY:")
        print(f"   - Range indices: {len(range_indices)}")
        print(f"   - Fulltext indices: {len(fulltext_indices)}")
        print(f"   - Vector indices: {len(vector_indices)}")

        if vector_indices:
            print("\n   🎯 VECTOR INDICES FOUND:")
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
            print("\n   ⚠️ NO VECTOR INDICES CREATED by build_indices_and_constraints()")

        # List some specific indices
        if fulltext_indices:
            print(f"\n   Fulltext indices: {', '.join(fulltext_indices[:5])}")

        # Check constraints
        result = await session.run("SHOW CONSTRAINTS")
        constraints = await result.data()
        print(f"\n   Constraints created: {len(constraints)}")

    await driver.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(build_and_check_indices())
