#!/usr/bin/env python3
"""
Check for existing vector indexes in Neo4j and clean up any conflicting ones
"""

import asyncio
from neo4j import AsyncGraphDatabase


async def check_and_clean_indexes():
    driver = AsyncGraphDatabase.driver(
        "bolt://neo4j.graphiti.local:7687",
        auth=("neo4j", "jzt4cAXRCBxAQWJ9eSC7qVrxtnA3EplimUsE1IvfMXo="),
    )

    try:
        async with driver.session(database="neo4j") as session:
            # Check all indexes
            print("=" * 60)
            print("CHECKING EXISTING INDEXES")
            print("=" * 60)

            # Get all indexes
            result = await session.run("SHOW INDEXES")
            all_indexes = await result.data()

            print(f"\nTotal indexes found: {len(all_indexes)}")

            # Filter for vector indexes
            vector_indexes = [idx for idx in all_indexes if idx.get("type") == "VECTOR"]

            if vector_indexes:
                print(f"\n🔍 Found {len(vector_indexes)} vector indexes:")
                for idx in vector_indexes:
                    name = idx["name"]
                    state = idx["state"]
                    dimensions = idx.get("indexConfig", {}).get(
                        "vector.dimensions", "unknown"
                    )
                    entity_type = idx.get("entityType", "unknown")
                    labels = idx.get("labelsOrTypes", [])
                    properties = idx.get("properties", [])

                    print(f"\n  Index: {name}")
                    print(f"    State: {state}")
                    print(f"    Dimensions: {dimensions}")
                    print(f"    Entity Type: {entity_type}")
                    print(f"    Labels: {labels}")
                    print(f"    Properties: {properties}")

                    # Check if it's a 768-dimension index (our old ones)
                    if dimensions == 768:
                        print(f"    ⚠️  This is a 768-dimension index - needs removal!")
            else:
                print("\n✅ No vector indexes found - clean slate!")

            # Check for our manually created indexes
            manual_index_names = [
                "entity_name_embedding",
                "entity_embedding",
                "edge_fact_embedding",
            ]

            indexes_to_drop = []
            for idx in all_indexes:
                if idx["name"] in manual_index_names:
                    indexes_to_drop.append(idx["name"])

            if indexes_to_drop:
                print(
                    f"\n🗑️  Found {len(indexes_to_drop)} manually created indexes to remove:"
                )
                for name in indexes_to_drop:
                    print(f"  - {name}")
                    try:
                        await session.run(f"DROP INDEX {name}")
                        print(f"    ✅ Dropped {name}")
                    except Exception as e:
                        print(f"    ❌ Failed to drop {name}: {e}")

            # Check for any nodes with embeddings
            print("\n" + "=" * 60)
            print("CHECKING EXISTING EMBEDDINGS")
            print("=" * 60)

            # Check Entity nodes
            result = await session.run(
                """
                MATCH (n:Entity)
                WHERE n.embedding IS NOT NULL OR n.name_embedding IS NOT NULL
                RETURN COUNT(n) as count,
                       COUNT(n.embedding) as with_embedding,
                       COUNT(n.name_embedding) as with_name_embedding
            """
            )
            entity_data = await result.single()

            if entity_data and entity_data["count"] > 0:
                print(f"\nEntity nodes with embeddings:")
                print(f"  Total: {entity_data['count']}")
                print(f"  With embedding: {entity_data['with_embedding']}")
                print(f"  With name_embedding: {entity_data['with_name_embedding']}")

                # Check dimensions of existing embeddings
                result = await session.run(
                    """
                    MATCH (n:Entity)
                    WHERE n.embedding IS NOT NULL
                    RETURN size(n.embedding) as dim
                    LIMIT 1
                """
                )
                dim_data = await result.single()
                if dim_data:
                    print(f"  Current embedding dimensions: {dim_data['dim']}")
                    if dim_data["dim"] != 1024:
                        print(
                            f"  ⚠️  Embeddings are {dim_data['dim']}-dimensional, will be replaced with 1024"
                        )
            else:
                print("\n✅ No entities with embeddings found")

            # Check for edges with embeddings
            result = await session.run(
                """
                MATCH ()-[r:RELATES_TO]-()
                WHERE r.fact_embedding IS NOT NULL
                RETURN COUNT(r) as count
            """
            )
            edge_data = await result.single()

            if edge_data and edge_data["count"] > 0:
                print(f"\nEdges with embeddings: {edge_data['count']}")
            else:
                print("✅ No edges with embeddings found")

    finally:
        await driver.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\nYour Neo4j is ready for the new 1024-dimension setup!")
    print("Graphiti will automatically create the correct vector indexes")
    print("when you add episodes with mxbai-embed-large embeddings.")


if __name__ == "__main__":
    asyncio.run(check_and_clean_indexes())
