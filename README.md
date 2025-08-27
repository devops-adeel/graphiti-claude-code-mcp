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
- FalkorDB running on port 6380 ([setup guide](https://docs.falkordb.com/quick-start))
- 1Password Service Account with read access to HomeLab vault
- OpenAI API key (stored in 1Password)

## Installation via Claude CLI (Recommended)

### Quick Setup

1. **Clone and build the Docker image:**
   ```bash
   git clone https://github.com/yourusername/graphiti-claude-code-mcp.git
   cd graphiti-claude-code-mcp
   ./scripts/build-docker.sh
   ```

2. **Set up 1Password service token:**
   ```bash
   # Create config directory
   mkdir -p ~/.config/graphiti-mcp

   # Save your service token (get from 1Password)
   echo 'export OP_SERVICE_ACCOUNT_TOKEN="your-token-here"' > ~/.config/graphiti-mcp/service-token
   chmod 600 ~/.config/graphiti-mcp/service-token
   ```

3. **Create configuration file:**
   ```bash
   # Copy the template
   cp .env.graphiti.example ~/.config/graphiti-mcp/.env.graphiti

   # Edit to set your FalkorDB connection details
   nano ~/.config/graphiti-mcp/.env.graphiti
   ```

4. **Add to Claude Code using CLI:**
   ```bash
   # Make wrapper executable
   chmod +x scripts/claude-mcp-wrapper.sh

   # Add the MCP server (from the project directory)
   claude mcp add graphiti-mcp -- $PWD/scripts/claude-mcp-wrapper.sh
   ```

5. **Verify connection:**
   ```
   # In Claude Code, ask:
   "Search your memory for 'test connection'"

   # Or check MCP server status:
   "What MCP servers are connected?"
   ```

### What This Does

The `claude mcp add` command:
- Registers the `graphiti-mcp` server with Claude Code
- Uses the wrapper script to handle Docker execution
- Loads your 1Password service token securely
- Mounts your configuration from `~/.config/graphiti-mcp/`
- Connects to your FalkorDB instance

## Alternative: Manual Configuration

If you prefer to manually edit the configuration file, you can add the server directly to Claude Code's configuration:

1. **Build the Docker image:**
   ```bash
   ./scripts/build-docker.sh
   ```

2. **Edit Claude Code configuration:**
   Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "graphiti-mcp": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "-e", "OP_SERVICE_ACCOUNT_TOKEN=${OP_SERVICE_ACCOUNT_TOKEN}",
           "-v", "${HOME}/.config/graphiti-mcp/.env.graphiti:/app/.env.graphiti:ro",
           "--add-host", "host.docker.internal:host-gateway",
           "graphiti-mcp-server:latest"
         ]
       }
     }
   }
   ```

3. **Source your service token before starting Claude Code:**
   ```bash
   source ~/.config/graphiti-mcp/service-token
   claude
   ```

## Docker Setup Details

The Docker installation provides:
- **Isolated environment** - No Python version conflicts
- **Automatic stdio transport** - Proper MCP protocol handling
- **Host networking** - Connects to FalkorDB on host machine
- **Secure secrets** - Uses 1Password SDK for API keys

### Troubleshooting Docker

If Claude Code can't connect:
1. Ensure Docker is running: `docker ps`
2. Check FalkorDB is accessible: `nc -z localhost 6380`
3. Verify image exists: `docker images | grep graphiti-mcp-server`
4. Check service token: `source ~/.config/graphiti-mcp/service-token && echo $OP_SERVICE_ACCOUNT_TOKEN`
5. View logs: `docker logs $(docker ps -lq)` after attempting connection

For manual testing:
```bash
# Load service token
source ~/.config/graphiti-mcp/service-token

# Run container manually
docker run -i --rm \
  -e OP_SERVICE_ACCOUNT_TOKEN="$OP_SERVICE_ACCOUNT_TOKEN" \
  -v ~/.config/graphiti-mcp/.env.graphiti:/app/.env.graphiti:ro \
  --add-host host.docker.internal:host-gateway \
  graphiti-mcp-server:latest
```

## 🔐 1Password SDK Integration

This project uses the 1Password Python SDK for secure runtime secret retrieval. All secrets are stored in 1Password and loaded at runtime - no hardcoded credentials!

### Benefits
- **No hardcoded secrets** - All credentials stored securely in 1Password
- **Runtime retrieval** - Secrets fetched only when needed
- **Automatic rotation** - Update in 1Password, no code changes required
- **Caching** - 5-minute cache reduces API calls by 95%
- **Health monitoring** - Token expiration tracking and alerts

### Setup

1. **Service Account Token**
   Your token is stored at `~/.config/graphiti-mcp/service-token`
   ```bash
   # Load token into environment
   source ~/.config/graphiti-mcp/service-token
   ```

2. **Health Check**
   ```bash
   # Run comprehensive health check
   python scripts/check-sdk-health.py
   ```

3. **Development Setup**
   ```bash
   # Automated setup script
   ./scripts/setup-dev.sh
   ```

### Secret References
All secrets are defined in `config/secrets_manifest.py`:
- `OPENAI_API_KEY` - From FalkorDB/Integration item
- `LANGFUSE_PUBLIC_KEY` - From Langfuse/Integration item
- `LANGFUSE_SECRET_KEY` - From Langfuse/Integration item
- `LANGFUSE_HOST` - From Langfuse/Integration item

## Quick Start

For a quick installation using Claude Code's CLI, see the [Installation via Claude CLI](#installation-via-claude-cli-recommended) section above.

### Manual Setup

If you prefer manual setup or need to customize the installation:

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/graphiti-claude-code-mcp.git
cd graphiti-claude-code-mcp
```

#### 2. Set Up 1Password SDK

The system uses 1Password SDK for all secrets. Configuration values are stored in `~/.config/graphiti-mcp/.env.graphiti`:

```bash
# Create config directory
mkdir -p ~/.config/graphiti-mcp

# Save your service token (get from 1Password)
echo 'export OP_SERVICE_ACCOUNT_TOKEN="your-token-here"' > ~/.config/graphiti-mcp/service-token
chmod 600 ~/.config/graphiti-mcp/service-token

# Load service account token
source ~/.config/graphiti-mcp/service-token

# Verify SDK health
python scripts/check-sdk-health.py

# Copy and customize configuration
cp .env.graphiti.example ~/.config/graphiti-mcp/.env.graphiti
nano ~/.config/graphiti-mcp/.env.graphiti
```

Note: Secrets like `OPENAI_API_KEY` and Langfuse credentials are fetched from 1Password automatically!

#### 3. Install Dependencies

```bash
# For local development
pip install -e .

# Or build Docker image (recommended)
./scripts/build-docker.sh
```

#### 4. Verify FalkorDB is Running

```bash
# Check FalkorDB status
redis-cli -p 6380 ping
# Should return: PONG

# Or check via Docker
docker ps | grep falkor
```

If FalkorDB is not running, see the [FalkorDB Quick Start Guide](https://docs.falkordb.com/quick-start).

#### 5. Run Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=term-missing
```

#### 6. Start the MCP Server

For Claude Code integration, use the [Installation via Claude CLI](#installation-via-claude-cli-recommended) section.

For local development:
```bash
# Load service token
source ~/.config/graphiti-mcp/service-token

# Start server
python mcp_server.py
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
