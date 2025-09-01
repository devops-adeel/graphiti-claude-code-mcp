# Connect Claude Code to Your Neo4j Memory

Link Claude Code to your Neo4j memory graph so it can capture and retrieve your coding patterns automatically.

## Prerequisites

✅ Neo4j running (from [previous tutorial](01-neo4j-quickstart.md))
✅ Claude Code CLI installed
✅ 1Password configured
✅ Docker running

## Step 1: Configure the MCP Server

### Quick Setup (Recommended)

Run our automated setup script:

```bash
./scripts/setup-claude-mcp.sh
```

This script:
1. Builds the MCP server Docker image
2. Configures Claude Code settings
3. Tests the connection
4. Verifies tool availability

### Manual Setup (If Needed)

Create Claude Code configuration:

```bash
# Create config directory
mkdir -p ~/.claude

# Add MCP server configuration
cat > ~/.claude/claude_code_config.json << 'EOF'
{
  "mcpServers": {
    "graphiti-memory": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network", "graphiti-network",
        "-e", "NEO4J_URI=bolt://neo4j:7687",
        "-e", "NEO4J_USER=neo4j",
        "-e", "OPENAI_MODEL=gpt-4o-mini",
        "graphiti-mcp-server:latest"
      ]
    }
  }
}
EOF
```

## Step 2: Build the MCP Server

```bash
# Build the Docker image
docker build -t graphiti-mcp-server:latest .

# Verify the build
docker images | grep graphiti-mcp
```

Expected output:
```
graphiti-mcp-server   latest   abc123def   2 minutes ago   1.2GB
```

## Step 3: Start the MCP Server

```bash
# Start with docker compose
docker compose up -d graphiti-mcp

# Check it's running
docker ps | grep graphiti-mcp
```

You should see:
```
CONTAINER ID   IMAGE                    STATUS         NAMES
abc123def456   graphiti-mcp-server     Up 30 seconds  graphiti-mcp
```

## Step 4: Configure Environment Variables

Create your local configuration:

```bash
# Copy template
cp .env.graphiti.example ~/.config/graphiti-mcp/.env.graphiti

# Edit with your settings
nano ~/.config/graphiti-mcp/.env.graphiti
```

Update these values:
```env
# Neo4j Configuration (matching your setup)
NEO4J_URI=bolt://neo4j.graphiti.local:7687
NEO4J_USER=neo4j
# Password comes from 1Password

# Shared Knowledge Graph
GRAPHITI_GROUP_ID=shared_knowledge

# OpenAI (for entity extraction)
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Step 5: Test Claude Code Integration

### Restart Claude Code
```bash
# Quit Claude Code completely
# Then restart it to load MCP configuration
```

### Verify MCP Tools

In Claude Code, type:
```
What MCP tools do you have access to?
```

Expected response:
```
I have access to these MCP tools:
• capture_solution - Capture coding solutions
• capture_tdd_pattern - Record TDD cycles
• search_memory - Search the knowledge graph
• find_cross_insights - Discover connections
• get_gtd_context - Retrieve GTD tasks
• supersede_memory - Update old memories
• capture_command - Record command patterns
[... more tools]
```

### Test Memory Search

Try searching for memories:
```
Search my memory for "docker"
```

If no memories exist yet:
```
No memories found matching "docker"
(This is normal for a fresh installation)
```

## Step 6: Verify Neo4j Connection

### Check from MCP Server
```bash
# Test Neo4j connection from MCP container
docker exec graphiti-mcp python -c "
from graphiti_memory import get_shared_memory
import asyncio

async def test():
    memory = await get_shared_memory()
    print('✅ Connected to Neo4j!')

asyncio.run(test())
"
```

### Check Logs
```bash
# View MCP server logs
docker logs graphiti-mcp --tail 50
```

Look for:
```
INFO: Connected to shared knowledge graph: neo4j/shared_knowledge
INFO: MCP server ready on stdio
```

## Step 7: First Memory Capture

Test the full flow by solving a simple problem:

```python
# Create a test file with an error
echo 'print("Hello World"' > test.py

