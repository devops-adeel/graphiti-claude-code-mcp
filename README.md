# Graphiti Claude Code MCP

A temporal knowledge graph memory layer for Claude Code that captures coding patterns, solutions, and troubleshooting plays. Shares knowledge with GTD Coach for cross-domain insights.

## 🧠 The Core Innovation

<div align="center">
  <!-- Animated GIF Teaser - Immediate Visual Hook -->
  <img src="docs/assets/images/one-mind-teaser.gif" alt="One Mind Concept Animation" width="600">

  <!-- Quick Stats for Decision Makers -->
  <p>
    <strong>✓ Recalls solutions from weeks ago</strong> •
    <strong>✓ Cross-domain insights</strong> •
    <strong>✓ Never loses context</strong>
  </p>

  <!-- Progressive Disclosure -->
  <details>
    <summary><b>🎬 Watch the Full Concept Video (5:38)</b></summary>

  <br>
  <a href="https://github.com/devops-adeel/graphiti-claude-code-mcp/releases/latest/download/The_AI_That_Never_Forgets.mp4">
    <img src="docs/assets/images/one-mind-thumbnail.png" alt="Watch: The AI That Never Forgets - How Persistent Memory Transforms AI" width="720">
  </a>

  <p align="center">
    <a href="docs/video-transcripts/the-ai-that-never-forgets.md">📄 Read Transcript</a> •
    <a href="#quick-demo">⚡ See It In Action</a> •
    <a href="docs/explanation/memory-philosophy.md">📖 Technical Deep Dive</a>
  </p>
  </details>
</div>

## Features

- 🧠 **Shared Knowledge Graph** - Integrates with GTD Coach using same Neo4j instance
- ⏳ **Temporal Memory** - Never deletes history, uses exponential decay weighting
- 🔄 **Pattern Evolution** - Tracks how solutions improve over time
- 🎯 **TDD Capture** - Records red-green-refactor cycles
- 🐳 **Docker Solutions** - Remembers deployment fixes and Docker patterns
- 🔗 **Cross-Domain Insights** - Links GTD tasks with coding solutions
- 📝 **Claude Commands** - Generates memory-aware commands for Claude Code

### 💼 Why This Matters for Your Team

> **For Engineering Leaders:** Watch how persistent AI memory [transforms team productivity (0:00-1:30)](https://github.com/devops-adeel/graphiti-claude-code-mcp/releases/latest/download/The_AI_That_Never_Forgets.mp4#t=0) - No more knowledge silos, no more repeated debugging, no more context loss between sessions.

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
│    (Neo4j - Port 7687)                  │
│    group_id: shared_gtd_knowledge       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│          GTD Coach                       │
│    (Also uses same graph)               │
└─────────────────────────────────────────┘
```

## Quick Start

**New to the project?** Start with our [Neo4j Quickstart](docs/tutorials/01-neo4j-quickstart.md) (5 minutes).

### 🚀 See It Work in 2 Minutes

> **For Developers:** Jump straight to the [technical implementation demo (2:30-4:00)](https://github.com/devops-adeel/graphiti-claude-code-mcp/releases/latest/download/The_AI_That_Never_Forgets.mp4#t=150) to see how temporal knowledge graphs solve the context persistence problem.

### Prerequisites

- Python 3.11+
- Docker with OrbStack (macOS) or Docker Desktop
- Neo4j running on port 7687
- 1Password Service Account
- OpenAI API key (stored in 1Password)

### Installation

```bash
# Clone and setup
git clone https://github.com/devops-adeel/graphiti-claude-code-mcp.git
cd graphiti-claude-code-mcp
make setup  # Runs complete setup

# Add to Claude Code
claude mcp add graphiti-mcp -- $PWD/scripts/claude-mcp-wrapper.sh

# Verify
make health-check
```

For detailed instructions, see [Neo4j Quickstart](docs/tutorials/01-neo4j-quickstart.md).

## Documentation

### 📚 Learn (Tutorials)
Start here if you're new:
- [Neo4j Quickstart](docs/tutorials/01-neo4j-quickstart.md) - Get up and running (5 min)
- [First Memory](docs/tutorials/02-first-memory.md) - Capture and retrieve your first memory (20 min)

### 🔧 Solve (How-to Guides)
Task-specific guides:
- [Search Memories](docs/how-to/search-memories.md) - Effective search techniques
- [Capture Patterns](docs/how-to/capture-patterns.md) - Record different pattern types
- [Troubleshoot Issues](docs/how-to/troubleshoot-common-issues.md) - Fix common problems

### 📖 Reference
Technical details:
- [API Reference](docs/reference/api.md) - Complete API documentation
- [Security Configuration](docs/reference/security.md) - Security setup and best practices
- [Configuration Options](docs/reference/configuration.md) - All configuration settings

### 💡 Understand (Explanations)
Conceptual deep-dives:
- 🎬 **[Video: The AI That Never Forgets](https://github.com/devops-adeel/graphiti-claude-code-mcp/releases/latest/download/The_AI_That_Never_Forgets.mp4)** - Visual journey through persistent memory (5:38)
- [Memory Philosophy](docs/explanation/memory-philosophy.md) - Why memories never delete
- [Temporal Decay](docs/explanation/temporal-decay.md) - How memory scoring works
- [System Design](docs/explanation/system-design.md) - Architectural decisions

> **For Researchers:** Study the [complete conceptual framework (0:00-5:38)](https://github.com/devops-adeel/graphiti-claude-code-mcp/releases/latest/download/The_AI_That_Never_Forgets.mp4) with [full transcript](docs/video-transcripts/the-ai-that-never-forgets.md) for citation and analysis.

## Key Features in Action

```python
# Automatic memory capture
await capture.capture_tdd_cycle(
    test_code="def test_auth(): assert False",
    implementation="def auth(): return True",
    feature_name="authentication"
)

# Temporal search with decay
results = await memory.search_with_temporal_weight(
    "docker error",
    include_historical=False
)

# Cross-domain insights
insights = await memory.find_cross_domain_insights("deployment")
```

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
- **Same Neo4j**: Port 7687
- **Cross-references**: Automatic linking between domains
- **Unified search**: Query across both GTD and coding memories

## Development

### Quick Commands

```bash
# Run tests
make test

# Build Docker image
make build

# Health check
make health-check

# View logs
docker compose logs -f graphiti-mcp
```

## Troubleshooting

```bash
# Quick diagnosis
make health-check-verbose

# Check connections
cypher-shell -a bolt://localhost:7687
docker ps | grep graphiti
```

For detailed help, see [Troubleshooting Guide](docs/how-to/troubleshoot-common-issues.md).

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
- Integrates with [GTD Coach](https://github.com/devops-adeel/gtd-coach)
- Uses [Neo4j](https://neo4j.com/) for graph storage
- Implements [MCP](https://github.com/anthropics/mcp) protocol
