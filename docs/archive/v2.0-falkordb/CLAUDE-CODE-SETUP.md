# Claude Code MCP Server Setup Guide

## Quick Start

For experienced users, run this single command:
```bash
make claude-setup
```

Then follow the output instructions to add the server to Claude Code.

## Prerequisites

1. **Docker/OrbStack**: Ensure Docker or OrbStack is running
2. **FalkorDB**: Should be running on port 6379 (via OrbStack)
3. **1Password CLI**: Installed and configured with Service Account token
4. **Claude Code CLI**: Latest version with MCP support

## Step-by-Step Setup

### 1. Build the Docker Image

```bash
make build
```

This will:
- Build the `graphiti-mcp-server:latest` image
- Include all recent security updates (pip-audit)
- Configure SSL support for OrbStack
- Set up Langfuse integration

### 2. Configure 1Password Integration

```bash
make setup-1password
```

Or manually:
```bash
# Create config directory
mkdir -p ~/.config/graphiti-mcp

# Save your service token
echo 'export OP_SERVICE_ACCOUNT_TOKEN="your-token-here"' > ~/.config/graphiti-mcp/service-token
chmod 600 ~/.config/graphiti-mcp/service-token
```

### 3. Set Up Configuration

If you don't have a configuration file:
```bash
cp .env.graphiti.example ~/.config/graphiti-mcp/.env.graphiti
```

Edit the file to ensure:
```bash
GRAPHITI_GROUP_ID=shared_knowledge
FALKORDB_DATABASE=shared_gtd_knowledge
```

### 4. Verify Everything is Ready

```bash
make claude-test
# Or directly:
./scripts/verify-mcp-ready.sh
```

You should see all green checkmarks:
- ✅ Docker image found
- ✅ Service token configured
- ✅ Configuration file found
- ✅ Wrapper script is executable
- ✅ MCP server responds correctly
- ✅ Network configuration exists

### 5. Add to Claude Code

The verification script will show the exact command. It will look like:

```bash
claude mcp add graphiti-mcp -- /path/to/your/project/scripts/claude-mcp-wrapper.sh
```

### 6. Restart Claude Code

After adding the MCP server, restart Claude Code completely.

### 7. Test the Integration

In Claude Code, try these commands:
- "Search your memory for recent coding patterns"
- "What GTD tasks am I working on?"
- "Find cross-domain insights about Docker"

## How It Works

### Architecture

```
Claude Code
    ↓ (stdio/JSON-RPC)
Wrapper Script (claude-mcp-wrapper.sh)
    ↓ (Docker exec)
MCP Server Container
    ↓ (1Password SDK)
Secrets Manager
    ↓ (GraphQL)
Graphiti Core
    ↓ (Redis protocol)
FalkorDB (OrbStack)
```

### Key Components

1. **Wrapper Script**: Handles Docker execution and environment setup
2. **MCP Server**: Provides tools and resources to Claude Code
3. **Secrets Manager**: Manages 1Password integration securely
4. **Shared Memory**: Links with GTD Coach knowledge graph

### Memory Features

The MCP server provides Claude Code with:
- **Automatic Behaviors**: Proactive memory search and application
- **Pattern Capture**: TDD cycles, Docker fixes, command patterns
- **Cross-Domain Insights**: Links between GTD tasks and coding
- **Temporal Weighting**: Recent memories weighted higher (0.95 decay/day)
- **Langfuse Integration**: Analyze traces and patterns

## Troubleshooting

### MCP Server Not Appearing in Claude Code

1. Check the wrapper script is executable:
   ```bash
   chmod +x scripts/claude-mcp-wrapper.sh
   ```

2. Verify the full path is correct:
   ```bash
   realpath scripts/claude-mcp-wrapper.sh
   ```

3. Check Claude Code logs for errors

### Connection Errors

1. Verify Docker is running:
   ```bash
   docker ps
   ```

2. Check the network exists:
   ```bash
   docker network ls | grep orbstack-shared
   ```

3. Test the MCP handshake:
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
     ./scripts/claude-mcp-wrapper.sh
   ```

### 1Password Errors

1. Check token is set:
   ```bash
   source ~/.config/graphiti-mcp/service-token
   echo $OP_SERVICE_ACCOUNT_TOKEN | cut -c1-10
   ```

2. Test 1Password access:
   ```bash
   make test-1password
   ```

3. Verify secrets are accessible:
   ```bash
   op inject -i secrets/.env.1password
   ```

### Memory Not Working

1. Check FalkorDB connection:
   ```bash
   redis-cli -h localhost -p 6379 ping
   ```

2. Run health check:
   ```bash
   make health-check-verbose
   ```

3. Verify shared configuration:
   ```bash
   grep "shared_knowledge" ~/.config/graphiti-mcp/.env.graphiti
   ```

## Maintenance

### Update the Docker Image

```bash
# Pull latest changes
git pull

# Rebuild
make rebuild

# Verify
make claude-test
```

### Clean Up Old Images

```bash
make clean-images
```

### View Logs

```bash
# Container logs
docker logs graphiti-mcp-server -f

# MCP server logs (when running)
make logs
```

### Monitor Health

```bash
# Quick health check
make health-check

# Detailed with fixes
make health-check-all
```

## Security Notes

- **1Password Token**: Stored securely in `~/.config/graphiti-mcp/service-token`
- **Secrets**: Never logged or exposed through MCP
- **Network**: Isolated in Docker network
- **Permissions**: File permissions set to 600 for sensitive files

## Integration with GTD Coach

The MCP server shares a knowledge graph with GTD Coach:
- Same FalkorDB instance (port 6379)
- Shared group_id: `shared_knowledge`
- Bidirectional memory sharing
- Cross-domain insights

## Advanced Usage

### Manual Docker Run

```bash
source ~/.config/graphiti-mcp/service-token
docker run -i --rm \
  --network orbstack-shared \
  -e OP_SERVICE_ACCOUNT_TOKEN="$OP_SERVICE_ACCOUNT_TOKEN" \
  -v ~/.config/graphiti-mcp/.env.graphiti:/app/.env.graphiti:ro \
  graphiti-mcp-server:latest
```

### Development Mode

```bash
# Run locally without Docker
python mcp_server.py

# Run with debugging
LOG_LEVEL=DEBUG python mcp_server.py
```

### Custom Configuration

Create environment-specific configs:
```bash
# For OrbStack
cp config/environments/orbstack.yml ~/.config/graphiti-mcp/

# For cloud deployment
cp config/environments/cloud.yml ~/.config/graphiti-mcp/
```

## Support

- GitHub Issues: Report bugs and feature requests
- Documentation: See `/docs` directory
- Health Check: `make health-check-all`
- Verification: `make claude-test`
