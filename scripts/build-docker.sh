#!/bin/bash
# Build script for Graphiti MCP Server Docker image

set -e  # Exit on error

echo "========================================="
echo "Building Graphiti MCP Server Docker Image"
echo "========================================="

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo "Error: Dockerfile not found in $PROJECT_ROOT"
    exit 1
fi

# Check required files exist
echo "Checking required files..."
required_files=(
    "mcp_server.py"
    "mcp_stdio_wrapper.py"
    "graphiti_memory.py"
    "memory_models.py"
    "capture.py"
    "commands.py"
    "pyproject.toml"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Error: Required file $file not found"
        exit 1
    fi
done

echo "✓ All required files found"

# Build the Docker image
echo ""
echo "Building Docker image..."
docker build -f Dockerfile -t graphiti-mcp-server:latest .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Docker image built successfully!"
    echo "Image: graphiti-mcp-server:latest"
    echo ""
    echo "To verify the image:"
    echo "  docker images | grep graphiti-mcp-server"
    echo ""
    echo "To test the image:"
    echo "  ./scripts/test-docker.sh"
    echo ""
    echo "To use with Claude Code, see claude_config_example.json"
else
    echo ""
    echo "❌ Docker build failed"
    exit 1
fi
