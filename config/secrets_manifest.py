"""
Secret Reference Manifest for 1Password SDK Integration

This file contains mappings between environment variable names and their
corresponding 1Password secret references. Only actual secrets are stored
in 1Password - configuration values remain in .env.graphiti
"""

# 1Password Secret References
# These are actual secrets that should never be hardcoded
SECRET_REFS = {
    "OPENAI_API_KEY": "op://HomeLab/37e5lxhox53xsvzp3ozau32nha/openai-api-key",
    "LANGFUSE_PUBLIC_KEY": "op://HomeLab/ctyxybforywkjp2krbdpeulzzq/langfuse-public-key",
    "LANGFUSE_SECRET_KEY": "op://HomeLab/ctyxybforywkjp2krbdpeulzzq/langfuse-secret-key",
    "LANGFUSE_HOST": "op://HomeLab/ctyxybforywkjp2krbdpeulzzq/langfuse-host",
}

# Non-secret configuration values
# These remain in .env.graphiti and are not sensitive
CONFIG_VALUES = {
    "GRAPHITI_GROUP_ID": "shared_knowledge",
    "FALKORDB_DATABASE": "shared_gtd_knowledge",
    # FALKORDB_HOST is now loaded from environment/config file
    "FALKORDB_PORT": "6379",
    "OPENAI_MODEL": "gpt-4o-mini",
    "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
    "MEMORY_DECAY_FACTOR": "0.95",
    "MEMORY_INCLUDE_HISTORICAL": "false",
    "ENABLE_GTD_INTEGRATION": "true",
    "ENABLE_CROSS_REFERENCES": "true",
}

# Combined for backward compatibility during migration
ALL_ENV_VARS = {**SECRET_REFS, **CONFIG_VALUES}
