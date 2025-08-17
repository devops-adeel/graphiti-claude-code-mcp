# Claude Code Memory Layer - Development Guide

## Project Context
This is a Graphiti-based memory layer for Claude Code that shares a knowledge graph with GTD Coach. It captures coding patterns, solutions, and troubleshooting plays while maintaining temporal history.

## Key Architectural Decisions

### Shared Knowledge Graph
- Uses same FalkorDB instance as GTD Coach (port 6380)
- Shares group_id: `shared_gtd_knowledge`
- Never deletes memories - only marks as superseded
- Maintains temporal history with exponential decay weighting

### Memory Status Lifecycle
- **ACTIVE**: Current, valid memories
- **SUPERSEDED**: Replaced by newer solutions (preserved for history)
- **HISTORICAL**: Old but potentially useful memories
- **DEPRECATED**: No longer applicable (filtered from searches)

## Development Preferences

### Code Style
- Python 3.11+ with type hints
- Async/await patterns throughout
- Singleton pattern for shared instances
- Minimal, clean root-level structure
- Separate tests/ directory

### Testing Methodology
- TDD with red-green-refactor cycle
- pytest with asyncio support
- Comprehensive mocking for external services
- Test coverage target: >80%

### Docker/OrbStack
- Use OrbStack for container management
- FalkorDB runs on custom port 6380
- Multi-stage builds for efficiency
- Health checks for all services

## Common Commands

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_memory.py -v

# Run in watch mode
pytest-watch tests/
```

### Docker Operations
```bash
# Start services (FalkorDB must be running first)
docker compose up -d

# View logs
docker compose logs -f graphiti-mcp

# Rebuild after changes
docker compose build --no-cache

# Check health
docker compose ps

# Stop services
docker compose down
```

### Memory Operations
```bash
# Test memory connection
python -c "import asyncio; from graphiti_memory import get_shared_memory; asyncio.run(get_shared_memory())"

# Generate Claude commands
python -c "import asyncio; from commands import get_command_generator; gen = asyncio.run(get_command_generator()); asyncio.run(gen.generate_all_commands())"

# Run MCP server locally
python mcp_server.py
```

## Key Files and Their Purposes

### Core Components
- `graphiti_memory.py` - Shared memory client with temporal weighting
- `capture.py` - Pattern capture logic for TDD, Docker fixes, etc.
- `commands.py` - Claude command generator with GTD awareness
- `mcp_server.py` - MCP server implementation

### Configuration
- `.env.graphiti` - Shared configuration (uses GTD Coach's)
- `docker-compose.yml` - Container orchestration
- `pyproject.toml` - Python project configuration

### Tests
- `tests/test_memory.py` - Comprehensive memory system tests

## Memory Search Patterns

### Basic Search
```python
# Search with temporal weighting
results = await memory.search_with_temporal_weight("docker error")

# Filter by source
results = await memory.search_with_temporal_weight(
    "test pattern",
    filter_source="claude_code"
)

# Include historical memories
results = await memory.search_with_temporal_weight(
    "deployment",
    include_historical=True
)
```

### Cross-Domain Insights
```python
# Find connections between GTD and coding
insights = await memory.find_cross_domain_insights("docker deployment")

# Get memory evolution
evolution = await memory.get_memory_evolution("test patterns")
```

## Pattern Capture Examples

### TDD Cycle
```python
await capture.capture_tdd_cycle(
    test_code="def test_feature(): assert False",
    implementation="def feature(): return True",
    feature_name="user_auth"
)
```

### Docker Fix
```python
await capture.capture_docker_fix(
    build_error="Module not found",
    fix="Add module to requirements.txt",
    dockerfile_snippet="RUN pip install -r requirements.txt"
)
```

### Command Pattern
```python
await capture.capture_command_pattern(
    command="docker compose up -d",
    context="deployment",
    success=True
)
```

## Integration with GTD Coach

### Shared Memories
- Both systems write to same knowledge graph
- GTD tasks can reference coding solutions
- Coding patterns can link to GTD tasks

### Cross-References
Automatically detected:
- `@computer` context items
- Deployment tasks
- Testing methodologies
- Project references

## Troubleshooting

### FalkorDB Connection Issues
1. Check FalkorDB is running: `docker ps | grep falkor`
2. Verify port 6380: `redis-cli -p 6380 ping`
3. Check environment variables in `.env.graphiti`

### Memory Not Persisting
1. Verify group_id matches: `shared_gtd_knowledge`
2. Check database name: `shared_knowledge_graph`
3. Ensure OPENAI_API_KEY is set

### MCP Server Not Starting
1. Check Python dependencies: `pip install -e .`
2. Verify async initialization completes
3. Check logs: `docker compose logs graphiti-mcp`

## Performance Considerations

### Temporal Decay
- Default decay factor: 0.95 per day
- Recent memories weighted higher
- Adjustable via MEMORY_DECAY_FACTOR

### Search Optimization
- Limit results to top 10 by default
- Pre-filter deprecated memories
- Cache singleton instances

## Future Enhancements
- [ ] Web UI for memory browsing
- [ ] Automated pattern extraction from code reviews
- [ ] Integration with IDE extensions
- [ ] Memory export/import capabilities
- [ ] Advanced cross-domain analytics

## Remember
- Never delete memories, only supersede them
- Always maintain temporal history
- Link to GTD tasks when relevant
- Capture patterns as you discover them
- Use TDD methodology for new features