# Ask Claude to fix it
"Fix the syntax error in test.py"
```

Claude will:
1. Identify the missing parenthesis
2. Fix the error
3. **Capture the solution in memory**

Verify the capture:
```
"Did you save that fix to memory?"
```

## Understanding the Integration

### How It Works

```
Your Question → Claude Code → MCP Protocol → Graphiti Server → Neo4j
                                   ↑                              ↓
                              1Password ← Authentication ← Password
```

### What Happens Automatically

1. **Problem Detection** - Claude recognizes coding issues
2. **Solution Capture** - Fixes are saved to Neo4j
3. **Pattern Recognition** - Similar problems found quickly
4. **Temporal Weighting** - Recent solutions prioritized
5. **Cross-References** - Links to GTD tasks created

### Security Model

- **1Password** manages Neo4j password
- **MCP** requires approval for each action
- **Docker** isolates the server
- **Local only** - No cloud dependencies

## Troubleshooting

### MCP Tools Not Available?

```bash
# Check Claude Code config
cat ~/.claude/claude_code_config.json

# Verify MCP server is in the config
# Restart Claude Code after changes
```

### Connection Refused?

```bash
# Check Docker network
docker network ls | grep graphiti

# Ensure Neo4j and MCP are on same network
docker inspect graphiti-mcp | grep NetworkMode
```

### Authentication Failed?

```bash
# Verify 1Password item
op item get "Neo4j GraphitiCore"

# Check environment variable
docker exec graphiti-mcp env | grep NEO4J
```

### No Memories Captured?

```bash
# Check OpenAI API key
docker exec graphiti-mcp env | grep OPENAI

# Verify in logs
docker logs graphiti-mcp | grep "add_memory"
```

## Configuration Options

### Memory Behavior

Edit `~/.config/graphiti-mcp/.env.graphiti`:

```env
# Temporal decay (0.95 = 5% decay per day)
MEMORY_DECAY_FACTOR=0.95

# Include old memories in search
MEMORY_INCLUDE_HISTORICAL=false

# Batch size for processing
GRAPHITI_BATCH_SIZE=5
```

### Performance Tuning

For large codebases:
```env
# Increase batch size
GRAPHITI_BATCH_SIZE=20

# More connections
NEO4J_MAX_CONNECTIONS=50

# Longer timeouts
NEO4J_CONNECTION_TIMEOUT=60
```

## Verify Everything Works

Run the complete health check:

```bash
./scripts/check-mcp-integration.sh
```

Expected output:
```
✅ Neo4j running
✅ MCP server running
✅ 1Password configured
✅ Claude Code connected
✅ Memory capture working
✅ Search functioning
✅ Ready to build memories!
```

## What's Next?

Your Claude Code is now connected to Neo4j! Time to:

1. **[Capture Your First Memory](03-first-memory-capture.md)** - Start building knowledge
2. **[Explore Your Memories](04-exploring-memories.md)** - Query your graph
3. **[Optimize Performance](05-optimizing-performance.md)** - Tune for your needs

## Quick Reference

### Essential Commands

```bash
# Start everything
docker compose up -d

# Stop everything
docker compose down

# View logs
docker compose logs -f

# Restart MCP
docker compose restart graphiti-mcp

# Check health
./scripts/check-mcp-integration.sh
```

### Key Files

- `~/.claude/claude_code_config.json` - Claude Code MCP config
- `~/.config/graphiti-mcp/.env.graphiti` - Environment settings
- `docker-compose.yml` - Service definitions
- `mcp_server.py` - MCP server implementation

---

**🎉 Success!** Claude Code is now connected to your Neo4j memory graph. Every solution you create, every pattern you discover, will be automatically captured and made searchable for future use.
