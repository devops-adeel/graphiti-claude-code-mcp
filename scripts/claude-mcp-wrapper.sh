#!/bin/bash
# Claude Code MCP Wrapper Script
# This script handles the Docker execution for the Graphiti MCP server
# when invoked through the `claude mcp add` command

set -e  # Exit on error

# Load 1Password service account token
SERVICE_TOKEN_FILE="$HOME/.config/graphiti-mcp/service-token"
if [ -f "$SERVICE_TOKEN_FILE" ]; then
    source "$SERVICE_TOKEN_FILE"
else
    echo "Error: Service token not found at $SERVICE_TOKEN_FILE" >&2
    echo "Please run: echo 'export OP_SERVICE_ACCOUNT_TOKEN=\"your-token\"' > ~/.config/graphiti-mcp/service-token" >&2
    exit 1
fi

# Check if token is set
if [ -z "$OP_SERVICE_ACCOUNT_TOKEN" ]; then
    echo "Error: OP_SERVICE_ACCOUNT_TOKEN not set in service token file" >&2
    exit 1
fi

# Check if configuration file exists
CONFIG_FILE="$HOME/.config/graphiti-mcp/.env.graphiti"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found at $CONFIG_FILE" >&2
    echo "Please create it from the template: cp .env.graphiti.example ~/.config/graphiti-mcp/.env.graphiti" >&2
    exit 1
fi

# Run the Docker container with proper environment and mounts
exec docker run -i --rm \
  --network orbstack-shared \
  -e OP_SERVICE_ACCOUNT_TOKEN="$OP_SERVICE_ACCOUNT_TOKEN" \
  -v "$CONFIG_FILE:/app/.env.graphiti:ro" \
  --add-host host.docker.internal:host-gateway \
  graphiti-mcp-server:latest
