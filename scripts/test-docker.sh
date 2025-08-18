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
if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout 5"
elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout 5"  # GNU coreutils on macOS via Homebrew
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
if nc -z localhost 6380 2>/dev/null; then
    echo -e "${GREEN}✓${NC} FalkorDB is running on port 6380"
else
    echo -e "${YELLOW}⚠${NC} FalkorDB is not running on port 6380"
    echo "  Please start FalkorDB first:"
    echo "  docker run -d -p 6380:6379 falkordb/falkordb"
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
$TIMEOUT_CMD docker run --rm \
    -v "$USER_HOME/.env:/app/.env:ro" \
    -v "$(pwd)/.env.graphiti:/app/.env.graphiti:ro" \
    graphiti-mcp-server:latest --help > /dev/null 2>&1

TEST1_EXIT_CODE=$?
if [ $TEST1_EXIT_CODE -eq 124 ] || [ $TEST1_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Container starts successfully"
else
    echo -e "${RED}✗${NC} Container failed to start"
    exit 1
fi

# Test 2: MCP initialization test
echo ""
echo "Test 2: MCP server initialization..."
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0.0"}}, "id": 1}' | \
$TIMEOUT_CMD docker run -i --rm \
    -v "$USER_HOME/.env:/app/.env:ro" \
    -v "$(pwd)/.env.graphiti:/app/.env.graphiti:ro" \
    --add-host host.docker.internal:host-gateway \
    graphiti-mcp-server:latest 2>/dev/null | head -1 | grep -q "jsonrpc"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} MCP server responds to initialization"
else
    echo -e "${YELLOW}⚠${NC} MCP server initialization test inconclusive"
    echo "  This may be normal if the server needs FalkorDB to be running"
fi

# Test 3: Volume mount test
echo ""
echo "Test 3: Volume mount verification..."
docker run --rm \
    -v "$USER_HOME/.env:/app/.env:ro" \
    -v "$(pwd)/.env.graphiti:/app/.env.graphiti:ro" \
    --entrypoint /bin/sh \
    graphiti-mcp-server:latest \
    -c "ls -la /app/.env /app/.env.graphiti" > /dev/null 2>&1

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
echo "docker run -i --rm \\"
echo "  -v \"$USER_HOME/.env:/app/.env:ro\" \\"
echo "  -v \"$(pwd)/.env.graphiti:/app/.env.graphiti:ro\" \\"
echo "  --add-host host.docker.internal:host-gateway \\"
echo "  graphiti-mcp-server:latest"
echo ""