#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CACHE_FILE=".direnv/cache.env"
ENV_FILE=".env"
SERVICE_TOKEN_FILE="$HOME/.config/graphiti-mcp/service-token"

echo -e "${BLUE}🔄 Preparing environment for Docker Compose...${NC}"

# Step 1: Ensure direnv cache exists
if [ ! -f "$CACHE_FILE" ]; then
    echo -e "${YELLOW}⚠️  Direnv cache not found, refreshing from 1Password...${NC}"

    # Create cache directory
    mkdir -p .direnv

    # Load from 1Password
    if ~/.config/1password/op-env load > /dev/null 2>&1; then
        if [ -f /tmp/.env ]; then
            cp /tmp/.env "$CACHE_FILE"
            echo -e "${GREEN}✅ Cache created from 1Password${NC}"
        else
            echo -e "${RED}❌ Failed to generate environment file${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Failed to load from 1Password${NC}"
        exit 1
    fi
fi

# Step 2: Export all variables to current shell
echo -e "${BLUE}📥 Loading environment variables...${NC}"
set -a  # Mark all new variables for export
source "$CACHE_FILE"
set +a  # Turn off auto-export

# Step 3: Create .env file for Docker Compose
echo -e "${BLUE}📄 Creating .env file for Docker Compose...${NC}"
cp "$CACHE_FILE" "$ENV_FILE"

# Step 4: Ensure Service Account Token is exported
if [ -f "$SERVICE_TOKEN_FILE" ]; then
    source "$SERVICE_TOKEN_FILE"
    export OP_SERVICE_ACCOUNT_TOKEN
    echo -e "${GREEN}✅ Service Account token loaded${NC}"
else
    echo -e "${YELLOW}⚠️  Service Account token not found${NC}"
    echo "  The container may not be able to access 1Password SDK"
fi

# Step 5: Validate critical variables
MISSING_VARS=()
CRITICAL_VARS=(
    "NEO4J_PASSWORD"
    "GRAPHITI_GROUP_ID"
    "OPENAI_API_KEY"
    "LANGFUSE_PUBLIC_KEY"
    "LANGFUSE_SECRET_KEY"
)

for var in "${CRITICAL_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing critical environment variables:${NC}"
    printf '%s\n' "${MISSING_VARS[@]}" | sed 's/^/  - /'
    echo ""
    echo "To fix:"
    echo "  1. Check 1Password has these variables"
    echo "  2. Update ~/.config/1password/secrets.env.template"
    echo "  3. Run: rm -rf .direnv/cache.env && direnv reload"
    exit 1
fi

echo -e "${GREEN}✅ Environment ready for Docker Compose${NC}"
echo ""
echo "Variables loaded:"
echo "  NEO4J_PASSWORD: ${NEO4J_PASSWORD:+[SET]}"
echo "  GRAPHITI_GROUP_ID: ${GRAPHITI_GROUP_ID}"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:+[SET]}"
echo "  LANGFUSE_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY:+[SET]}"
echo "  OP_SERVICE_ACCOUNT_TOKEN: ${OP_SERVICE_ACCOUNT_TOKEN:+[SET]}"

# Step 6: Run Docker Compose with the action provided as arguments
if [ $# -gt 0 ]; then
    echo ""
    echo -e "${BLUE}🐳 Running: docker compose $@${NC}"
    exec docker compose "$@"
else
    echo ""
    echo "Usage: $0 [docker-compose-args]"
    echo "Example: $0 up -d"
    echo "         $0 build --no-cache"
    echo "         $0 logs -f"
fi
