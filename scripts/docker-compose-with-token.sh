#!/bin/bash
# Docker Compose wrapper that sources the 1Password service token
# This ensures the OP_SERVICE_ACCOUNT_TOKEN is available to containers

# Source the service token
if [ -f ~/.config/graphiti-mcp/service-token ]; then
    source ~/.config/graphiti-mcp/service-token
    echo "✅ 1Password service token loaded"
else
    echo "⚠️ Service token file not found at ~/.config/graphiti-mcp/service-token"
    echo "Run: scripts/setup-1password.sh to create it"
    exit 1
fi

# Pass all arguments to docker compose
exec docker compose "$@"
