#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📁 Starting Graphiti MCP Server with .env.graphiti...${NC}"
echo "Using standard configuration (no 1Password)"

# Change to project directory
cd "$(dirname "$0")/.."

# Start Docker Compose with standard config
if docker compose up -d; then
    echo -e "${GREEN}✅ Services started successfully${NC}"
    echo ""
    echo "View logs with: make logs"
    echo "Stop with: make down"
else
    echo "Failed to start services"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check Docker is running"
    echo "  2. Verify .env.graphiti exists and is configured"
    echo "  3. Check FalkorDB is accessible"
    exit 1
fi