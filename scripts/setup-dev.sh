#!/bin/bash
# Development Setup Script for 1Password SDK Integration
# This script loads the service account token and starts the MCP server in Docker

set -e  # Exit on error

echo "🔐 Setting up 1Password SDK development environment..."

# Source the service account token
TOKEN_FILE="$HOME/.config/graphiti-mcp/service-token"

if [ -f "$TOKEN_FILE" ]; then
    echo "📂 Loading service account token from $TOKEN_FILE"
    source "$TOKEN_FILE"
else
    echo "❌ Service account token file not found at $TOKEN_FILE"
    echo "Please ensure the token file exists or set OP_SERVICE_ACCOUNT_TOKEN manually"
    exit 1
fi

# Validate token is set
if [ -z "$OP_SERVICE_ACCOUNT_TOKEN" ]; then
    echo "❌ OP_SERVICE_ACCOUNT_TOKEN not set after sourcing token file"
    echo "Please check the token file format"
    exit 1
fi

# Check token format
if [[ ! "$OP_SERVICE_ACCOUNT_TOKEN" =~ ^ops_ ]]; then
    echo "⚠️ Warning: Token doesn't start with 'ops_' - may be invalid"
fi

echo "✅ 1Password token loaded successfully"

# Calculate token expiration (90 days from August 27, 2025)
CREATED_DATE="2025-08-27"
EXPIRES_DATE=$(date -j -v+90d -f "%Y-%m-%d" "$CREATED_DATE" "+%Y-%m-%d" 2>/dev/null || date -d "$CREATED_DATE + 90 days" "+%Y-%m-%d" 2>/dev/null)
DAYS_LEFT=$(( ($(date -j -f "%Y-%m-%d" "$EXPIRES_DATE" "+%s" 2>/dev/null || date -d "$EXPIRES_DATE" "+%s") - $(date "+%s")) / 86400 ))

if [ $DAYS_LEFT -lt 0 ]; then
    echo "❌ Service account token expired $((DAYS_LEFT * -1)) days ago!"
    echo "Please rotate the token in 1Password"
    exit 1
elif [ $DAYS_LEFT -lt 7 ]; then
    echo "⚠️ WARNING: Token expires in $DAYS_LEFT days! Please rotate soon."
elif [ $DAYS_LEFT -lt 30 ]; then
    echo "📅 Token expires in $DAYS_LEFT days"
else
    echo "✅ Token valid for $DAYS_LEFT more days"
fi

# Check if Neo4j is running
echo ""
echo "🔍 Checking Neo4j status..."
if nc -z neo4j.graphiti.local 7687 2>/dev/null; then
    echo "✅ Neo4j is running"
else
    echo "⚠️ Neo4j doesn't appear to be running on port 7687"
    echo "Please ensure Neo4j is running in OrbStack"
fi

# Export the token for Docker Compose
export OP_SERVICE_ACCOUNT_TOKEN

# Build and start the containers
echo ""
echo "🐳 Starting Docker containers in OrbStack..."
echo "Building image..."
docker compose build

echo ""
echo "Starting services..."
docker compose up -d

# Wait for health check
echo ""
echo "⏳ Waiting for health check..."
sleep 5

# Check container status
if docker compose ps | grep -q "graphiti-claude-code-mcp.*running.*healthy"; then
    echo "✅ MCP server is healthy and running"
else
    echo "⚠️ MCP server may not be healthy. Checking logs..."
    docker compose logs graphiti-mcp | tail -20
fi

echo ""
echo "🚀 Development environment ready!"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f graphiti-mcp    # View logs"
echo "  docker compose restart graphiti-mcp    # Restart server"
echo "  docker compose down                    # Stop services"
echo "  docker compose exec graphiti-mcp bash  # Enter container"
echo ""
echo "To run tests in OrbStack:"
echo "  docker compose exec graphiti-mcp pytest tests/"
