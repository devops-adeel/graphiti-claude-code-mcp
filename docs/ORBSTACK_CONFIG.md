# OrbStack Configuration for graphiti-claude-code-mcp

This document covers the specific configuration required when using OrbStack instead of Docker Desktop for running FalkorDB and the graphiti-claude-code MCP server.

## Overview

OrbStack provides enhanced Docker container networking with features like:
- Custom domain names for containers (`container.orb.local`)
- Direct IP access from macOS
- Automatic port detection for web services
- Better localhost integration

## FalkorDB with OrbStack

### Port Configuration

FalkorDB runs with the following port mapping:
- **Internal port**: 6379 (default Redis/FalkorDB port)
- **External port**: 6380 (mapped to avoid conflicts)
- **Container**: `falkordb`

### Access Methods

With OrbStack, FalkorDB can be accessed via:

1. **Standard Docker port mapping**: `localhost:6380`
2. **OrbStack custom domain**: `falkordb.local:6379` 
3. **OrbStack automatic domain**: `falkordb.orb.local:6379`
4. **Direct container IP**: `192.168.148.2:6379` (IP may vary)

## Configuration Files

### .env.graphiti

```bash
# Shared Configuration for Testing
GRAPHITI_GROUP_ID=shared_gtd_knowledge
# OrbStack: Use localhost with mapped port or falkordb.local with internal port
FALKORDB_HOST=localhost
FALKORDB_PORT=6380
FALKORDB_DATABASE=shared_knowledge_graph
```

### ~/.env (User home directory)

For Docker containers to connect properly:

```bash
# FalkorDB configuration for Docker containers
# When running in Docker, use host.docker.internal for macOS/Windows
HOST_OS=darwin
FALKORDB_HOST=host.docker.internal
FALKORDB_PORT=6380
```

## Docker Container Networking

When the MCP server runs in a Docker container, it needs special configuration:

1. **Inside Docker containers**, `localhost` refers to the container itself, not the host
2. **On macOS with OrbStack**, use `host.docker.internal` to reach the host machine
3. The `mcp_stdio_wrapper.py` automatically handles this conversion when `HOST_OS=darwin`

## Testing Connection

Use the provided `test_connection.py` script to verify connectivity:

```bash
source venv/bin/activate
python test_connection.py
```

Expected output:
```
Testing: localhost with mapped port
  Host: localhost
  Port: 6380
  ✅ FalkorDB client connected
  ✅ SharedMemory initialized
  ✅ Search executed (found X results)

🎉 SUCCESS: localhost with mapped port works!
```

## Troubleshooting

### Connection Refused Errors

If you see "Error 111 connecting to localhost:6380. Connection refused":

1. **Verify FalkorDB is running**:
   ```bash
   docker ps | grep falkor
   ```

2. **Test connectivity directly**:
   ```bash
   nc -zv localhost 6380
   nc -zv falkordb.local 6379
   ```

3. **Check Docker logs**:
   ```bash
   docker logs falkordb
   ```

### MCP Server in Docker

If the MCP server runs in Docker and can't connect:

1. **Ensure HOST_OS is set**: The container needs `HOST_OS=darwin` in environment
2. **Check the wrapper script**: `mcp_stdio_wrapper.py` should convert `localhost` to `host.docker.internal`
3. **Rebuild the Docker image** after any changes:
   ```bash
   docker build -t graphiti-mcp-server:latest .
   ```

### OrbStack-Specific Features

1. **Custom domains**: Set via Docker labels
   ```yaml
   labels:
     - "dev.orbstack.domains=falkordb.local"
   ```

2. **Direct IP access**: Find container IP with:
   ```bash
   docker inspect falkordb | grep IPAddress
   ```

3. **Network settings**: Ensure "Allow access to container domains & IPs" is enabled in OrbStack Settings → Network

## Best Practices

1. **Use explicit configuration**: Always set `FALKORDB_HOST` and `FALKORDB_PORT` explicitly
2. **Test before deploying**: Use `test_connection.py` to verify setup
3. **Monitor logs**: Check both FalkorDB and MCP server logs for issues
4. **Keep ports consistent**: Use 6380 for external access to avoid conflicts

## Summary

The key to successful OrbStack integration is understanding the networking differences:
- Local processes use `localhost:6380`
- Docker containers use `host.docker.internal:6380`
- OrbStack provides additional access via custom domains

With proper configuration in `.env.graphiti` and `~/.env`, the graphiti-claude-code MCP server will work seamlessly with FalkorDB running in OrbStack.