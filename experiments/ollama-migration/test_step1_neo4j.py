#!/usr/bin/env python3
"""
Step 1: Test Neo4j connection and APOC availability
"""

import asyncio
from neo4j import AsyncGraphDatabase


async def test_neo4j():
    print("\n" + "=" * 60)
    print("STEP 1: TEST NEO4J + APOC")
    print("=" * 60)

    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688", auth=("neo4j", "password")
    )

    async with driver.session(database="neo4j") as session:
        # Test basic connection
        result = await session.run("RETURN 1 as test")
        record = await result.single()
        if record and record["test"] == 1:
            print("✅ Neo4j connection successful")
        else:
            print("❌ Neo4j connection failed")
            return

        # Test APOC availability
        try:
            result = await session.run("RETURN apoc.version() as version")
            record = await result.single()
            if record:
                print(f"✅ APOC version: {record['version']}")
        except Exception as e:
            print(f"⚠️ APOC not available: {e}")

        # Check Neo4j version
        result = await session.run(
            "CALL dbms.components() YIELD name, versions WHERE name = 'Neo4j Kernel' RETURN versions[0] as version"
        )
        record = await result.single()
        if record:
            print(f"✅ Neo4j version: {record['version']}")

    await driver.close()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_neo4j())
