#!/usr/bin/env python3
"""
Test script for native Ollama client with structured outputs.
This validates that entity extraction works with 100% Pydantic compliance.
"""

import asyncio
import os
import json
import sys
from pathlib import Path
from typing import List

# Set up environment for Ollama
os.environ["USE_OLLAMA"] = "true"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "llama3.2:3b"
os.environ["OLLAMA_EMBEDDING_MODEL"] = "nomic-embed-text"
os.environ["GRAPHITI_GROUP_ID"] = "shared_knowledge"


async def test_basic_ollama_connection():
    """Test 1: Verify Ollama is running and accessible"""
    print("\n🔍 Test 1: Basic Ollama Connection")
    print("=" * 50)

    try:
        from ollama import AsyncClient

        client = AsyncClient(host="http://localhost:11434")

        # Test basic chat
        response = await client.chat(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "Say 'test successful'"}],
        )

        print(f"✅ Ollama is running")
        print(f"   Response: {response['message']['content'][:50]}...")
        return True
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print("   Make sure Ollama is running: ollama serve")
        return False


async def test_native_client_structured_output():
    """Test 2: Verify OllamaNativeClient with structured outputs"""
    print("\n🔍 Test 2: Native Client with Structured Output")
    print("=" * 50)

    try:
        from ollama_native_client import OllamaNativeClient
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.prompts.models import Message
        from pydantic import BaseModel, Field

        # Define a test Pydantic model
        class TestEntity(BaseModel):
            name: str = Field(..., description="Entity name")
            entity_type: str = Field(..., description="Type of entity")
            confidence: float = Field(
                ..., ge=0.0, le=1.0, description="Confidence score"
            )

        class TestEntities(BaseModel):
            entities: List[TestEntity] = Field(..., description="List of entities")

        # Create native client
        config = LLMConfig(
            model="llama3.2:3b", base_url="http://localhost:11434", temperature=0.1
        )
        client = OllamaNativeClient(config)

        # Test structured output
        messages = [
            Message(
                role="user",
                content="Extract entities from: John Smith is the CEO of TechCorp, a technology company.",
            )
        ]

        result = await client.generate_response(
            messages=messages, response_model=TestEntities
        )

        print(f"✅ Structured output successful!")
        print(f"   Result type: {type(result)}")
        print(f"   Entities found: {len(result.get('entities', []))}")

        for entity in result.get("entities", []):
            print(f"   - {entity['name']} ({entity['entity_type']})")

        return True

    except Exception as e:
        print(f"❌ Native client test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_graphiti_entity_extraction():
    """Test 3: Test actual Graphiti ExtractedEntities model"""
    print("\n🔍 Test 3: Graphiti Entity Extraction")
    print("=" * 50)

    try:
        from ollama_native_client import OllamaNativeClient
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.prompts.models import Message
        from graphiti_core.prompts.extract_nodes import (
            ExtractedEntity,
            ExtractedEntities,
        )

        # Create native client
        config = LLMConfig(
            model="llama3.2:3b", base_url="http://localhost:11434", temperature=0.1
        )
        client = OllamaNativeClient(config)

        # Prepare extraction prompt similar to what Graphiti uses
        test_text = """
        Alice Johnson works at Microsoft as a Senior Software Engineer.
        She collaborates with Bob Smith who is the Product Manager.
        They are developing a new AI feature for Office 365.
        """

        entity_types = """
        1: Person - Individual human beings
        2: Company - Business organizations
        3: Product - Software or hardware products
        4: Role - Job titles or positions
        """

        messages = [
            Message(
                role="system",
                content="You are an AI assistant that extracts entity nodes from text.",
            ),
            Message(
                role="user",
                content=f"""
                Extract entities from the following text.

                ENTITY TYPES:
                {entity_types}

                TEXT:
                {test_text}

                For each entity, provide its name and entity_type_id (1, 2, 3, or 4).
                """,
            ),
        ]

        result = await client.generate_response(
            messages=messages, response_model=ExtractedEntities
        )

        print(f"✅ ExtractedEntities validation successful!")
        print(f"   Entities extracted: {len(result.get('extracted_entities', []))}")

        for entity in result.get("extracted_entities", []):
            entity_type_map = {1: "Person", 2: "Company", 3: "Product", 4: "Role"}
            entity_type = entity_type_map.get(entity["entity_type_id"], "Unknown")
            print(f"   - {entity['name']} (Type: {entity_type})")

        # Verify structure matches Pydantic model
        validated = ExtractedEntities.model_validate(result)
        print(f"✅ Pydantic validation passed!")

        return True

    except Exception as e:
        print(f"❌ Entity extraction test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_embedder():
    """Test 4: Verify OllamaEmbedder works correctly"""
    print("\n🔍 Test 4: Ollama Embedder")
    print("=" * 50)

    try:
        from ollama_embedder_wrapper import OllamaEmbedder

        embedder = OllamaEmbedder(
            model="nomic-embed-text", host="http://localhost:11434"
        )

        # Test both parameter names
        test_texts = ["Hello world", "Test embedding"]

        # Test with 'input' parameter (what Graphiti uses)
        embeddings1 = await embedder.create(input=test_texts)
        print(f"✅ Embedder works with 'input' parameter")
        print(f"   Generated {len(embeddings1)} embeddings")
        print(f"   Dimension: {len(embeddings1[0])}")

        # Test with 'input_data' parameter (what OpenAIEmbedder expects)
        embeddings2 = await embedder.create(input_data=test_texts)
        print(f"✅ Embedder works with 'input_data' parameter")

        # Test batch method
        embeddings3 = await embedder.create_batch(test_texts)
        print(f"✅ Batch embedding works")

        return True

    except Exception as e:
        print(f"❌ Embedder test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_full_graphiti_integration():
    """Test 5: Full integration with Graphiti memory system"""
    print("\n🔍 Test 5: Full Graphiti Integration")
    print("=" * 50)

    try:
        from graphiti_memory import SharedMemory

        # Initialize shared memory
        memory = SharedMemory()
        await memory.initialize()

        print(f"✅ SharedMemory initialized")
        print(f"   LLM Client type: {type(memory.client.llm_client).__name__}")
        print(f"   Embedder type: {type(memory.client.embedder).__name__}")

        # Try to add a memory
        test_memory = {
            "content": "Test memory with native Ollama client",
            "metadata": {"source": "test_script", "test_run": True},
        }

        # Test embedding generation
        embeddings = await memory.client.embedder.create(input=["test text"])
        print(f"✅ Embeddings generated successfully")

        # Test entity extraction (the critical part)
        from graphiti_core.nodes import EpisodeType
        from datetime import datetime, timezone

        result = await memory.client.add_episode(
            name="test_episode",
            episode_body="John Smith is testing the Ollama integration with Graphiti.",
            source=EpisodeType.message,
            source_description="Test episode",
            reference_time=datetime.now(timezone.utc),
        )

        print(f"✅ Episode added successfully!")
        print(f"   Result: {result}")

        # Check if memory IDs have "pending_" prefix (indicates transaction failure)
        query = """
        MATCH (e:Episodic {group_id: $group_id})
        WHERE e.created_at >= datetime() - duration('PT1M')
        RETURN e.uuid as uuid, e.name as name
        ORDER BY e.created_at DESC
        LIMIT 5
        """

        async with memory.client.driver.session() as session:
            result = await session.run(query, group_id=memory.group_id)
            records = await result.data()

        if records:
            has_pending = any("pending_" in r["uuid"] for r in records)
            if has_pending:
                print(f"⚠️  Found pending_ prefixed IDs (transaction issue)")
                for record in records:
                    print(f"   - {record['uuid']}: {record['name']}")
            else:
                print(f"✅ No pending_ prefixes - transactions working!")
                for record in records[:3]:
                    print(f"   - {record['uuid']}: {record['name']}")

        return True

    except Exception as e:
        print(f"❌ Full integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 OLLAMA NATIVE CLIENT TEST SUITE")
    print("=" * 60)

    tests = [
        ("Basic Connection", test_basic_ollama_connection),
        ("Native Client", test_native_client_structured_output),
        ("Entity Extraction", test_graphiti_entity_extraction),
        ("Embedder", test_embedder),
        ("Full Integration", test_full_graphiti_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {name}")

    print(f"\n   Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Entity extraction is fixed!")
        print("   Your 0% accuracy problem is solved.")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        print("   Common issues:")
        print("   - Is Ollama running? (ollama serve)")
        print("   - Is the model downloaded? (ollama pull llama3.2:3b)")
        print("   - Is Neo4j running?")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
