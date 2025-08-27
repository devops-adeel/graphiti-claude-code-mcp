#!/usr/bin/env python3
"""
Claude Command Generator with GTD Awareness
Generates commands for ~/.claude/commands/ that leverage shared memory
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from graphiti_memory import get_shared_memory
from capture import get_pattern_capture, PatternType

logger = logging.getLogger(__name__)


class CommandGenerator:
    """Generates Claude Code commands with GTD integration"""

    def __init__(self):
        self.memory = None
        self.capture = None
        self.commands_dir = Path.home() / ".claude" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize connections"""
        self.memory = await get_shared_memory()
        self.capture = await get_pattern_capture()
        logger.info("CommandGenerator initialized")

    async def generate_tdd_feature_command(self) -> str:
        """Generate /tdd-feature command with memory awareness"""

        # Search for TDD patterns
        patterns = await self.memory.search_with_temporal_weight(
            "TDD pattern pytest", filter_source="claude_code"
        )

        # Search for related GTD tasks
        gtd_tasks = await self.memory.search_with_temporal_weight(
            "task @computer testing", filter_source="gtd_coach"
        )

        # Get pattern evolution
        evolution = await self.capture.get_pattern_evolution(PatternType.TDD_CYCLE)

        command_content = f"""---
allowed-tools: Write, Edit, Bash(pytest:*), Read
description: Scaffold test-first Python feature with learned patterns
argument-hint: feature name
model: gpt-4.1-mini
---

# TDD Feature Implementation with Shared Knowledge

Create a test-first implementation for: $ARGUMENTS

## Memory Context (from {os.getenv('GRAPHITI_GROUP_ID', 'shared_gtd_knowledge')})

### Best TDD Patterns Found:
{self._format_patterns(patterns[:3])}

### Pattern Statistics:
- Total TDD iterations captured: {evolution.get('total_iterations', 0)}
- Active patterns: {evolution.get('active_patterns', 0)}
- Superseded patterns: {evolution.get('superseded_patterns', 0)}

### Related GTD Tasks:
{self._format_gtd_tasks(gtd_tasks[:3])}

## Implementation Steps:

1. **Red Phase** - Write failing test in `tests/test_$ARGUMENTS.py`:
   - Follow captured assertion patterns
   - Use proven fixtures from memory
   - Include edge cases from past learnings

2. **Green Phase** - Implement minimal code to pass:
   - Create implementation in appropriate module
   - Focus on making test pass, not perfection
   - Run: `pytest tests/test_$ARGUMENTS.py -v`

3. **Refactor Phase** - Improve code quality:
   - Apply learned patterns
   - Ensure clean, maintainable code
   - Run full test suite: `pytest tests/ --cov`

4. **Capture Learning** - Store new patterns:
   - If new pattern emerges, capture for future use
   - Link to any GTD tasks if applicable

## Commands to Run:
```bash
# Create test file
touch tests/test_$ARGUMENTS.py

# Run test (should fail initially)
pytest tests/test_$ARGUMENTS.py -v

# After implementation
pytest tests/ --cov

# Check coverage
pytest --cov=$ARGUMENTS --cov-report=term-missing
```

Remember: Red -> Green -> Refactor -> Capture Learning
"""

        # Save command
        command_path = self.commands_dir / "tdd-feature.md"
        command_path.write_text(command_content)
        logger.info(f"Generated /tdd-feature command at {command_path}")

        return command_content

    async def generate_check_deployment_command(self) -> str:
        """Generate /check-deployment command with deployment memory"""

        # Search for deployment issues and solutions
        deployment_issues = await self.memory.search_with_temporal_weight(
            "docker deployment issue OrbStack", include_historical=True
        )

        # Search for GTD deployment tasks
        gtd_deploy = await self.memory.search_with_temporal_weight(
            "@computer deploy task", filter_source="gtd_coach"
        )

        # Get successful deployment commands
        deploy_commands = await self.memory.search_with_temporal_weight(
            "command docker compose success", filter_source="claude_code"
        )

        command_content = f"""---
allowed-tools: Bash(docker:*), Bash(curl:*), Read
description: Check OrbStack deployment with learned solutions
model: gpt-4.1-mini
---

# Deployment Check with Shared Knowledge

## Active GTD Deployment Tasks:
{self._format_gtd_tasks(gtd_deploy[:2])}

## Known Issues & Solutions:
{self._format_deployment_issues(deployment_issues[:3])}

## Deployment Checklist:

### 1. Check Docker/OrbStack Status:
```bash
# Check running containers
docker compose ps

# Check specific service (FalkorDB on port 6379)
docker exec falkordb redis-cli ping

# View recent logs
docker compose logs -f --tail=50
```

### 2. Verify Services:
```bash
# Check FalkorDB
curl -s http://localhost:6379/ping || echo "FalkorDB not responding"

# Check Netdata monitoring
curl -s http://localhost:19999/api/v1/info | jq '.version' || echo "Netdata not available"

# Memory usage
docker stats --no-stream
```

### 3. Common Fixes from Memory:
{self._format_common_fixes(deployment_issues)}

### 4. Successful Command Patterns:
{self._format_commands(deploy_commands[:3])}

## If Issues Found:
1. Check captured solutions in memory
2. Update GTD task with progress
3. Capture new solution if fix is novel

## Update GTD Task:
If deployment succeeds, remember to update related GTD tasks.
"""

        # Save command
        command_path = self.commands_dir / "check-deployment.md"
        command_path.write_text(command_content)
        logger.info(f"Generated /check-deployment command at {command_path}")

        return command_content

    async def generate_fix_docker_command(self) -> str:
        """Generate /fix-docker command with Docker-specific solutions"""

        # Search for Docker fixes
        docker_fixes = await self.memory.search_with_temporal_weight(
            "Docker fix error build", include_historical=False
        )

        # Get evolution of Docker solutions
        evolution = await self.capture.get_pattern_evolution(PatternType.DOCKER_FIX)

        command_content = f"""---
allowed-tools: Bash(docker:*), Edit, Read, Write
description: Fix Docker build/deployment issues with learned solutions
argument-hint: error description
model: gpt-4.1-mini
---

# Fix Docker Issue: $ARGUMENTS

## Searching Memory for Similar Issues...

### Previously Successful Fixes:
{self._format_docker_fixes(docker_fixes[:5])}

### Solution Evolution:
- Total Docker fixes captured: {evolution.get('total_iterations', 0)}
- Currently active solutions: {evolution.get('active_patterns', 0)}
- Superseded (improved) solutions: {evolution.get('superseded_patterns', 0)}

## Diagnostic Steps:

1. **Identify Issue Type**:
```bash
# Check build errors
docker compose build --no-cache 2>&1 | tail -20

# Check runtime errors
docker compose logs --tail=50 | grep -i error

# Check resource constraints
docker system df
docker system prune -a --volumes  # If space issue
```

2. **Common Fixes by Category**:

### Dependency Issues:
- Clear pip cache: `docker compose build --no-cache`
- Update base image in Dockerfile
- Pin dependency versions in requirements.txt

### Multi-stage Build Issues:
- Ensure COPY commands reference correct stage
- Check build context paths
- Verify stage naming consistency

### Layer Caching Issues:
- Reorder Dockerfile commands (less frequently changing first)
- Use specific tags instead of :latest
- Add .dockerignore for unnecessary files

### Environment Variables:
- Check .env file exists and is loaded
- Verify variable names match in docker-compose.yml
- Ensure no spaces around = in .env file

3. **OrbStack Specific**:
```bash
# Restart OrbStack if needed
orb restart

# Check OrbStack resources
orb config get memory
orb config get cpu
```

4. **Capture Solution**:
If you find a new fix, it will be automatically captured for future use.

## Port Configuration Reminder:
- FalkorDB runs on port 6379 (standard Redis port)
- Netdata monitoring on port 19999
- Always check port conflicts with: `lsof -i :6379`
"""

        # Save command
        command_path = self.commands_dir / "fix-docker.md"
        command_path.write_text(command_content)
        logger.info(f"Generated /fix-docker command at {command_path}")

        return command_content

    async def generate_project_structure_command(self) -> str:
        """Generate /project-structure command with preferences"""

        # Search for structure patterns
        structures = await self.memory.search_with_temporal_weight(
            "project structure minimal clean", filter_source="claude_code"
        )

        command_content = f"""---
allowed-tools: Write, Bash(mkdir:*), Bash(touch:*)
description: Create project with preferred minimal structure
argument-hint: project name
model: gpt-4.1-mini
---

# Create Project: $ARGUMENTS

## Your Preferred Structure Pattern:

### Principles (from memory):
- Minimal, clean root-level
- Separate tests/ directory
- Start with monorepo pattern
- No unnecessary nesting

### Standard Structure:
```
$ARGUMENTS/
├── $ARGUMENTS.py          # Main module (or src/ if complex)
├── tests/
│   └── test_$ARGUMENTS.py # TDD tests
├── docker-compose.yml      # If using Docker/OrbStack
├── pyproject.toml         # Modern Python packaging
├── .env.example           # Environment template
├── CLAUDE.md              # AI assistant guidance
└── README.md              # Project documentation
```

## Create Structure:
```bash
# Create directories
mkdir -p $ARGUMENTS/tests

# Create files
cd $ARGUMENTS
touch $ARGUMENTS.py
touch tests/test_$ARGUMENTS.py
touch pyproject.toml
touch README.md
touch CLAUDE.md
touch .env.example

# Initialize git
git init
echo "__pycache__/" > .gitignore
echo ".env" >> .gitignore
echo "*.pyc" >> .gitignore
```

## pyproject.toml Template:
```toml
[project]
name = "$ARGUMENTS"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Link to GTD:
Create a GTD project task if this is a significant project.
"""

        # Save command
        command_path = self.commands_dir / "project-structure.md"
        command_path.write_text(command_content)
        logger.info(f"Generated /project-structure command at {command_path}")

        return command_content

    async def generate_search_memory_command(self) -> str:
        """Generate /search-memory command to query shared knowledge"""

        command_content = f"""---
allowed-tools: Read
description: Search shared knowledge graph (GTD + Code)
argument-hint: search query
model: gpt-4.1-mini
---

# Search Shared Knowledge: $ARGUMENTS

Searching in group: {os.getenv('GRAPHITI_GROUP_ID', 'shared_gtd_knowledge')}

## Search Categories:

### 1. Coding Patterns:
- TDD patterns and test examples
- Docker/deployment solutions
- Project structures
- Command patterns

### 2. GTD Context:
- Active tasks and projects
- Review insights
- @computer context items
- Weekly priorities

### 3. Cross-Domain Insights:
- Solutions linked to GTD tasks
- Patterns that inform productivity
- Recurring issues across domains

## What to Search For:

### Problem Solving:
- "error: <error message>" - Find previous solutions
- "docker build issue" - Deployment fixes
- "test pattern <type>" - Testing examples

### GTD Integration:
- "task @computer" - Technical tasks
- "project <name>" - Project details
- "review insight" - Weekly learnings

### Pattern Discovery:
- "superseded by" - See solution evolution
- "frequency high" - Most used patterns
- "cross_references" - Connected insights

The search will return temporally-weighted results, with recent and active memories prioritized.
"""

        # Save command
        command_path = self.commands_dir / "search-memory.md"
        command_path.write_text(command_content)
        logger.info(f"Generated /search-memory command at {command_path}")

        return command_content

    def _format_patterns(self, patterns: List[Any]) -> str:
        """Format TDD patterns for display"""
        if not patterns:
            return "- No patterns found yet. Patterns will be captured as you work."

        formatted = []
        for i, pattern in enumerate(patterns, 1):
            meta = getattr(pattern, "metadata", {})
            formatted.append(
                f"{i}. {meta.get('title', 'Pattern')} "
                f"(Score: {getattr(pattern, 'final_score', 0):.2f})\n"
                f"   {meta.get('pattern', '')[:100]}..."
            )

        return "\n".join(formatted)

    def _format_gtd_tasks(self, tasks: List[Any]) -> str:
        """Format GTD tasks for display"""
        if not tasks:
            return "- No related GTD tasks found"

        formatted = []
        for task in tasks:
            meta = getattr(task, "metadata", {})
            formatted.append(
                f"- {meta.get('title', 'Task')}: {meta.get('description', '')[:80]}"
            )

        return "\n".join(formatted)

    def _format_deployment_issues(self, issues: List[Any]) -> str:
        """Format deployment issues with solutions"""
        if not issues:
            return "- No previous deployment issues recorded"

        formatted = []
        for issue in issues:
            meta = getattr(issue, "metadata", {})
            formatted.append(
                f"**Issue**: {meta.get('error', 'Unknown')[:60]}...\n"
                f"**Solution**: {meta.get('solution', 'No solution')[:100]}...\n"
                f"**Status**: {getattr(issue, 'status', 'unknown')}\n"
            )

        return "\n".join(formatted)

    def _format_common_fixes(self, issues: List[Any]) -> str:
        """Extract and format common fixes"""
        if not issues:
            return "No common fixes found"

        fixes = []
        for issue in issues:
            meta = getattr(issue, "metadata", {})
            if meta.get("solution"):
                fixes.append(f"- {meta['solution'][:120]}...")

        return "\n".join(fixes[:5]) if fixes else "No fixes available"

    def _format_commands(self, commands: List[Any]) -> str:
        """Format successful commands"""
        if not commands:
            return "No command patterns found"

        formatted = []
        for cmd in commands:
            meta = getattr(cmd, "metadata", {})
            formatted.append(
                f"```bash\n{meta.get('command', 'No command')}\n```\n"
                f"Context: {meta.get('context', 'Unknown context')}"
            )

        return "\n\n".join(formatted)

    def _format_docker_fixes(self, fixes: List[Any]) -> str:
        """Format Docker-specific fixes"""
        if not fixes:
            return "No Docker fixes found in memory"

        formatted = []
        for fix in fixes:
            meta = getattr(fix, "metadata", {})
            formatted.append(
                f"### {meta.get('error', 'Error')[:50]}...\n"
                f"**Fix**: {meta.get('fix', meta.get('solution', 'No fix'))}\n"
                f"**Confidence**: {getattr(fix, 'final_score', 0):.2f}\n"
            )

        return "\n".join(formatted)

    async def generate_all_commands(self):
        """Generate all Claude commands"""
        await self.generate_tdd_feature_command()
        await self.generate_check_deployment_command()
        await self.generate_fix_docker_command()
        await self.generate_project_structure_command()
        await self.generate_search_memory_command()

        logger.info(f"Generated all commands in {self.commands_dir}")

        # Create index file
        index_content = """# Claude Code Commands with Shared Memory

Generated commands that leverage the shared knowledge graph with GTD Coach.

## Available Commands:

- `/tdd-feature <name>` - Create test-first Python feature
- `/check-deployment` - Verify Docker/OrbStack deployment
- `/fix-docker <error>` - Fix Docker issues with learned solutions
- `/project-structure <name>` - Create project with preferred structure
- `/search-memory <query>` - Search shared knowledge graph

## Shared Knowledge Group:
All commands access the shared knowledge graph: `{}`

## Memory Features:
- Temporal weighting (recent solutions prioritized)
- Solution evolution tracking (superseded patterns preserved)
- Cross-domain insights (GTD ↔ Coding connections)
- Never deletes history (only marks as superseded)
""".format(
            os.getenv("GRAPHITI_GROUP_ID", "shared_gtd_knowledge")
        )

        index_path = self.commands_dir / "README.md"
        index_path.write_text(index_content)

        return index_content


# Singleton instance
_generator_instance = None


async def get_command_generator() -> CommandGenerator:
    """Get or create singleton CommandGenerator instance"""
    global _generator_instance

    if _generator_instance is None:
        _generator_instance = CommandGenerator()
        await _generator_instance.initialize()

    return _generator_instance
