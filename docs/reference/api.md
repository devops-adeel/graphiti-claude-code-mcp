# API Reference

## Core Classes

### SharedMemory

The main interface to the memory system.

```python
from graphiti_memory import get_shared_memory

memory = await get_shared_memory()
```

#### Methods

##### add_memory(content, source)
Add a new memory to the knowledge graph.

```python
await memory.add_memory(
    content={"solution": "Use Docker healthchecks"},
    source="claude_code"
)
```

**Parameters:**
- `content` (dict): Memory data to store
- `source` (str): Source identifier ("claude_code", "gtd_coach")

**Returns:** Memory ID (str)

##### search_with_temporal_weight(query, include_historical, filter_source)
Search memories with temporal decay scoring.

```python
results = await memory.search_with_temporal_weight(
    query="docker error",
    include_historical=False,
    filter_source="claude_code"
)
```

**Parameters:**
- `query` (str): Search query
- `include_historical` (bool): Include memories >30 days old
- `filter_source` (str): Filter by source system

**Returns:** List[SearchResultWrapper]

##### supersede_memory(old_id, new_content, reason)
Create new memory that replaces an old one.

```python
await memory.supersede_memory(
    old_id="mem_123",
    new_content={"solution": "Better approach"},
    reason="Optimized for performance"
)
```

**Parameters:**
- `old_id` (str): ID of memory to supersede
- `new_content` (dict): New memory content
- `reason` (str): Reason for supersession

**Returns:** New memory ID (str)

##### find_cross_domain_insights(topic)
Find connections between coding and GTD domains.

```python
insights = await memory.find_cross_domain_insights("deployment")
```

**Parameters:**
- `topic` (str): Topic to explore

**Returns:** List[Dict] with cross-references

### PatternCapture

Captures specific coding patterns.

```python
from capture import get_pattern_capture

capture = await get_pattern_capture()
```

#### Methods

##### capture_tdd_cycle(test_code, implementation, refactored, feature_name)
Capture test-driven development cycle.

```python
await capture.capture_tdd_cycle(
    test_code="def test_auth(): assert False",
    implementation="def auth(): return True",
    feature_name="authentication"
)
```

**Returns:** Memory ID (str)

##### capture_deployment_solution(error, solution, context, docker_compose)
Capture deployment fixes.

```python
await capture.capture_deployment_solution(
    error="Connection refused",
    solution="Use host.docker.internal",
    context={"platform": "macos"},
    docker_compose=compose_yaml
)
```

**Returns:** Memory ID (str)

##### capture_session_summary(narrative, problems_solved, patterns_discovered, gtd_connections, follow_up_items, user_confirmed)
Capture comprehensive session summary.

```python
await capture.capture_session_summary(
    narrative="Session focused on Docker fixes",
    problems_solved=[{"description": "SSL error", "solution": "Updated cert"}],
    patterns_discovered=[{"type": "docker", "description": "Multi-stage builds"}],
    gtd_connections=["@computer", "@deployment"],
    follow_up_items=["Add health checks"],
    user_confirmed=True
)
```

**Returns:** Memory ID (str)

### SearchResultWrapper

Wraps search results with computed scores.

#### Properties

- `score` (float): Final computed score with temporal decay
- `metadata` (dict): Memory metadata
- `status` (str): Memory status (ACTIVE, SUPERSEDED, etc.)
- `fact` (str): Core fact/content
- `uuid` (str): Memory identifier

#### Methods

##### to_dict()
Convert to dictionary for serialization.

```python
result_dict = result.to_dict()
```

## MCP Tools

### capture_solution
Capture a coding solution.

```json
{
  "error": "Module not found",
  "solution": "Add to requirements.txt",
  "context": {"file": "main.py"}
}
```

### search_memory
Search the knowledge graph.

```json
{
  "query": "docker ssl error",
  "filter_source": "claude_code"
}
```

### find_cross_insights
Find cross-domain connections.

```json
{
  "topic": "deployment strategies"
}
```

### supersede_memory
Update an existing memory.

