# How to Troubleshoot Common Issues

This guide helps you solve the most common problems with the Graphiti Claude Code MCP server.

## Quick Health Check

Before troubleshooting specific issues, run the comprehensive health check:

```bash
make health-check          # Basic check
make health-check-verbose  # Detailed diagnostics
make health-check-fix      # Get fix suggestions
```

## Connection Issues

### Problem: Cannot connect to Neo4j

**Symptoms:**
- `Neo4jError: Failed to establish connection`
- `ServiceUnavailable: Unable to connect to bolt://`

**Solutions:**

1. Verify Neo4j is running:
```bash
docker ps | grep neo4j
cypher-shell -a bolt://localhost:7687  # Enter credentials when prompted
```

2. Check port configuration:
```bash
# Verify URI in .env.graphiti
grep NEO4J_URI ~/.config/graphiti-mcp/.env.graphiti
```

3. For OrbStack users, use domain name:
```bash
# In .env.graphiti, set:
NEO4J_URI=bolt://neo4j.graphiti.local:7687
NEO4J_USER=neo4j
```

### Problem: MCP server not found in Claude Code

**Solutions:**

1. Verify Docker image exists:
```bash
docker images | grep graphiti-mcp
```

2. Check Claude Code configuration:
```bash
# Verify MCP server is registered
grep graphiti-mcp ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

3. Restart Claude Code after configuration changes

## Memory Issues

### Problem: Memories not persisting

**Solutions:**

1. Check OpenAI API key validity:
```bash
# Test API key
python -c "import os; from openai import OpenAI; client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')); print('✅ API key valid')"
```

2. Verify group_id alignment:
```bash
# Should be 'shared_knowledge' or 'shared_gtd_knowledge'
grep GROUP_ID ~/.config/graphiti-mcp/.env.graphiti
```

3. Force flush pending memories:
```python
from graphiti_memory import get_shared_memory
memory = await get_shared_memory()
await memory.force_flush()
```

### Problem: Search returns no results

**Solutions:**

1. Check for special characters in query:
```python
# Remove problematic characters
query = query.replace("@", "").replace(":", " ")
```

2. Verify temporal decay settings:
```bash
# Default should be 0.95
grep DECAY_FACTOR ~/.config/graphiti-mcp/.env.graphiti
```

## SSL Certificate Issues (OrbStack/HTTPS)

### Problem: Certificate verification failed

**Symptoms:**
- `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed`

**Solutions:**

1. Extract and use OrbStack certificate:
```bash
# Extract from container
docker exec langfuse-prod-langfuse-web-1 cat /usr/local/share/ca-certificates/orbstack-root.crt > /tmp/orbstack-root.crt

# Set environment variable
export SSL_CERT_FILE=/tmp/orbstack-root.crt
```

2. For Python scripts, disable SSL verification (development only):
```python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

3. Configure httpx client:
```python
import httpx
client = httpx.Client(verify="/tmp/orbstack-root.crt")
```

## 1Password Integration Issues

### Problem: Cannot retrieve secrets

**Solutions:**

1. Verify service account token:
```bash
source ~/.config/graphiti-mcp/service-token
echo $OP_SERVICE_ACCOUNT_TOKEN | head -c 20  # Should show token prefix
```

2. Test 1Password SDK:
```bash
python scripts/check-sdk-health.py
```

3. Check item references:
```python
# Verify item exists in vault
op item get "Neo4j GraphitiCore" --vault "Personal"
```

## Docker Issues

### Problem: Container fails to start

**Solutions:**

1. Check logs:
```bash
docker logs $(docker ps -lq)
```

2. Verify network configuration:
```bash
docker network ls | grep graphiti
```

3. Rebuild with clean cache:
```bash
docker compose down
docker compose build --no-cache
docker compose up
```

## Performance Issues

### Problem: Slow memory operations

**Solutions:**

1. Check batch size configuration:
```bash
# Default is 50
grep BATCH_SIZE ~/.config/graphiti-mcp/.env.graphiti
```

2. Monitor token usage:
```python
from graphiti_memory import get_shared_memory
memory = await get_shared_memory()
print(f"Max tokens: {memory.max_tokens}")
```

3. Build smart indexes:
```python
memory = await get_shared_memory()
await memory.build_smart_index()
```

## Debug Commands

### View container logs
```bash
docker compose logs -f graphiti-mcp
```

### Test memory capture
```bash
make test-capture
```

### Verify MCP tools
```bash
# Use MCP Inspector or ask Claude Code:
"What MCP tools are available?"
```

### Check system health
```bash
make system-health
```

## Getting Help

If issues persist:

1. Run verbose diagnostics:
```bash
make health-check-all > diagnostics.log 2>&1
```

2. Check GitHub issues:
https://github.com/yourusername/graphiti-claude-code-mcp/issues

3. Review logs with context:
```bash
docker logs graphiti-mcp --tail 100 --follow
```
