"""
Secret Reference Manifest for 1Password SDK Integration

This file contains mappings between environment variable names and their
corresponding 1Password secret references. Only actual secrets are stored
in 1Password - configuration values remain in .env.graphiti
"""

# 1Password Secret References
# These are actual secrets that should never be hardcoded
SECRET_REFS = {
    "NEO4J_PASSWORD": "op://Developer/Neo4j/password",
    "OPENAI_API_KEY": "op://Developer/OpenAI/credential",
    "LANGFUSE_PUBLIC_KEY": "op://Developer/Langfuse/langfuse-public-key",
    "LANGFUSE_SECRET_KEY": "op://Developer/Langfuse/langfuse-secret-key",
    "LANGFUSE_HOST": "op://Developer/Langfuse/langfuse-host",
}

# Non-secret configuration values
# These remain in .env.graphiti and are not sensitive
CONFIG_VALUES = {
    "GRAPHITI_GROUP_ID": "shared_knowledge",
    "NEO4J_DATABASE": "neo4j",  # Must be "neo4j" for Community Edition
    "NEO4J_HOST": "neo4j.graphiti.local",  # OrbStack domain
    "NEO4J_PORT": "7687",
    "NEO4J_USER": "neo4j",
    "OPENAI_MODEL": "gpt-4o-mini",
    "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
    "MEMORY_DECAY_FACTOR": "0.95",
    "MEMORY_INCLUDE_HISTORICAL": "false",
    "ENABLE_GTD_INTEGRATION": "true",
    "ENABLE_CROSS_REFERENCES": "true",
}

# Combined for backward compatibility during migration
ALL_ENV_VARS = {**SECRET_REFS, **CONFIG_VALUES}
