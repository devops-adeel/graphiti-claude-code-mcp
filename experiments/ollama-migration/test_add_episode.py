#!/usr/bin/env python3
"""
Test adding an episode to Graphiti to see if it creates vector indexes.
Based on: https://help.getzep.com/graphiti/core-concepts/adding-episodes
"""

import asyncio
import os
import logging
from datetime import datetime
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv("/Users/adeel/.config/graphiti-mcp/.env.graphiti")


async def test_add_episode():
    """Test adding an episode to trigger vector index creation"""

    print("\n" + "=" * 60)
    print("TEST: ADD EPISODE TO TRIGGER VECTOR INDEX CREATION")
    print("=" * 60)

    # Get Neo4j password
    import subprocess

    result = subprocess.run(
        [
            "bash",
            "-c",
            "source ~/.config/graphiti-mcp/service-token && op read 'op://HomeLab/Graphiti-Neo4j/password'",
        ],
        capture_output=True,
        text=True,
    )
    neo4j_password = (
        result.stdout.strip() if result.returncode == 0 else os.getenv("NEO4J_PASSWORD")
    )

    neo4j_uri = f"bolt://{os.getenv('NEO4J_HOST')}:{os.getenv('NEO4J_PORT')}"
    neo4j_database = os.getenv("NEO4J_DATABASE")

    # Initialize Neo4j driver for inspection
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=("neo4j", neo4j_password))

    # Check initial vector index state
    print("\n1️⃣ Initial Vector Index State:")
    async with driver.session(database=neo4j_database) as session:
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        indexes = await result.data()
        if indexes:
            for idx in indexes:
                print(f"   - {idx['name']}: {idx.get('indexConfig', {})}")
        else:
            print("   No vector indexes found")

    # Initialize Graphiti
    print("\n2️⃣ Initializing Graphiti with Ollama...")

    try:
        from graphiti_core import Graphiti
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.nodes import EpisodeType
        from ollama_native_client import OllamaNativeClient
        from ollama_embedder_wrapper import OllamaEmbedder

        # Create LLM client (use localhost when running from host)
        llm_config = LLMConfig(
            api_key="ollama",
            model=os.getenv("OLLAMA_MODEL"),
            base_url="http://localhost:11434/v1",
            temperature=0.1,
            max_tokens=4096,
        )
        llm_client = OllamaNativeClient(config=llm_config)
        print("   ✅ Ollama LLM client created")

        # Create Embedder with 768 dimensions
        embedding_dim = int(os.getenv("OLLAMA_EMBEDDING_DIM"))
        embedder = OllamaEmbedder(
            model=os.getenv("OLLAMA_EMBEDDING_MODEL"),
            host="http://localhost:11434",
            embedding_dim=embedding_dim,
        )
        print(f"   ✅ Ollama Embedder created ({embedding_dim} dimensions)")

        # Initialize Graphiti
        graphiti = Graphiti(
            uri=neo4j_uri,
            user="neo4j",
            password=neo4j_password,
            llm_client=llm_client,
            embedder=embedder,
        )
        print("   ✅ Graphiti client initialized")

        # Build indices (non-vector ones)
        await graphiti.build_indices_and_constraints()
        print("   ✅ Base indices built")

    except Exception as e:
        print(f"   ❌ Initialization error: {e}")
        import traceback

        traceback.print_exc()
        return

    # Add an episode
    print("\n3️⃣ Adding a test episode...")

    try:
        # Create a simple episode about the Ollama migration
        episode_result = await graphiti.add_episode(
            name="ollama_migration_test",
            episode_body="""
            Successfully migrated the Graphiti memory system from a hybrid OpenAI/Ollama
            configuration to a pure Ollama setup. The system now uses mxbai-embed-large
            model with 768-dimensional embeddings instead of the previous 1536 dimensions
            from OpenAI. This migration makes the entire system self-hosted and eliminates
            vector dimension mismatch errors.
            """,
            source=EpisodeType.text,
            source_description="Technical migration documentation",
            reference_time=datetime.now(),
            group_id=os.getenv("GRAPHITI_GROUP_ID"),
        )

        print("   ✅ Episode added successfully!")
        print(
            f"   Episode UUID: {episode_result.episode.uuid if hasattr(episode_result, 'episode') else 'N/A'}"
        )

        # Print extracted entities if available
        if hasattr(episode_result, "nodes") and episode_result.nodes:
            print(f"   Extracted {len(episode_result.nodes)} entities:")
            for node in episode_result.nodes[:3]:  # Show first 3
                print(
                    f"      - {node.name}: {node.label if hasattr(node, 'label') else 'Entity'}"
                )

    except Exception as e:
        print(f"   ❌ Error adding episode: {e}")
        import traceback

        traceback.print_exc()

    # Check vector index state AFTER adding episode
    print("\n4️⃣ Vector Index State AFTER Adding Episode:")
    async with driver.session(database=neo4j_database) as session:
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        indexes = await result.data()
        if indexes:
            print("   🎉 Vector indexes found!")
            for idx in indexes:
                print(f"   - Name: {idx['name']}")
                print(f"     State: {idx['state']}")
                print(f"     Labels: {idx['labelsOrTypes']}")
                print(f"     Properties: {idx['properties']}")
                config = idx.get("indexConfig", {})
                if config:
                    print(f"     Dimensions: {config.get('vector.dimensions', 'N/A')}")
                    print(
                        f"     Similarity: {config.get('vector.similarity_function', 'N/A')}"
                    )
        else:
            print("   ⚠️  Still no vector indexes found")

    # Check if embeddings were created
    print("\n5️⃣ Checking for embeddings in the database:")
    async with driver.session(database=neo4j_database) as session:
        # Check Entity nodes with embeddings
        result = await session.run(
            """
            MATCH (n:Entity)
            WHERE n.embedding IS NOT NULL
            RETURN n.name as name, size(n.embedding) as dim
            LIMIT 5
        """
        )
        entities = await result.data()

        if entities:
            print(f"   ✅ Found {len(entities)} entities with embeddings:")
            for entity in entities:
                print(f"      - {entity['name']}: {entity['dim']} dimensions")
        else:
            print("   No Entity nodes with embeddings found")

        # Check Episodic nodes with embeddings
        result = await session.run(
            """
            MATCH (n:Episodic)
            WHERE n.embedding IS NOT NULL
            RETURN n.name as name, size(n.embedding) as dim
            LIMIT 5
        """
        )
        episodes = await result.data()

        if episodes:
            print(f"   ✅ Found {len(episodes)} episodes with embeddings:")
            for episode in episodes:
                print(f"      - {episode['name']}: {episode['dim']} dimensions")
        else:
            print("   No Episodic nodes with embeddings found")

    await driver.close()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    # Summary
    if indexes:
        print("\n✅ SUCCESS: Vector index was created when adding episode!")
    else:
        print("\n⚠️  Vector index was NOT created automatically")
        print("   Graphiti might not create vector indexes in Community Edition")
        print("   or might require manual creation")


if __name__ == "__main__":
    asyncio.run(test_add_episode())
