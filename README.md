# Graphiti Claude Code MCP

A temporal knowledge graph memory layer for Claude Code that captures coding patterns, solutions, and troubleshooting plays. Shares knowledge with GTD Coach for cross-domain insights.

## Features

- 🧠 **Shared Knowledge Graph** - Integrates with GTD Coach using same FalkorDB instance
- ⏳ **Temporal Memory** - Never deletes history, uses exponential decay weighting
- 🔄 **Pattern Evolution** - Tracks how solutions improve over time
- 🎯 **TDD Capture** - Records red-green-refactor cycles
- 🐳 **Docker Solutions** - Remembers deployment fixes and Docker patterns
- 🔗 **Cross-Domain Insights** - Links GTD tasks with coding solutions
- 📝 **Claude Commands** - Generates memory-aware commands for Claude Code

## Architecture

```
┌─────────────────────────────────────────┐
│         Claude Code                      │
│         (You are here)                   │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│     Graphiti Claude Code MCP            │
│  - Pattern Capture                       │
│  - Temporal Weighting                    │
│  - Cross-Domain Search                   │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│        Shared Knowledge Graph            │
│    (FalkorDB - Port 6380)               │
│    group_id: shared_gtd_knowledge       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│          GTD Coach                       │
│    (Also uses same graph)               │
└─────────────────────────────────────────┘
```

## Prerequisites

- Python 3.11+
- Docker with OrbStack (macOS) or Docker Desktop
- FalkorDB running on port 6380 (via your existing setup)
- OpenAI API key

## Docker Installation (Recommended for Claude Code)

### Quick Start

1. **Build the Docker image:**
   ```bash
   ./scripts/build-docker.sh
   ```

2. **Test the setup:**
   ```bash
   ./scripts/test-docker.sh
   ```

3. **Configure Claude Code:**
   Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "graphiti-memory": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "-v", "/Users/adeel/.env:/app/.env:ro",
           "-v", "/Users/adeel/Documents/1_projects/graphiti-claude-code-mcp/.env.graphiti:/app/.env.graphiti:ro",
           "--add-host", "host.docker.internal:host-gateway",
           "graphiti-mcp-server:latest"
         ]
       }
     }
   }
   ```

4. **Restart Claude Code** and verify connection

### Docker Setup Details

The Docker installation provides:
- **Isolated environment** - No Python version conflicts
- **Automatic stdio transport** - Proper MCP protocol handling
- **Host networking** - Connects to FalkorDB on host machine
- **Secure secrets** - Mounts environment files as read-only

### Environment Configuration

The Docker container expects:
- `~/.env` - Contains your OPENAI_API_KEY
- `.env.graphiti` - Contains Graphiti/FalkorDB configuration

The wrapper automatically handles Docker networking by converting `localhost` to `host.docker.internal` when running in Docker.

### Troubleshooting Docker

If Claude Code can't connect:
1. Ensure Docker is running: `docker ps`
2. Check FalkorDB is accessible: `nc -z localhost 6380`
3. Verify image exists: `docker images | grep graphiti-mcp-server`
4. Check logs: Remove `--rm` from args and run `docker logs <container-id>`

For manual testing:
```bash
docker run -i --rm \
  -v ~/.env:/app/.env:ro \
  -v $(pwd)/.env.graphiti:/app/.env.graphiti:ro \
  --add-host host.docker.internal:host-gateway \
  graphiti-mcp-server:latest
```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/graphiti-claude-code-mcp.git
cd graphiti-claude-code-mcp
```

### 2. Set Up Environment

The system uses the shared `.env.graphiti` from GTD Coach. If it doesn't exist, create it:

```bash
# Copy from GTD Coach if available
cp ~/gtd-coach/.env.graphiti .env.graphiti

# Or create new one
cat > .env.graphiti << 'EOF'
# Shared Configuration
GRAPHITI_GROUP_ID=shared_gtd_knowledge
FALKORDB_HOST=localhost
FALKORDB_PORT=6380
FALKORDB_DATABASE=shared_knowledge_graph

# OpenAI Configuration
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Memory Configuration
MEMORY_DECAY_FACTOR=0.95
MEMORY_INCLUDE_HISTORICAL=false
ENABLE_GTD_INTEGRATION=true
ENABLE_CROSS_REFERENCES=true
EOF
```

### 3. Install Dependencies

```bash
# Install in development mode
pip install -e .

# Or use Docker
docker compose build
```

### 4. Verify FalkorDB is Running

```bash
# Check FalkorDB status
redis-cli -p 6380 ping
# Should return: PONG

# Or check via Docker
docker ps | grep falkor
```

### 5. Run Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=term-missing
```

### 6. Start the MCP Server

```bash
# Local development
python mcp_server.py

# Or via Docker
docker compose up -d
```

## Usage Examples

### Capture a TDD Pattern

```python
from capture import get_pattern_capture

capture = await get_pattern_capture()
memory_id = await capture.capture_tdd_cycle(
    test_code="def test_auth(): assert user.is_authenticated == False",
    implementation="def authenticate(user): user.is_authenticated = True",
    feature_name="user_authentication"
)
```

### Search Shared Knowledge

```python
from graphiti_memory import get_shared_memory

memory = await get_shared_memory()

# Search for Docker solutions
results = await memory.search_with_temporal_weight(
    "docker build error",
    include_historical=False
)

# Find cross-domain insights
insights = await memory.find_cross_domain_insights("deployment")
```

### Generate Claude Commands

```bash
# Generate all commands
python -c "import asyncio; from commands import get_command_generator; gen = asyncio.run(get_command_generator()); asyncio.run(gen.generate_all_commands())"

