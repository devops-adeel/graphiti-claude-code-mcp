#!/usr/bin/env python3
"""
Test Graphiti with Instructor library for proper Ollama JSON handling
This is the final solution that combines everything we've learned.
"""

import asyncio
from datetime import datetime, timezone
from neo4j import AsyncGraphDatabase


async def test_instructor_solution():
    print("\n" + "=" * 60)
    print("FINAL SOLUTION: GRAPHITI + OLLAMA VIA INSTRUCTOR")
    print("=" * 60)

    # 1. First test Instructor with Ollama directly
    print("\n1. Testing Instructor + Ollama integration...")
    try:
        from openai import OpenAI
        from pydantic import BaseModel
        import instructor

        # Simple test model
        class User(BaseModel):
            name: str
            age: int

        # Patch OpenAI client with Instructor
        client = instructor.from_openai(
            OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",
            ),
            mode=instructor.Mode.JSON,
        )

        # Test extraction
        user = client.chat.completions.create(
            model="llama3.1:8b",
            response_model=User,
            messages=[{"role": "user", "content": "Jason is 25 years old"}],
        )
        print(f"   ✅ Instructor works! Extracted: {user.name}, age {user.age}")

    except Exception as e:
        print(f"   ❌ Instructor test failed: {e}")
        return

    # 2. Now test with Graphiti using OpenAIGenericClient
    # Since Instructor doesn't directly integrate with Graphiti, we'll use
    # the insights we learned to make it work
    print("\n2. Testing Graphiti with proper configuration...")

    try:
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )

        # Use a larger model that handles complex schemas better
        llm_config = LLMConfig(
            api_key="ollama",
            model="llama3.1:8b",
            base_url="http://localhost:11434/v1",
            temperature=0.1,  # Lower temperature for more consistent output
        )

        llm_client = OpenAIGenericClient(config=llm_config)

        graphiti = Graphiti(
            "bolt://localhost:7688",
            "neo4j",
            "password",
            llm_client=llm_client,
            embedder=OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key="ollama",
                    embedding_model="mxbai-embed-large",
                    embedding_dim=1024,
                    base_url="http://localhost:11434/v1",
                )
            ),
            cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
        )
        print("   ✅ Graphiti initialized")

    except Exception as e:
        print(f"   ❌ Graphiti init failed: {e}")
        return

    # 3. Build indices
    print("\n3. Building indices...")
    try:
        await graphiti.build_indices_and_constraints()
        print("   ✅ Indices built (range and fulltext only)")
    except Exception as e:
        print(f"   ⚠️ Indices may already exist: {e}")

    # 4. Try to add a simple episode
    print("\n4. Adding test episode...")
    try:
        # Use a simpler test case first
        result = await graphiti.add_episode(
            name="Simple Test",
            episode_body="Alice likes Bob.",  # Very simple to extract
            source=EpisodeType.text,
            source_description="Test",
            reference_time=datetime.now(timezone.utc),
        )
        print("   ✅ Simple episode added!")

        if hasattr(result, "nodes") and result.nodes:
            print(f"   Found {len(result.nodes)} entities")

    except Exception as e:
        print(f"   ❌ Failed to add episode: {str(e)[:200]}")

        # The error is likely due to schema mismatch
        # Let's document the solution
        print("\n" + "=" * 60)
        print("ANALYSIS OF FAILURE:")
        print("=" * 60)
        print(
            """
The issue is that OpenAIGenericClient adds schemas in a way that
confuses Ollama models. Even larger models struggle because the
prompt says "Respond with a JSON object in the following format:"
followed by the JSON schema, which models interpret as returning
the schema itself.

SOLUTIONS:
1. Use a much larger model (70B+) that better understands context
2. Modify Graphiti's OpenAIGenericClient (what we did in ollama_graphiti_client.py)
3. Use a different LLM provider that supports structured output natively
4. Wait for Ollama to support OpenAI's structured output endpoints
        """
        )

    # 5. Check and create vector indexes
    print("\n5. Checking/Creating vector indexes...")
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688", auth=("neo4j", "password")
    )

    async with driver.session(database="neo4j") as session:
        # Check existing indexes
        result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
        vector_indices = await result.data()

        if not vector_indices:
            print("   No vector indexes found. Creating them...")

            # Create the necessary vector indexes
            indexes_to_create = [
                ("entity_name_embedding", "Entity", "name_embedding"),
                ("entity_embedding", "Entity", "embedding"),
                ("edge_fact_embedding", "RELATES_TO", "fact_embedding"),
            ]

            for index_name, label_or_type, property_name in indexes_to_create:
                try:
                    if label_or_type == "RELATES_TO":
                        # Edge index
                        query = f"""
                        CREATE VECTOR INDEX {index_name} IF NOT EXISTS
                        FOR ()-[r:{label_or_type}]-() ON r.{property_name}
                        OPTIONS {{
                            indexConfig: {{
                                `vector.dimensions`: 1024,
                                `vector.similarity_function`: 'cosine'
                            }}
                        }}
                        """
                    else:
                        # Node index
                        query = f"""
                        CREATE VECTOR INDEX {index_name} IF NOT EXISTS
                        FOR (n:{label_or_type}) ON n.{property_name}
                        OPTIONS {{
                            indexConfig: {{
                                `vector.dimensions`: 1024,
                                `vector.similarity_function`: 'cosine'
                            }}
                        }}
                        """

                    await session.run(query)
                    print(f"   ✅ Created {index_name}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"   ⚠️ {index_name} already exists")
                    else:
                        print(f"   ❌ Failed to create {index_name}: {e}")
        else:
            print(f"   ✅ Found {len(vector_indices)} existing vector indexes")

    await driver.close()

    print("\n" + "=" * 60)
    print("FINAL RECOMMENDATION:")
    print("=" * 60)
    print(
        """
To use Graphiti with Ollama successfully:

1. Use the custom ollama_graphiti_client.py we created
2. Use a model of at least 8B parameters (llama3.1:8b works)
3. Manually create vector indexes (they're not auto-created)
4. Lower temperature for more consistent JSON output

The root issue is that Graphiti's prompt construction confuses
Ollama models. Our custom client fixes this by providing clearer
instructions with examples instead of raw JSON schemas.
    """
    )


if __name__ == "__main__":
    asyncio.run(test_instructor_solution())
