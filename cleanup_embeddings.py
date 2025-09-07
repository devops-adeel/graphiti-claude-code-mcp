#!/usr/bin/env python3
"""Clean up old embeddings from Neo4j to prepare for new 1024-dimension embeddings."""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Load configuration
load_dotenv(".env.graphiti")

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

if not password:
    print("❌ NEO4J_PASSWORD not set. Please export it first.")
    print(
        "   Run: export NEO4J_PASSWORD=$(op item get ctyxybforywkjp2krbdpeulzzq --fields 'Neo4j.neo4j-password')"
    )
    exit(1)

driver = GraphDatabase.driver(uri, auth=(user, password))


def cleanup_embeddings():
    """Remove old embeddings and vector indexes."""
    with driver.session() as session:
        print("🧹 Cleaning up old embeddings...")

        # Drop existing vector indexes
        print("  Dropping vector indexes...")
        try:
            session.run("DROP INDEX group_entity_vector_ IF EXISTS")
            print("    ✅ Dropped group_entity_vector_ index")
        except Exception as e:
            print(f"    ⚠️  Could not drop index: {e}")

        # Clear name_embedding fields from Entity nodes
        print("  Clearing name_embedding fields from Entity nodes...")
        result = session.run(
            """
            MATCH (n:Entity_)
            WHERE n.name_embedding IS NOT NULL
            REMOVE n.name_embedding
            RETURN count(n) as cleared
        """
        )
        count = result.single()["cleared"]
        print(f"    ✅ Cleared {count} name_embedding fields")

        # Clear embedding fields from all nodes
        print("  Clearing embedding fields from all nodes...")
        result = session.run(
            """
            MATCH (n)
            WHERE n.embedding IS NOT NULL
            REMOVE n.embedding
            RETURN count(n) as cleared
        """
        )
        count = result.single()["cleared"]
        print(f"    ✅ Cleared {count} embedding fields")

        # Clear edge embeddings
        print("  Clearing edge embeddings...")
        result = session.run(
            """
            MATCH ()-[r]->()
            WHERE r.embedding IS NOT NULL
            REMOVE r.embedding
            RETURN count(r) as cleared
        """
        )
        count = result.single()["cleared"]
        print(f"    ✅ Cleared {count} edge embeddings")

        print("\n✨ Cleanup complete! Ready for fresh 1024-dimension embeddings.")


if __name__ == "__main__":
    cleanup_embeddings()
    driver.close()
