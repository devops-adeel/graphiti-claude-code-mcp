# Memory Pipeline Troubleshooting

## Quick Diagnosis

Run the health check first to identify issues:
```bash
make health-check-verbose
```

## Decision Tree

### Memory not captured?
```
├─ Check: FalkorDB connection (port 6379 or 6380)
│   └─ Test: redis-cli -p 6379 ping
├─ Check: OpenAI API key valid
│   └─ Test: echo $OPENAI_API_KEY (should start with sk-)
└─ Check: Entity extraction response
    └─ View logs: docker logs graphiti-claude-code-mcp
```

### Memory captured but not found?
```
├─ Check: Temporal decay (memories >30 days old become weak)
│   └─ Query: Search with include_historical=True
├─ Check: Status filter (DEPRECATED filtered out)
│   └─ Verify: Memory status is ACTIVE or SUPERSEDED
└─ Direct query in FalkorDB:
    redis-cli -p 6379
    GRAPH.QUERY shared_knowledge_graph "MATCH (n) RETURN n LIMIT 10"
```

### Memory found but wrong content?
```
├─ Check: Supersession chain
│   └─ Look for: supersedes field in metadata
├─ Check: Cross-domain linking
│   └─ Verify: gtd_link and cross_references fields
└─ Check: Metadata validation
    └─ Ensure: Pydantic models match expected structure
```

## Useful FalkorDB Queries

### Check if database exists
```bash
redis-cli -p 6379
GRAPH.LIST
```

### Find recent memories (last 24h)
```cypher
MATCH (e:Episode)
WHERE e.created_at > datetime() - duration({hours: 24})
RETURN e.content, e.created_at
ORDER BY e.created_at DESC
LIMIT 10
```

### Find memories by source
```cypher
MATCH (e:Episode)
WHERE e.source = 'claude_code'
RETURN e.content, e.uuid
LIMIT 10
```

### Check memory by UUID
```cypher
MATCH (e:Episode {uuid: 'your-uuid-here'})
RETURN e
```

### Find superseded memories
```cypher
MATCH (e:Episode)
WHERE e.episode_body CONTAINS '"status":"superseded"'
RETURN e.uuid, e.content
LIMIT 10
```

### Count all nodes and edges
```cypher
MATCH (n)
RETURN count(n) as node_count
UNION
MATCH ()-[r]->()
RETURN count(r) as edge_count
```

## Common Issues and Solutions

### Issue: "Valid OPENAI_API_KEY not found"
**Solution:**
1. Set in `~/.env`: `OPENAI_API_KEY=sk-...`
2. Or export: `export OPENAI_API_KEY='sk-...'`
3. Verify: `echo $OPENAI_API_KEY`

### Issue: "Cannot connect to FalkorDB"
**Solution:**
1. Check if running: `docker ps | grep falkor`
2. Test connection: `nc -zv localhost 6379`
3. For Docker: Use `falkordb.local` instead of `localhost`
4. Start FalkorDB: `docker run -d --name falkordb -p 6379:6379 falkordb/falkordb`

### Issue: "Memory captured but search returns nothing"
**Solution:**
1. Wait a few seconds (entity extraction is async)
2. Check temporal decay: `MEMORY_DECAY_FACTOR=0.95`
3. Try broader search terms
4. Use `include_historical=True` in search

### Issue: "Configuration mismatch with GTD Coach"
**Solution:**
1. Ensure both use same `GRAPHITI_GROUP_ID`
2. Verify database name matches
3. Check port numbers (6379 vs 6380)
4. Run: `make verify-config`

## Docker/OrbStack Specific

### Running health check in Docker
```bash
docker compose run --rm graphiti-mcp python scripts/health_check_memory.py --verbose
```

### Testing from OrbStack
```bash
# Use the test script that handles OrbStack networking
./scripts/test-in-docker.sh

# Or manually with proper host resolution
docker run --rm \
  --add-host falkordb.local:host-gateway \
  -v $(pwd):/app \
  graphiti-mcp-server:latest \
  python scripts/health_check_memory.py
```

### Debugging container issues
```bash
# View container logs
docker logs graphiti-claude-code-mcp -f

# Exec into container
docker exec -it graphiti-claude-code-mcp bash

# Test FalkorDB from inside container
docker exec graphiti-claude-code-mcp redis-cli -h falkordb.local -p 6379 ping
```

## Performance Monitoring

### Check memory usage
```bash
# FalkorDB memory usage
redis-cli -p 6379 INFO memory
```

### Monitor capture/retrieval times
```python
# Add timing to your code
import time
start = time.time()
result = await memory.add_memory(content)
print(f"Capture took {time.time() - start:.2f}s")
```

## When All Else Fails

1. **Restart everything:**
   ```bash
   docker compose down
   docker compose up -d
   ```

2. **Check the test suite:**
   ```bash
   pytest tests/test_memory.py -v
   ```

3. **Verify with health check:**
   ```bash
   make health-check-all
   ```

4. **Look at existing issues:**
   - Check GitHub issues
   - Review CLAUDE.md for known limitations
   - Check Graphiti version compatibility
