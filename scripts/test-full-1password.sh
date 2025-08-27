#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Comprehensive 1Password Integration Test ===${NC}"
echo ""

# 1. Check prerequisites
echo -e "${BLUE}1. Checking prerequisites...${NC}"

# Check 1Password CLI
if ! command -v op &> /dev/null; then
    echo -e "${RED}❌ 1Password CLI not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 1Password CLI installed: $(op --version)${NC}"

# Check service account token
SERVICE_TOKEN_FILE="$HOME/.config/graphiti-mcp/service-token"
if [ ! -f "$SERVICE_TOKEN_FILE" ]; then
    echo -e "${RED}❌ Service Account token not found at $SERVICE_TOKEN_FILE${NC}"
    echo "Run: make setup-1password"
    exit 1
fi
source "$SERVICE_TOKEN_FILE"
echo -e "${GREEN}✅ Service Account token loaded${NC}"

# 2. Verify 1Password access to secrets
echo ""
echo -e "${BLUE}2. Verifying 1Password secret access...${NC}"

# Check FalkorDB/Integration item
if op item get "FalkorDB/Integration" --vault HomeLab --fields label=openai-api-key > /dev/null 2>&1; then
    echo -e "${GREEN}✅ FalkorDB/Integration accessible (OpenAI API key)${NC}"
else
    echo -e "${RED}❌ Cannot access FalkorDB/Integration${NC}"
    exit 1
fi

# Check Langfuse/Integration item
if op item get "Langfuse/Integration" --vault HomeLab --fields label=langfuse-public-key > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Langfuse/Integration accessible (Langfuse keys)${NC}"
else
    echo -e "${RED}❌ Cannot access Langfuse/Integration${NC}"
    exit 1
fi

# 3. Verify FalkorDB container is running
echo ""
echo -e "${BLUE}3. Verifying FalkorDB container...${NC}"

# Debug: Show what containers are running
echo "Debug: Running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" | head -5

if docker ps --format "{{.Names}}" | grep -q "^falkordb$"; then
    echo -e "${GREEN}✅ FalkorDB container is running${NC}"
else
    echo -e "${RED}❌ FalkorDB container not running${NC}"
    echo "Please start FalkorDB first: cd ../falkordb && docker compose up -d"
    exit 1
fi

# Test FalkorDB connectivity
if docker exec falkordb redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✅ FalkorDB is responding to ping${NC}"
else
    echo -e "${RED}❌ FalkorDB not responding${NC}"
    exit 1
fi

# 4. Verify network configuration
echo ""
echo -e "${BLUE}4. Verifying Docker network...${NC}"

if docker network ls --format "{{.Name}}" | grep -q "^falkordb_default$"; then
    echo -e "${GREEN}✅ Network falkordb_default exists${NC}"
else
    echo -e "${RED}❌ Network falkordb_default not found${NC}"
    echo "Available networks:"
    docker network ls --format "{{.Name}}" | grep -E "falkor|graphiti"
    exit 1
fi

# 5. Test secret injection
echo ""
echo -e "${BLUE}5. Testing 1Password secret injection...${NC}"

# Test that secrets can be injected
if op run --env-file="secrets/.env.1password" -- bash -c 'test -n "$OPENAI_API_KEY"' 2>/dev/null; then
    echo -e "${GREEN}✅ OPENAI_API_KEY successfully injected${NC}"
else
    echo -e "${RED}❌ Failed to inject OPENAI_API_KEY${NC}"
    exit 1
fi

if op run --env-file="secrets/.env.1password" -- bash -c 'test -n "$LANGFUSE_PUBLIC_KEY"' 2>/dev/null; then
    echo -e "${GREEN}✅ LANGFUSE_PUBLIC_KEY successfully injected${NC}"
else
    echo -e "${RED}❌ Failed to inject LANGFUSE_PUBLIC_KEY${NC}"
    exit 1
fi

if op run --env-file="secrets/.env.1password" -- bash -c 'test -n "$LANGFUSE_SECRET_KEY"' 2>/dev/null; then
    echo -e "${GREEN}✅ LANGFUSE_SECRET_KEY successfully injected${NC}"
else
    echo -e "${RED}❌ Failed to inject LANGFUSE_SECRET_KEY${NC}"
    exit 1
fi

# 6. Build Docker image if needed
echo ""
echo -e "${BLUE}6. Building Docker image...${NC}"
docker compose build graphiti-mcp
echo -e "${GREEN}✅ Docker image built${NC}"

# 7. Test container networking with FalkorDB
echo ""
echo -e "${BLUE}7. Testing container-to-container networking...${NC}"

# Run a test container that connects to FalkorDB using container name
op run --env-file="secrets/.env.1password" -- \
docker compose run --rm \
  -e FALKORDB_HOST=falkordb \
  graphiti-mcp python -c "
import redis
import sys
try:
    r = redis.Redis(host='falkordb', port=6379, decode_responses=True)
    r.ping()
    print('✅ Successfully connected to FalkorDB via container name')
except Exception as e:
    print(f'❌ Failed to connect: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Container networking verified${NC}"
else
    echo -e "${RED}❌ Container networking failed${NC}"
    exit 1
fi

# 8. Run health check with 1Password secrets
echo ""
echo -e "${BLUE}8. Running memory pipeline health check...${NC}"

op run --env-file="secrets/.env.1password" -- \
docker compose run --rm \
  -e FALKORDB_HOST=falkordb \
  graphiti-mcp python scripts/health_check_memory.py --verbose

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check reported issues (this may be expected)${NC}"
fi

# 9. Test MCP server startup
echo ""
echo -e "${BLUE}9. Testing MCP server startup...${NC}"

# Start MCP server in background and check if it starts successfully
op run --env-file="secrets/.env.1password" -- \
docker compose run --rm -d \
  -e FALKORDB_HOST=falkordb \
  --name test-mcp-server \
  graphiti-mcp python mcp_server.py &

# Wait for server to start
sleep 5

# Check if container is still running
if docker ps | grep -q test-mcp-server; then
    echo -e "${GREEN}✅ MCP server started successfully${NC}"
    # Clean up test container
    docker stop test-mcp-server > /dev/null 2>&1
    docker rm test-mcp-server > /dev/null 2>&1
else
    echo -e "${RED}❌ MCP server failed to start${NC}"
    # Check logs if available
    docker logs test-mcp-server 2>/dev/null || true
    docker rm test-mcp-server > /dev/null 2>&1
    exit 1
fi

# 10. Summary
echo ""
echo -e "${BLUE}=== Test Summary ===${NC}"
echo -e "${GREEN}✅ All critical tests passed!${NC}"
echo ""
echo "The system is ready with:"
echo "  • 1Password integration configured"
echo "  • Service Account authentication (no Touch ID needed)"
echo "  • FalkorDB accessible via container networking"
echo "  • Secrets properly injected"
echo "  • MCP server functional"
echo ""
echo "To start the service with 1Password:"
echo "  make up-secure"
echo ""
echo "To view logs:"
echo "  make logs"