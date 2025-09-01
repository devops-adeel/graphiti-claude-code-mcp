#!/bin/bash
# Verify Graphiti MCP Server is ready for Claude Code

set -e

echo "==================================="
echo "Graphiti MCP Server Verification"
echo "==================================="
echo ""

# Check Docker image
echo "1. Checking Docker image..."
if docker images | grep -q "graphiti-mcp-server.*latest"; then
    echo "   ✅ Docker image found: graphiti-mcp-server:latest"
    IMAGE_ID=$(docker images --format "{{.ID}}" graphiti-mcp-server:latest)
    IMAGE_AGE=$(docker images --format "{{.CreatedSince}}" graphiti-mcp-server:latest)
    echo "      ID: $IMAGE_ID"
    echo "      Age: $IMAGE_AGE"
else
    echo "   ❌ Docker image not found"
    echo "      Run: make build"
    exit 1
fi
echo ""

# Check 1Password token
echo "2. Checking 1Password configuration..."
SERVICE_TOKEN_FILE="$HOME/.config/graphiti-mcp/service-token"
if [ -f "$SERVICE_TOKEN_FILE" ]; then
    source "$SERVICE_TOKEN_FILE"
    if [ -n "$OP_SERVICE_ACCOUNT_TOKEN" ]; then
        echo "   ✅ Service token configured"
        # Extract expiry info if possible
        TOKEN_LENGTH=${#OP_SERVICE_ACCOUNT_TOKEN}
        echo "      Token length: $TOKEN_LENGTH characters"
    else
        echo "   ❌ Service token file exists but token not set"
        exit 1
    fi
else
    echo "   ❌ Service token not found at $SERVICE_TOKEN_FILE"
    echo "      Run: make setup-1password"
    exit 1
fi
echo ""

# Check configuration file
echo "3. Checking configuration file..."
CONFIG_FILE="$HOME/.config/graphiti-mcp/.env.graphiti"
if [ -f "$CONFIG_FILE" ]; then
    echo "   ✅ Configuration file found"
    # Check critical settings
    if grep -q "GRAPHITI_GROUP_ID=shared_knowledge" "$CONFIG_FILE"; then
        echo "      ✅ Group ID: shared_knowledge"
    else
        echo "      ⚠️  Group ID may not match GTD Coach"
    fi
    if grep -q "NEO4J_DATABASE=shared_gtd_knowledge" "$CONFIG_FILE"; then
        echo "      ✅ Database: shared_gtd_knowledge"
    else
        echo "      ⚠️  Database may not match GTD Coach"
    fi
else
    echo "   ⚠️  Configuration file not found"
    echo "      Using GTD Coach config from: ~/gtd-coach/.env.graphiti"
fi
echo ""

# Check wrapper script
echo "4. Checking wrapper script..."
WRAPPER_SCRIPT="scripts/claude-mcp-wrapper.sh"
if [ -f "$WRAPPER_SCRIPT" ] && [ -x "$WRAPPER_SCRIPT" ]; then
    echo "   ✅ Wrapper script is executable"
else
    echo "   ❌ Wrapper script not found or not executable"
    echo "      Run: chmod +x scripts/claude-mcp-wrapper.sh"
    exit 1
fi
echo ""

# Test MCP handshake
echo "5. Testing MCP server handshake..."
TEST_REQUEST='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"1.0.0","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
RESPONSE=$(echo "$TEST_REQUEST" | ./scripts/claude-mcp-wrapper.sh 2>/dev/null || echo "FAILED")

if echo "$RESPONSE" | grep -q '"name":"graphiti-claude-code-mcp"'; then
    echo "   ✅ MCP server responds correctly"
    SERVER_VERSION=$(echo "$RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo "      Version: $SERVER_VERSION"

    # Check if instructions are present
    if echo "$RESPONSE" | grep -q "AUTOMATIC BEHAVIORS"; then
        echo "      ✅ Instructions configured"
    else
        echo "      ⚠️  Instructions may not be configured"
    fi
else
    echo "   ❌ MCP server handshake failed"
    echo "      Debug with: docker logs graphiti-mcp-server"
    exit 1
fi
echo ""

# Check network connectivity
echo "6. Checking network configuration..."
if docker network ls | grep -q "orbstack-shared"; then
    echo "   ✅ OrbStack shared network exists"
else
    echo "   ⚠️  OrbStack shared network not found"
    echo "      Check that OrbStack is running"
fi
echo ""

# Generate Claude Code command
echo "==================================="
echo "✅ MCP Server is ready!"
echo "==================================="
echo ""
echo "Add to Claude Code with:"
echo ""
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
echo "  claude mcp add graphiti-mcp -- $PROJECT_DIR/scripts/claude-mcp-wrapper.sh"
echo ""
echo "Or manually add to Claude Code config:"
echo ""
echo '  {
    "mcpServers": {
      "graphiti-mcp": {
        "command": "'$PROJECT_DIR'/scripts/claude-mcp-wrapper.sh"
      }
    }
  }'
echo ""
echo "Then restart Claude Code and test with:"
echo '  "Search your memory for recent coding patterns"'
echo ""
