#!/bin/bash
# Script to fix OrbStack configuration for graphiti-claude-code-mcp

echo "🔧 Fixing OrbStack configuration for graphiti-claude-code-mcp"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if FalkorDB is running
echo -e "\n${YELLOW}Checking FalkorDB status...${NC}"
if docker ps | grep -q falkordb; then
    echo -e "${GREEN}✅ FalkorDB container is running${NC}"
    FALKORDB_ID=$(docker ps | grep falkordb | awk '{print $1}')
    echo "   Container ID: $FALKORDB_ID"
else
    echo -e "${RED}❌ FalkorDB container is not running${NC}"
    echo "   Please start FalkorDB first:"
    echo "   docker run -p 6380:6379 -it --rm falkordb/falkordb:latest"
    exit 1
fi

# Test connectivity
echo -e "\n${YELLOW}Testing FalkorDB connectivity...${NC}"
if nc -zv localhost 6380 2>&1 | grep -q succeeded; then
    echo -e "${GREEN}✅ Connection to localhost:6380 successful${NC}"
else
    echo -e "${RED}❌ Cannot connect to localhost:6380${NC}"
    exit 1
fi

# Update .env.graphiti
echo -e "\n${YELLOW}Updating .env.graphiti...${NC}"
if [ -f .env.graphiti ]; then
    # Backup existing file
    cp .env.graphiti .env.graphiti.backup
    echo "   Backed up to .env.graphiti.backup"
    
    # Update or add FALKORDB_HOST for OrbStack container-to-container communication
    if grep -q "^FALKORDB_HOST=" .env.graphiti; then
        sed -i.tmp 's/^FALKORDB_HOST=.*/FALKORDB_HOST=falkordb.local/' .env.graphiti
    else
        echo "FALKORDB_HOST=falkordb.local" >> .env.graphiti
    fi
    
    # Update or add FALKORDB_PORT (use internal port for container-to-container)
    if grep -q "^FALKORDB_PORT=" .env.graphiti; then
        sed -i.tmp 's/^FALKORDB_PORT=.*/FALKORDB_PORT=6379/' .env.graphiti
    else
        echo "FALKORDB_PORT=6379" >> .env.graphiti
    fi
    
    rm -f .env.graphiti.tmp
    echo -e "${GREEN}✅ Updated .env.graphiti for OrbStack networking${NC}"
else
    echo -e "${RED}❌ .env.graphiti not found${NC}"
    echo "   Creating new .env.graphiti..."
    cat > .env.graphiti << EOF
# Shared Configuration for Testing
GRAPHITI_GROUP_ID=shared_gtd_knowledge
# OrbStack: Use falkordb.local for container-to-container communication
FALKORDB_HOST=falkordb.local
FALKORDB_PORT=6379
FALKORDB_DATABASE=shared_knowledge_graph

# OpenAI Configuration (will be overridden by ~/.env)
OPENAI_API_KEY=placeholder-set-in-home-env
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Memory Configuration
MEMORY_DECAY_FACTOR=0.95
MEMORY_INCLUDE_HISTORICAL=false
ENABLE_GTD_INTEGRATION=true
ENABLE_CROSS_REFERENCES=true
EOF
    echo -e "${GREEN}✅ Created .env.graphiti${NC}"
fi

# Note about ~/.env
echo -e "\n${YELLOW}Note about ~/.env${NC}"
echo "   Your ~/.env should contain your OPENAI_API_KEY"
echo "   The FalkorDB configuration is handled via .env.graphiti"
echo "   No changes needed to ~/.env for OrbStack networking"

# Rebuild Docker image if Dockerfile exists
if [ -f Dockerfile ]; then
    echo -e "\n${YELLOW}Rebuilding Docker image...${NC}"
    docker build -t graphiti-mcp-server:latest . > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Docker image rebuilt successfully${NC}"
    else
        echo -e "${RED}❌ Failed to rebuild Docker image${NC}"
        echo "   Run manually: docker build -t graphiti-mcp-server:latest ."
    fi
fi

# Test the configuration
echo -e "\n${YELLOW}Testing configuration...${NC}"
echo "Testing from host (localhost:6380)..."
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    python3 -c "
import os
# Test from host perspective using mapped port
try:
    from falkordb import FalkorDB
    db = FalkorDB(host='localhost', port=6380)
    graph = db.select_graph('test')
    print('✅ Python client connected via localhost:6380')
except Exception as e:
    print(f'❌ Python client failed: {e}')
" 2>/dev/null
else
    echo -e "${YELLOW}⚠️  Virtual environment not found, skipping Python test${NC}"
fi

# Test OrbStack domain resolution
echo "Testing OrbStack domain resolution..."
if ping -c 1 falkordb.local >/dev/null 2>&1; then
    echo -e "${GREEN}✅ falkordb.local is resolvable${NC}"
else
    echo -e "${YELLOW}⚠️  falkordb.local not resolvable - containers may have issues${NC}"
fi

echo -e "\n${GREEN}🎉 Configuration complete!${NC}"
echo -e "\nNext steps:"
echo "1. Restart any running MCP servers"
echo "2. Test with: python test_connection.py"
echo "3. If using Claude, restart the app to reload MCP servers"