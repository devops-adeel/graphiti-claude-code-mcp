#!/usr/bin/env python3
"""
Minimal Graphiti test to understand initialization and index creation.
"""

import asyncio
import os
import logging
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv("/Users/adeel/.config/graphiti-mcp/.env.graphiti")


async def test_minimal_graphiti():
    """Test minimal Graphiti initialization with Ollama"""

    print("\n" + "=" * 60)
    print("MINIMAL GRAPHITI TEST WITH OLLAMA")
    print("=" * 60)

    # Step 1: Show environment configuration
    print("\n1️⃣ Environment Configuration:")
    print(f"   USE_OLLAMA: {os.getenv('USE_OLLAMA')}")
    print(f"   OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL')}")
    print(f"   OLLAMA_EMBEDDING_MODEL: {os.getenv('OLLAMA_EMBEDDING_MODEL')}")
    print(f"   OLLAMA_EMBEDDING_DIM: {os.getenv('OLLAMA_EMBEDDING_DIM')}")
    print(f"   NEO4J_HOST: {os.getenv('NEO4J_HOST')}")
    print(f"   NEO4J_DATABASE: {os.getenv('NEO4J_DATABASE')}")

    # Step 2: Initialize Neo4j driver for direct queries
    print("\n2️⃣ Initializing Neo4j driver for inspection...")

    # Get password from environment or 1Password
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_password:
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
        if result.returncode == 0:
            neo4j_password = result.stdout.strip()
            print("   ✅ Got password from 1Password")
        else:
            print(f"   ❌ Failed to get password: {result.stderr}")
            return

    neo4j_uri = f"bolt://{os.getenv('NEO4J_HOST', 'localhost')}:{os.getenv('NEO4J_PORT', '7687')}"
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=("neo4j", neo4j_password))

    async with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
        # Check initial state
        print("\n3️⃣ Initial Neo4j state - Vector indexes:")
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        indexes = await result.data()
        if indexes:
            for idx in indexes:
                print(f"   - {idx['name']}: dimensions={idx.get('indexConfig', {})}")
        else:
            print("   No vector indexes found")

    # Step 4: Initialize Graphiti components
    print("\n4️⃣ Initializing Graphiti components...")

    try:
        # Import Graphiti components
        from graphiti_core import Graphiti
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.nodes import EpisodeType
        from graphiti_core.utils.bulk_utils import RawEpisode

        # Import Ollama-specific components
        print("   Importing Ollama components...")
        from ollama_native_client import OllamaNativeClient
        from ollama_embedder_wrapper import OllamaEmbedder

        # Create LLM client
        print("\n5️⃣ Creating Ollama LLM client...")
        llm_config = LLMConfig(
            api_key="ollama",  # Ollama doesn't need a real key
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            base_url="http://host.docker.internal:11434/v1",
            temperature=0.1,
            max_tokens=4096,
        )
        llm_client = OllamaNativeClient(config=llm_config)
        print("   ✅ LLM client created")

        # Create Embedder
        print("\n6️⃣ Creating Ollama Embedder...")
        embedding_dim = int(os.getenv("OLLAMA_EMBEDDING_DIM", "768"))
        embedder = OllamaEmbedder(
            model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            host="http://host.docker.internal:11434",
            embedding_dim=embedding_dim,
        )
        print(f"   ✅ Embedder created with {embedding_dim} dimensions")

        # Initialize Graphiti with connection parameters
        print("\n7️⃣ Initializing Graphiti client...")
        # Graphiti expects URI, username, password - not a driver object
        graphiti = Graphiti(
            uri=neo4j_uri,
            user="neo4j",
            password=neo4j_password,
            llm_client=llm_client,
            embedder=embedder,
        )
        print("   ✅ Graphiti client created")

        # Build indices
        print("\n8️⃣ Building indices and constraints...")
        await graphiti.build_indices_and_constraints()
        print("   ✅ Indices built")

    except Exception as e:
        print(f"\n   ❌ Error during Graphiti initialization: {e}")
        import traceback

        traceback.print_exc()

    # Step 9: Check Neo4j state after Graphiti initialization
    print("\n9️⃣ Neo4j state AFTER Graphiti initialization:")

    async with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
        # Check all indexes
        print("\n   All indexes:")
        result = await session.run("SHOW INDEXES")
        indexes = await result.data()

        # Group by type
        vector_indexes = []
        fulltext_indexes = []
        range_indexes = []

        for idx in indexes:
            idx_type = idx.get("type", "")
            if idx_type == "VECTOR":
                vector_indexes.append(idx)
            elif idx_type == "FULLTEXT":
                fulltext_indexes.append(idx)
            elif idx_type == "RANGE":
                range_indexes.append(idx)

        print(f"\n   📊 Index Summary:")
        print(f"      Vector indexes: {len(vector_indexes)}")
        print(f"      Fulltext indexes: {len(fulltext_indexes)}")
        print(f"      Range indexes: {len(range_indexes)}")

        if vector_indexes:
            print("\n   🎯 Vector Indexes (DETAILED):")
            for idx in vector_indexes:
                print(f"      Name: {idx['name']}")
                print(f"      Labels: {idx['labelsOrTypes']}")
                print(f"      Properties: {idx['properties']}")
                print(f"      State: {idx['state']}")
                config = idx.get("indexConfig", {})
                print(f"      Config: {config}")
                if config:
                    print(
                        f"        - Dimensions: {config.get('vector.dimensions', 'N/A')}"
                    )
                    print(
                        f"        - Similarity: {config.get('vector.similarity_function', 'N/A')}"
                    )
                print()
        else:
            print("\n   ⚠️  No vector indexes found after Graphiti initialization!")

        # Check if any Entity nodes exist
        print("\n🔟 Checking for Entity nodes:")
        result = await session.run("MATCH (n:Entity) RETURN count(n) as count")
        record = await result.single()
        entity_count = record["count"] if record else 0
        print(f"   Entity nodes in database: {entity_count}")

        if entity_count > 0:
            # Check if any have embeddings
            result = await session.run(
                "MATCH (n:Entity) WHERE n.embedding IS NOT NULL RETURN count(n) as count"
            )
            record = await result.single()
            embedded_count = record["count"] if record else 0
            print(f"   Entity nodes with embeddings: {embedded_count}")

            if embedded_count > 0:
                # Check embedding dimensions
                result = await session.run(
                    "MATCH (n:Entity) WHERE n.embedding IS NOT NULL "
                    "RETURN size(n.embedding) as dim LIMIT 1"
                )
                record = await result.single()
                if record:
                    print(f"   Embedding dimension found: {record['dim']}")

    await driver.close()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_minimal_graphiti())
