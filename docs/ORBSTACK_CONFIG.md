# OrbStack Configuration for graphiti-claude-code-mcp

This document covers the specific configuration required when using OrbStack instead of Docker Desktop for running FalkorDB and the graphiti-claude-code MCP server.

## Overview

OrbStack provides enhanced Docker container networking with features like:
- Custom domain names for containers (`container.local`)
- Direct IP access from macOS
- Automatic port detection for web services
- Better localhost integration

## Key Configuration Change

The primary difference when using OrbStack is that containers communicate using OrbStack's custom domains (`falkordb.local`) instead of Docker Desktop's `host.docker.internal`.

## FalkorDB with OrbStack

### Port Configuration

FalkorDB runs with the following port mapping:
- **Internal port**: 6379 (default Redis/FalkorDB port)
- **External port**: 6380 (mapped to avoid conflicts with local Redis)
- **Container name**: `falkordb`
- **OrbStack domain**: `falkordb.local`

### Docker Compose Label

To enable the custom domain in OrbStack, add this label to your FalkorDB container:
```yaml
labels:
  - "dev.orbstack.domains=falkordb.local"
```

### Access Methods

With OrbStack, FalkorDB can be accessed via:

1. **From host machine**: `localhost:6380` (standard Docker port mapping)
2. **From containers**: `falkordb.local:6379` (OrbStack domain with internal port)
3. **Direct container IP**: Available but not recommended as IPs can change

## Configuration Files

### .env.graphiti

```bash
# Shared Configuration for graphiti-claude-code-mcp
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
```

### docker-compose.yml

Key environment variables for container communication:
```yaml
environment:
  - FALKORDB_HOST=${FALKORDB_HOST:-falkordb.local}
  - FALKORDB_PORT=${FALKORDB_PORT:-6379}
  - OPENAI_API_KEY=${OPENAI_API_KEY}  # Pass API key directly
```

### ~/.env (User home directory)

Your personal API keys:
```bash
OPENAI_API_KEY=your-actual-api-key-here
```

## Container Networking Details

### MCP Server in Docker

When the MCP server runs in a Docker container with OrbStack:

1. **Container-to-container**: Use `falkordb.local:6379`
2. **No host.docker.internal needed**: OrbStack's domains work directly
3. **Environment variables**: Pass `OPENAI_API_KEY` directly to containers

### Python Buffering Fix

The `mcp_stdio_wrapper.py` includes buffering controls for Docker:
```python
# Ensure unbuffered output for Docker
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
```

## Testing

### Test Script Updates

The `scripts/test-docker.sh` script has been updated for OrbStack:
- Removed `--add-host host.docker.internal:host-gateway` flags
- Uses `falkordb.local:6379` for container communication
- Passes `OPENAI_API_KEY` as environment variable
- Increased timeout to 15s for initialization

### Running Tests

1. **Test FalkorDB connectivity**:
   ```bash
   nc -zv localhost 6380  # From host
   ping falkordb.local    # Check domain resolution
   ```

2. **Run Docker test script**:
   ```bash
   ./scripts/test-docker.sh
   ```

3. **Test MCP server locally**:
   ```bash
   source venv/bin/activate
   python test_connection.py
   ```

## Troubleshooting

### Connection Issues

If containers can't connect to FalkorDB:

1. **Verify FalkorDB is running**:
   ```bash
   docker ps | grep falkor
   ```

2. **Check OrbStack domain**:
   ```bash
   # Should resolve to container IP
   ping falkordb.local
   ```

3. **Verify port mapping**:
   ```bash
   # From host machine
   redis-cli -h localhost -p 6380 ping
   ```

### MCP Server Issues

If the MCP server appears unresponsive:

1. **Check Python buffering**: Ensure `PYTHONUNBUFFERED=1` is set
2. **Monitor logs**: 
   ```bash
   docker compose logs -f graphiti-mcp
   ```
3. **Test connectivity from container**:
   ```bash
   docker run --rm redis:7-alpine redis-cli -h falkordb.local -p 6379 ping
   ```

## OrbStack vs Docker Desktop

### Key Differences

| Feature | Docker Desktop | OrbStack |
|---------|---------------|----------|
| Host access from container | `host.docker.internal` | Not needed (use custom domains) |
| Container domains | Not available | `container.local` via labels |
| Network setup | Manual `--add-host` flags | Automatic with domains |
| Performance | Good | Better (native virtualization) |

### Migration Checklist

When switching from Docker Desktop to OrbStack:

1. ✅ Update `FALKORDB_HOST` to `falkordb.local`
2. ✅ Use internal port (6379) for container communication
3. ✅ Remove `--add-host` flags from Docker commands
4. ✅ Add OrbStack domain labels to containers
5. ✅ Pass environment variables directly (not via volume mounts)

## Best Practices

1. **Use explicit domains**: Always use `falkordb.local` for clarity
2. **Consistent ports**: Keep 6380 for external, 6379 for internal
3. **Environment variables**: Pass secrets directly, not through mounted files
4. **Buffering controls**: Always set `PYTHONUNBUFFERED=1` for Python in Docker
5. **Health checks**: Use OrbStack domains in health check scripts

## Summary

OrbStack simplifies Docker networking with custom domains, eliminating the need for `host.docker.internal` workarounds. The key configuration points are:

- Containers use `falkordb.local:6379` for FalkorDB access
- Host machines use `localhost:6380`
- Environment variables are passed directly to containers
- Python buffering is explicitly disabled for proper stdio handling

With these configurations, the graphiti-claude-code MCP server works seamlessly with FalkorDB running in OrbStack.