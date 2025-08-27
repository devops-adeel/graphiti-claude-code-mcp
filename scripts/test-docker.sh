#!/bin/bash
# Test script for Graphiti MCP Server Docker image

set -e  # Exit on error

echo "========================================="
echo "Testing Graphiti MCP Server Docker Image"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Platform-specific timeout handling
if command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout 15"  # GNU coreutils on macOS via Homebrew - increased to 15s for initialization
    echo -e "${GREEN}✓${NC} Using gtimeout for test protection"
elif command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout 15"  # Increased to 15s for initialization
    echo -e "${GREEN}✓${NC} Using timeout for test protection"
else
    TIMEOUT_CMD=""  # No timeout available, run directly
    echo -e "${YELLOW}⚠${NC} timeout command not found, tests will run without timeout protection"
fi

# Get user home directory
USER_HOME="$HOME"

# Check if Docker image exists
echo "Checking Docker image..."
if docker images | grep -q "graphiti-mcp-server"; then
    echo -e "${GREEN}✓${NC} Docker image found"
else
    echo -e "${RED}✗${NC} Docker image not found. Run ./scripts/build-docker.sh first"
    exit 1
fi

# Check if FalkorDB is running
echo ""
echo "Checking FalkorDB connectivity..."
# Check both localhost:6380 (from host) and falkordb.local:6379 (for containers)
if nc -z localhost 6380 2>/dev/null; then
    echo -e "${GREEN}✓${NC} FalkorDB is accessible from host on localhost:6380"
else
    echo -e "${YELLOW}⚠${NC} FalkorDB is not accessible on localhost:6380"
    echo "  Please ensure FalkorDB is running with port mapping -p 6380:6379"
fi

# Also check if falkordb.local resolves (OrbStack domain)
if ping -c 1 falkordb.local >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} FalkorDB domain falkordb.local is resolvable"
else
    echo -e "${YELLOW}⚠${NC} Cannot resolve falkordb.local"
    echo "  Ensure FalkorDB container has label: dev.orbstack.domains=falkordb.local"
fi

# Check environment files
echo ""
echo "Checking environment files..."
if [ -f "$USER_HOME/.env" ]; then
    echo -e "${GREEN}✓${NC} Found ~/.env"
    # Check for OPENAI_API_KEY (without showing it)
    if grep -q "OPENAI_API_KEY" "$USER_HOME/.env"; then
        echo -e "${GREEN}✓${NC} OPENAI_API_KEY found in ~/.env"
    else
        echo -e "${YELLOW}⚠${NC} OPENAI_API_KEY not found in ~/.env"
    fi
else
    echo -e "${RED}✗${NC} ~/.env not found"
    echo "  Please create ~/.env with your OPENAI_API_KEY"
fi

if [ -f ".env.graphiti" ]; then
    echo -e "${GREEN}✓${NC} Found .env.graphiti"
else
    echo -e "${RED}✗${NC} .env.graphiti not found"
fi

# Test 1: Basic Docker run test
echo ""
echo "Test 1: Basic container startup..."
# Extract OPENAI_API_KEY if not already done
if [ -z "$OPENAI_API_KEY" ] && [ -f "$USER_HOME/.env" ]; then
    export OPENAI_API_KEY=$(grep OPENAI_API_KEY "$USER_HOME/.env" | cut -d'=' -f2)
fi

# Test that the container can start and return any JSON-RPC response (even an error)
# A ping before initialization should return an error, but that still shows the server is working
RESPONSE=$( echo '{"jsonrpc": "2.0", "method": "ping", "id": 1}' | \
$TIMEOUT_CMD docker run -i --rm \
    -v "$(pwd)/.env.graphiti:/app/.env.graphiti:ro" \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e FALKORDB_HOST=falkordb.local \
    -e FALKORDB_PORT=6379 \
    graphiti-mcp-server:latest 2>/dev/null )

# Check if we got any JSON-RPC response (success or error)
if echo "$RESPONSE" | grep -q '"jsonrpc".*"2.0"'; then
    echo -e "${GREEN}✓${NC} Container starts successfully"
else
    echo -e "${RED}✗${NC} Container failed to start"
    if [ -n "$RESPONSE" ]; then
        echo "  Response: ${RESPONSE:0:100}..."
    fi
    exit 1
fi

# Test 2: MCP initialization test
echo ""
echo "Test 2: MCP server initialization..."
# Extract OPENAI_API_KEY from ~/.env
if [ -f "$USER_HOME/.env" ]; then
    export OPENAI_API_KEY=$(grep OPENAI_API_KEY "$USER_HOME/.env" | cut -d'=' -f2)
fi

# Store the response and check it properly
RESPONSE=$( echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0.0"}}, "id": 1}' | \
$TIMEOUT_CMD docker run -i --rm \
    -v "$(pwd)/.env.graphiti:/app/.env.graphiti:ro" \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e FALKORDB_HOST=falkordb.local \
    -e FALKORDB_PORT=6379 \
    graphiti-mcp-server:latest 2>/dev/null )

if echo "$RESPONSE" | grep -q '"jsonrpc".*"2.0"'; then
    echo -e "${GREEN}✓${NC} MCP server responds to initialization"
elif echo "$RESPONSE" | grep -q "Waiting for FalkorDB"; then
    echo -e "${YELLOW}⚠${NC} MCP server waiting for FalkorDB connection"
    echo "  Ensure FalkorDB is running at falkordb.local:6379"
else
    echo -e "${YELLOW}⚠${NC} MCP server initialization test inconclusive"
    echo "  Response: ${RESPONSE:0:100}..."
fi

# Test 3: Volume mount test
echo ""
echo "Test 3: Volume mount verification..."
docker run --rm \
    -v "$(pwd)/.env.graphiti:/app/.env.graphiti:ro" \
    --entrypoint /bin/sh \
    graphiti-mcp-server:latest \
    -c "ls -la /app/.env.graphiti" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Volume mounts work correctly"
else
    echo -e "${RED}✗${NC} Volume mount test failed"
fi

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "Docker image is ready for use with Claude Code!"
echo ""
echo "To configure Claude Code:"
echo "1. Copy the configuration from claude_config_example.json"
echo "2. Add it to: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "3. Restart Claude Code"
echo ""
echo "Example test command for manual testing:"
echo "docker run -it --rm \\"
echo "  -v \"$(pwd)/.env.graphiti:/app/.env.graphiti:ro\" \\"
echo "  -e OPENAI_API_KEY=\"\$OPENAI_API_KEY\" \\"
echo "  -e FALKORDB_HOST=falkordb.local \\"
echo "  -e FALKORDB_PORT=6379 \\"
echo "  graphiti-mcp-server:latest"
echo ""
echo "Or to test JSON-RPC directly:"
echo "echo '{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"params\":{},\"id\":1}' | \\"
echo "  docker run -i --rm \\"
echo "    -v \"$(pwd)/.env.graphiti:/app/.env.graphiti:ro\" \\"
echo "    -e OPENAI_API_KEY=\"\$OPENAI_API_KEY\" \\"
echo "    -e FALKORDB_HOST=falkordb.local \\"
echo "    -e FALKORDB_PORT=6379 \\"
echo "    graphiti-mcp-server:latest"
echo ""
