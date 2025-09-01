#!/usr/bin/env python3
"""
Neo4j integration tests for Graphiti memory system
AI-CONTEXT: Neo4j graph database via OrbStack domain
Connection: bolt://neo4j.graphiti.local:7687
Database: "neo4j" (Community Edition requirement)
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_neo4j_connection():
    """Test Neo4j connectivity and configuration"""
    print("=" * 60)
    print("NEO4J INTEGRATION TEST")
    print("=" * 60)

    # Verify environment configuration
    assert (
        os.getenv("NEO4J_HOST") == "neo4j.graphiti.local"
    ), f"NEO4J_HOST should be 'neo4j.graphiti.local', got {os.getenv('NEO4J_HOST')}"
    assert (
        os.getenv("NEO4J_PORT") == "7687"
    ), f"NEO4J_PORT should be '7687', got {os.getenv('NEO4J_PORT')}"
    assert (
        os.getenv("NEO4J_DATABASE") == "neo4j"
    ), f"NEO4J_DATABASE must be 'neo4j' for Community Edition, got {os.getenv('NEO4J_DATABASE')}"

    print("✓ Environment configuration correct")
    print(f"  Host: {os.getenv('NEO4J_HOST')}")
    print(f"  Port: {os.getenv('NEO4J_PORT')}")
    print(f"  Database: {os.getenv('NEO4J_DATABASE')}")

    # Test Neo4j driver connection
    try:
        from neo4j import GraphDatabase

        uri = f"bolt://{os.getenv('NEO4J_HOST')}:{os.getenv('NEO4J_PORT')}"
        driver = GraphDatabase.driver(
            uri, auth=("neo4j", os.getenv("NEO4J_PASSWORD", ""))
        )

        # Verify connectivity
        driver.verify_connectivity()
        print("✓ Neo4j driver connected successfully")

        # Test basic query
        with driver.session(database="neo4j") as session:
            result = session.run("RETURN 1 AS test")
            record = result.single()
            assert record["test"] == 1
            print("✓ Basic query executed successfully")

        driver.close()

    except Exception as e:
        print(f"✗ Neo4j connection failed: {e}")
        return False

    # Test Graphiti memory integration
    try:
        from graphiti_memory import get_shared_memory

        print("\nTesting Graphiti memory integration...")
        memory = await get_shared_memory()

        # Add test memory
        test_content = {
            "title": "Neo4j Integration Test",
            "description": "Testing Neo4j backend with Graphiti",
            "test_type": "integration",
        }
        memory_id = await memory.add_memory(test_content, source="neo4j_test")
        print(f"✓ Added test memory: {memory_id}")

        # Search for the memory
        results = await memory.search_with_temporal_weight("Neo4j integration")
        print(f"✓ Search executed, found {len(results)} results")

        # Close connection
        await memory.close()

    except Exception as e:
        print(f"✗ Graphiti integration failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ NEO4J INTEGRATION TEST PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    # Load environment configuration
    from dotenv import load_dotenv

    load_dotenv(".env.graphiti")

    try:
        result = asyncio.run(test_neo4j_connection())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
