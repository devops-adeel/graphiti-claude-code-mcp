# Makefile Docker Compose Update

## Changes Made

### 1. Converted Direct Docker Run to Docker Compose Run

**Rationale:** Using `docker compose run` ensures consistency with service definitions, proper network configuration, and environment inheritance from docker-compose.yml.

#### Updated Commands:
- `test-connection`: Now uses `docker compose run --rm test-runner` instead of direct `docker run`
  - Automatically uses the correct network (`falkordb_default`)
  - No need to manually specify network configuration
  - Consistent with other service operations

### 2. Added Utility Service for Testing

Added a `test-runner` service to docker-compose.yml:
```yaml
test-runner:
  image: redis:7-alpine
  networks:
    - graphiti-network
  entrypoint: ["/bin/sh", "-c"]
```

This provides a flexible utility container for running various test commands without needing direct docker run.

### 3. Removed Deprecated Version Field

Removed `version: '3.8'` from docker-compose.yml as it's obsolete and was causing warnings.

## Benefits

1. **Network Consistency** - All commands now use the same network configuration
2. **Environment Inheritance** - Commands inherit all settings from docker-compose.yml
3. **Maintainability** - Single source of truth for service configuration
4. **Cleaner Commands** - No need to manually specify networks, volumes, or environment variables
5. **Dependency Management** - Respects service dependencies and relationships

## Commands That Remain with Docker Exec

The following commands appropriately use `docker exec` as they interact with running containers:
- `make shell` - Opens interactive shell in running container
- `make python` - Opens Python REPL in running container
- `make test-sharing` - Tests runtime configuration of the running service

## Testing

All updated commands have been tested and verified:
```bash
make test-connection  # ✅ Works with docker compose run
make test-health-1p   # ✅ Already using docker compose run
make test-mcp-1p      # ✅ Already using docker compose run
```
