# Tutorial: Installing Graphiti Memory Layer

In this tutorial, you'll install and configure the Graphiti Claude Code MCP server. By the end, you'll have a working memory system integrated with Claude Code.

**Time required:** 15 minutes
**Prerequisites:** Docker, Claude Code CLI, 1Password account

## What You'll Build

A memory layer that:
- Captures coding patterns and solutions
- Shares knowledge with GTD Coach
- Integrates seamlessly with Claude Code

## Step 1: Clone and Build

Start by getting the code and building the Docker image:

```bash
# Clone the repository
git clone https://github.com/yourusername/graphiti-claude-code-mcp.git
cd graphiti-claude-code-mcp

# Build the Docker image
./scripts/build-docker.sh
```

You should see:
```
Successfully tagged graphiti-mcp-server:latest
```

## Step 2: Configure 1Password

Set up your service account token for secure secret management:

```bash
# Create config directory
mkdir -p ~/.config/graphiti-mcp

# Save your service token
cat > ~/.config/graphiti-mcp/service-token << 'EOF'
export OP_SERVICE_ACCOUNT_TOKEN="ops_eyJzaWduSW4iOi..."
EOF

# Secure the file
chmod 600 ~/.config/graphiti-mcp/service-token

# Test it works
source ~/.config/graphiti-mcp/service-token
echo $OP_SERVICE_ACCOUNT_TOKEN | head -c 20
```

Expected output: `ops_eyJzaWduSW4iOi...`

## Step 3: Create Configuration

Copy and customize the configuration file:

```bash
# Copy template
cp .env.graphiti.example ~/.config/graphiti-mcp/.env.graphiti

# Edit configuration
nano ~/.config/graphiti-mcp/.env.graphiti
```

Essential settings:
```bash
NEO4J_URI=bolt://neo4j.graphiti.local:7687  # For Neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here  # Set your Neo4j password
GRAPHITI_GROUP_ID=shared_knowledge
```

## Step 4: Add to Claude Code

Register the MCP server with Claude Code:

```bash
# Make wrapper executable
chmod +x scripts/claude-mcp-wrapper.sh

# Add the server (run from project directory)
claude mcp add graphiti-mcp -- $PWD/scripts/claude-mcp-wrapper.sh
```

You should see:
```
✓ Added MCP server 'graphiti-mcp'
```

## Step 5: Verify Installation

Test that everything works:

1. **Restart Claude Code:**
   ```bash
   # Quit and restart Claude Code
   cmd+q (in Claude Code)
   claude  # Restart from terminal
   ```

2. **Ask Claude Code to test the connection:**
   ```
   "What MCP servers are connected?"
   ```

   Expected response:
   ```
   I can see the graphiti-mcp server is connected with 9 tools available...
   ```

3. **Test memory capture:**
   ```
   "Search your memory for 'test connection'"
   ```

## Step 6: Verify Neo4j Connection

Ensure Neo4j is accessible:

```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Test connection
nc -z neo4j.graphiti.local 7687
# Should return: Connection successful

# Run health check
make health-check
```

Expected output:
```
✅ Configuration aligned with GTD Coach
✅ Neo4j connection successful
✅ Memory capture working
```

## What You've Accomplished

✅ Built the Docker image with all dependencies
✅ Configured secure secret management via 1Password
✅ Set up the shared knowledge graph connection
✅ Integrated the MCP server with Claude Code
✅ Verified the memory system is operational

## Next Steps

Now that installation is complete, continue to:
- [Tutorial: Capture Your First Memory](02-first-memory.md)
- [How to: Search and Retrieve Memories](../how-to/search-memories.md)
- [Explanation: Memory Philosophy](../explanation/memory-philosophy.md)

## Troubleshooting

If something didn't work:

1. **Docker issues:** Check `docker logs graphiti-mcp-server`
2. **Connection issues:** See [Troubleshooting Guide](../how-to/troubleshoot-common-issues.md)
3. **1Password issues:** Run `python scripts/check-sdk-health.py`

## Summary

You've successfully installed the Graphiti memory layer! The system is now:
- Capturing your coding patterns
- Preserving solution history
- Ready to enhance your development workflow

The memory layer will automatically capture patterns as you work with Claude Code, building a persistent knowledge base that improves over time.