# Commands are saved to ~/.claude/commands/
ls ~/.claude/commands/
```

## Available Claude Commands

After generation, these commands become available:

- `/tdd-feature <name>` - Scaffold test-first Python feature
- `/check-deployment` - Verify Docker/OrbStack deployment
- `/fix-docker <error>` - Fix Docker issues with learned solutions
- `/project-structure <name>` - Create project with preferred structure
- `/search-memory <query>` - Search shared knowledge graph

## MCP Tools

The MCP server provides these tools:

- `capture_solution` - Capture coding solutions
- `capture_tdd_pattern` - Record TDD cycles
- `search_memory` - Search knowledge graph
- `find_cross_insights` - Discover cross-domain connections
- `get_gtd_context` - Get current GTD context
- `supersede_memory` - Update existing memories
- `capture_command` - Record command patterns
- `get_memory_evolution` - Trace solution evolution

## Memory Status Lifecycle

```
ACTIVE ──superseded──> SUPERSEDED ──aged──> HISTORICAL ──invalid──> DEPRECATED
   │                        │                    │                      │
   └────────────────────────┴────────────────────┴──────────────────────┘
                        All states preserved in history
```

## Integration with GTD Coach

This memory layer shares the same knowledge graph with GTD Coach:

- **Shared group_id**: `shared_gtd_knowledge`
- **Same FalkorDB**: Port 6380
- **Cross-references**: Automatic linking between domains
- **Unified search**: Query across both GTD and coding memories

## Development

### Project Structure

```
graphiti-claude-code-mcp/
├── graphiti_memory.py      # Core memory client
├── capture.py              # Pattern capture logic
├── commands.py             # Claude command generator
├── mcp_server.py          # MCP server implementation
├── tests/
│   └── test_memory.py     # Comprehensive tests
├── docker-compose.yml     # Container orchestration
├── Dockerfile            # Container definition
├── pyproject.toml       # Python project config
├── .env.graphiti       # Shared configuration
├── CLAUDE.md          # AI assistant guide
└── README.md         # This file
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test class
pytest tests/test_memory.py::TestSharedMemory -v

# With debugging
pytest tests/ -v -s

# Watch mode
pytest-watch tests/
```

### Docker Development

```bash
# Build and start
docker compose up --build

# View logs
docker compose logs -f

# Exec into container
docker compose exec graphiti-mcp bash

# Rebuild clean
docker compose down
docker compose build --no-cache
docker compose up
```

## Troubleshooting

### Quick Diagnosis

Run the health check script for immediate diagnosis:

```bash
# Basic health check
make health-check

# Detailed with FalkorDB queries shown
make health-check-verbose

# With fix suggestions
make health-check-fix
```

### FalkorDB Connection Failed

```bash
# Check if FalkorDB is running
docker ps | grep falkor

# Test connection (port may be 6379 or 6380)
redis-cli -p 6379 ping

# Check logs
docker logs falkordb
```

### Memory Not Persisting

1. Run health check: `make health-check-verbose`
2. Verify group_id matches: `shared_knowledge`
3. Check database name in `.env.graphiti`
4. Ensure OpenAI API key is valid

### MCP Server Issues

```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -e . --force-reinstall

# Run health check
python scripts/health_check_memory.py --fix
```

For detailed troubleshooting, see `docs/TROUBLESHOOTING.md`

## Security 🔒

### Security Best Practices

This project implements multiple layers of security to protect sensitive information:

#### 🛡️ Secret Management
- **1Password Integration**: All secrets stored securely in 1Password vault
- **Environment Variables**: Credentials injected at runtime, never hardcoded
- **Placeholder Values**: Setup scripts use placeholders, not real credentials

#### 🔍 Secret Detection
- **Pre-commit Hooks**: TruffleHog and Gitleaks scan before every commit
- **GitHub Actions**: Continuous scanning in CI/CD pipeline
- **Custom Rules**: Project-specific patterns in `.gitleaks.toml`

#### 📋 Quick Security Setup

```bash
# 1. Install pre-commit hooks (REQUIRED)
pip install pre-commit
pre-commit install

# 2. Test secret scanning
pre-commit run --all-files

# 3. Set up 1Password (for production use)
make setup-1password
```

#### ⚠️ Security Reminders
- **NEVER** hardcode credentials, even for testing
- **ALWAYS** use mock credentials in test files
- **ROTATE** credentials every 90 days
- **REVIEW** [SECURITY.md](SECURITY.md) for incident response

#### 🚨 If You Find a Security Issue
1. **Do NOT** create a public issue
2. Rotate affected credentials immediately
3. Follow the [Security Incident Response](SECURITY.md#security-incident-response) guide
4. Use GitHub's Security Advisory feature for reporting

For complete security documentation, see [SECURITY.md](SECURITY.md)

## Contributing

1. Use TDD methodology - write tests first
2. Maintain temporal history - never delete memories
3. Follow existing patterns in codebase
4. Add cross-domain references where relevant
5. Update CLAUDE.md for AI-specific guidance

## License

MIT

## Acknowledgments

- Built on [Graphiti](https://github.com/getzep/graphiti) by Zep
- Integrates with [GTD Coach](https://github.com/yourusername/gtd-coach)
- Uses [FalkorDB](https://www.falkordb.com/) for graph storage
- Implements [MCP](https://github.com/anthropics/mcp) protocol
