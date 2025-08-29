#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_TOKEN_FILE="$HOME/.config/graphiti-mcp/service-token"

# Check if Service Account token exists
if [ ! -f "$SERVICE_TOKEN_FILE" ]; then
    echo -e "${RED}❌ Service Account token not found${NC}"
    echo "Location checked: $SERVICE_TOKEN_FILE"
    echo ""
    echo "To set up 1Password integration, run:"
    echo "  make setup-1password"
    echo ""
    echo "Or to use standard mode without 1Password:"
    echo "  make up"
    exit 1
fi

# Source the Service Account token
source "$SERVICE_TOKEN_FILE"

# Verify token is set and export it
if [ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]; then
    echo -e "${RED}❌ Service Account token file exists but token not set${NC}"
    echo "Check the contents of: $SERVICE_TOKEN_FILE"
    exit 1
fi

# CRITICAL: Export the token so Docker Compose can access it
export OP_SERVICE_ACCOUNT_TOKEN

echo -e "${BLUE}🔐 Starting Graphiti MCP Server with 1Password secrets...${NC}"
echo "Using Service Account (zero Touch ID required)"

# Change to project directory
cd "$(dirname "$0")/.."

# Inject secrets and start Docker Compose
# The token is now exported and available to both op run AND docker compose
echo "Injecting secrets from 1Password..."
if OP_SERVICE_ACCOUNT_TOKEN="$OP_SERVICE_ACCOUNT_TOKEN" op run --env-file=secrets/.env.1password -- docker compose up -d; then
    echo -e "${GREEN}✅ Services started successfully with 1Password secrets${NC}"
    echo ""
    echo "View logs with: make logs"
    echo "Stop with: make down"
else
    echo -e "${RED}❌ Failed to start services${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check Docker is running"
    echo "  2. Verify FalkorDB is accessible at falkordb.local"
    echo "  3. Run: make test-1password"
    exit 1
fi
