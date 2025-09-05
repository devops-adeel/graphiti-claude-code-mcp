#!/usr/bin/env python3
"""
Create vector indexes for Graphiti in Neo4j
These are required for vector similarity search but not created automatically by Graphiti
"""

import asyncio
import sys
from neo4j import AsyncGraphDatabase
from typing import List, Tuple


class VectorIndexManager:
    def __init__(
        self,
        uri: str = "bolt://localhost:7688",
        user: str = "neo4j",
        password: str = "password",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None

    async def __aenter__(self):
        self.driver = AsyncGraphDatabase.driver(
            self.uri, auth=(self.user, self.password)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            await self.driver.close()

    async def check_existing_indexes(self) -> dict:
        """Check what indexes already exist"""
        async with self.driver.session(database="neo4j") as session:
            # Check vector indexes
            result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
            vector_indices = await result.data()

            # Check all indexes
            result = await session.run("SHOW INDEXES")
            all_indices = await result.data()

            return {
                "vector": vector_indices,
                "all": all_indices,
                "vector_count": len(vector_indices),
                "total_count": len(all_indices),
            }

    async def create_vector_index(
        self,
        index_name: str,
        label_or_type: str,
        property_name: str,
        dimensions: int = 768,
        is_edge: bool = False,
    ) -> bool:
        """Create a single vector index"""
        async with self.driver.session(database="neo4j") as session:
            try:
                if is_edge:
                    # Edge index
                    query = f"""
                    CREATE VECTOR INDEX {index_name} IF NOT EXISTS
                    FOR ()-[r:{label_or_type}]-() ON r.{property_name}
                    OPTIONS {{
                        indexConfig: {{
                            `vector.dimensions`: {dimensions},
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
                            `vector.dimensions`: {dimensions},
                            `vector.similarity_function`: 'cosine'
                        }}
                    }}
                    """

                await session.run(query)
                print(f"   ✅ Created {index_name}")
                return True

            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   ⚠️  {index_name} already exists")
                    return True
                else:
                    print(f"   ❌ Failed to create {index_name}: {e}")
                    return False

    async def create_all_graphiti_indexes(self, dimensions: int = 768) -> dict:
        """Create all indexes required by Graphiti"""
        print(f"\nCreating vector indexes with {dimensions} dimensions...")

        # Define all required indexes
        indexes_to_create = [
            # Node indexes
            ("entity_name_embedding", "Entity", "name_embedding", False),
            ("entity_embedding", "Entity", "embedding", False),
            # Edge indexes
            ("edge_fact_embedding", "RELATES_TO", "fact_embedding", True),
        ]

        results = {"created": [], "existing": [], "failed": []}

        for index_name, label_or_type, property_name, is_edge in indexes_to_create:
            success = await self.create_vector_index(
                index_name, label_or_type, property_name, dimensions, is_edge
            )

            if success:
                if f"already exists" in f"   ⚠️  {index_name} already exists":
                    results["existing"].append(index_name)
                else:
                    results["created"].append(index_name)
            else:
                results["failed"].append(index_name)

        return results

    async def verify_embeddings(self) -> dict:
        """Verify that embeddings exist in the database"""
        async with self.driver.session(database="neo4j") as session:
            # Check for entities with embeddings
            result = await session.run(
                """
                MATCH (n:Entity)
                WHERE n.embedding IS NOT NULL OR n.name_embedding IS NOT NULL
                RETURN COUNT(n) as entity_count,
                       COUNT(n.embedding) as embedding_count,
                       COUNT(n.name_embedding) as name_embedding_count
            """
            )
            entity_data = await result.single()

            # Check for edges with embeddings
            result = await session.run(
                """
                MATCH ()-[r:RELATES_TO]-()
                WHERE r.fact_embedding IS NOT NULL
                RETURN COUNT(r) as edge_count,
                       COUNT(r.fact_embedding) as fact_embedding_count
            """
            )
            edge_data = await result.single()

            # Get sample embeddings to check dimensions
            result = await session.run(
                """
                MATCH (n:Entity)
                WHERE n.embedding IS NOT NULL
                RETURN size(n.embedding) as embedding_dim
                LIMIT 1
            """
            )
            dim_data = await result.single()

            return {
                "entities": {
                    "total": entity_data["entity_count"] if entity_data else 0,
                    "with_embedding": (
                        entity_data["embedding_count"] if entity_data else 0
                    ),
                    "with_name_embedding": (
                        entity_data["name_embedding_count"] if entity_data else 0
                    ),
                },
                "edges": {
                    "total": edge_data["edge_count"] if edge_data else 0,
                    "with_fact_embedding": (
                        edge_data["fact_embedding_count"] if edge_data else 0
                    ),
                },
                "dimensions": dim_data["embedding_dim"] if dim_data else None,
            }

    async def drop_mismatched_indexes(self) -> List[str]:
        """Drop any vector indexes with wrong dimensions"""
        dropped = []
        async with self.driver.session(database="neo4j") as session:
            # Get all vector indexes
            result = await session.run("SHOW INDEXES WHERE type = 'VECTOR'")
            vector_indices = await result.data()

            for idx in vector_indices:
                dimensions = idx.get("indexConfig", {}).get("vector.dimensions")
                name = idx["name"]

                # Check if dimensions don't match
                if dimensions and dimensions != 768:
                    print(
                        f"   🗑️  Dropping {name} (has {dimensions} dimensions, need 768)"
                    )
                    try:
                        await session.run(f"DROP INDEX {name}")
                        dropped.append(name)
                    except Exception as e:
                        print(f"   ❌ Failed to drop {name}: {e}")

        return dropped


async def main():
    print("=" * 60)
    print("GRAPHITI VECTOR INDEX MANAGER")
    print("=" * 60)

    async with VectorIndexManager() as manager:
        # 1. Check current state
        print("\n1. Checking existing indexes...")
        existing = await manager.check_existing_indexes()
        print(
            f"   Found {existing['vector_count']} vector indexes out of {existing['total_count']} total"
        )

        if existing["vector"]:
            print("\n   Existing vector indexes:")
            for idx in existing["vector"]:
                dim = idx.get("indexConfig", {}).get("vector.dimensions", "?")
                print(f"      - {idx['name']} ({dim} dimensions)")

        # 2. Drop mismatched indexes if any
        print("\n2. Checking for dimension mismatches...")
        dropped = await manager.drop_mismatched_indexes()
        if dropped:
            print(f"   Dropped {len(dropped)} mismatched indexes")
        else:
            print(f"   ✅ No mismatched indexes found")

        # 3. Create required indexes
        print("\n3. Creating/verifying required indexes...")
        results = await manager.create_all_graphiti_indexes()

        print(f"\n   Summary:")
        print(f"      Created: {len(results['created'])}")
        print(f"      Already existed: {len(results['existing'])}")
        print(f"      Failed: {len(results['failed'])}")

        # 4. Verify embeddings
        print("\n4. Verifying embeddings in database...")
        embeddings = await manager.verify_embeddings()

        if embeddings["dimensions"]:
            print(f"   ✅ Embedding dimensions: {embeddings['dimensions']}")
        else:
            print(f"   ⚠️  No embeddings found in database yet")

        print(f"\n   Entity statistics:")
        print(f"      Total entities: {embeddings['entities']['total']}")
        print(f"      With embeddings: {embeddings['entities']['with_embedding']}")
        print(
            f"      With name embeddings: {embeddings['entities']['with_name_embedding']}"
        )

        print(f"\n   Edge statistics:")
        print(f"      Total edges: {embeddings['edges']['total']}")
        print(
            f"      With fact embeddings: {embeddings['edges']['with_fact_embedding']}"
        )

        # 5. Final check
        print("\n5. Final verification...")
        final_state = await manager.check_existing_indexes()

        required_indexes = [
            "entity_name_embedding",
            "entity_embedding",
            "edge_fact_embedding",
        ]
        existing_names = [idx["name"] for idx in final_state["vector"]]

        all_present = all(name in existing_names for name in required_indexes)

        if all_present:
            print("   🎉 All required vector indexes are present!")
            print("\n   You can now use Graphiti with Ollama successfully.")
        else:
            missing = [name for name in required_indexes if name not in existing_names]
            print(f"   ⚠️  Missing indexes: {', '.join(missing)}")
            print("\n   Please check Neo4j logs for any errors.")

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("1. Run test_ollama_client.py to test with custom client")
    print("2. Verify entities are extracted and stored")
    print("3. Test vector similarity search")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