```json
{
  "old_id": "mem_123",
  "new_content": {"solution": "Improved approach"},
  "reason": "Performance optimization"
}
```

## Memory States

### Status Values

| Status | Description | Score Modifier |
|--------|-------------|---------------|
| `ACTIVE` | Current best practice | 1.0 |
| `SUPERSEDED` | Replaced by better solution | 0.3 |
| `HISTORICAL` | >30 days old but relevant | 0.1 |
| `DEPRECATED` | No longer applicable | 0.0 |

### State Transitions

```
ACTIVE → SUPERSEDED (via supersede_memory)
ACTIVE → HISTORICAL (after 30 days)
HISTORICAL → DEPRECATED (manual intervention)
```

## Temporal Scoring

### Formula

```python
final_score = base_score × (0.95 ^ age_days) × status_weight
```

### Examples

| Age | Decay Factor | Status | Final Score (base=1.0) |
|-----|-------------|---------|------------------------|
| 0 days | 1.00 | ACTIVE | 1.00 |
| 7 days | 0.70 | ACTIVE | 0.70 |
| 30 days | 0.21 | HISTORICAL | 0.02 |
| 90 days | 0.006 | DEPRECATED | 0.00 |

## Configuration

### Environment Variables

```bash
# Memory behavior
MEMORY_DECAY_FACTOR=0.95       # Daily decay rate
GRAPHITI_BATCH_SIZE=50          # Episodes per flush
GRAPHITI_GROUP_ID=shared_knowledge

# Features
ENABLE_GTD_INTEGRATION=true
ENABLE_CROSS_REFERENCES=true
MEMORY_INCLUDE_HISTORICAL=false

# Connection
FALKORDB_HOST=falkordb.local
FALKORDB_PORT=6379
FALKORDB_DATABASE=shared_knowledge
```

### Python Configuration

```python
# Override defaults
memory = SharedMemory()
memory.decay_factor = 0.90  # Faster decay
memory.batch_size = 100     # Larger batches
memory.max_tokens = 10000   # More context
```

## Error Handling

### Common Exceptions

| Exception | Cause | Solution |
|-----------|-------|----------|
| `ConnectionError` | FalkorDB unavailable | Check Docker/connection |
| `ValueError` | Invalid API key | Verify 1Password setup |
| `TokenLimitError` | Results too large | Reduce search scope |
| `ValidationError` | Invalid metadata | Check Pydantic models |

### Error Recovery

```python
try:
    memory = await get_shared_memory()
except ConnectionError:
    # Fallback to local cache
    memory = LocalMemoryCache()
```

## Performance

### Batching

Memories are batched for efficiency:

```python
# Automatic batching
for i in range(100):
    await memory.add_memory(data)  # Batched internally

# Manual flush
await memory.force_flush()
```

### Token Management

```python
# Check token usage
tokens = memory.count_tokens(text)
if tokens > memory.max_tokens:
    # Results will be automatically batched
    pass
```

### Smart Indexing

```python
# Build indexes for common patterns
await memory.build_smart_index()

# Use smart search
results = await memory.search_with_smart_index(query)
```

## Examples

### Complete Workflow

```python
# Initialize
memory = await get_shared_memory()
capture = await get_pattern_capture()

# Capture solution
memory_id = await capture.capture_deployment_solution(
    error="Port 6379 already in use",
    solution="Use port 6380 for FalkorDB",
    context={"service": "falkordb"}
)

# Search later
results = await memory.search_with_temporal_weight(
    "port conflict falkordb"
)

# Check evolution
evolution = await memory.get_memory_evolution("falkordb port")

# Supersede if better solution found
if better_solution:
    new_id = await memory.supersede_memory(
        old_id=memory_id,
        new_content={"solution": "Use Docker networks"},
        reason="More flexible port management"
    )
```

## See Also

- [Memory Philosophy](../explanation/memory-philosophy.md)
- [Configuration Guide](configuration.md)
- [Troubleshooting](../how-to/troubleshoot-common-issues.md)
