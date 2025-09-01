# MCP: Claude's Connection to Your Tools

## What is Model Context Protocol?

Model Context Protocol (MCP) is a new standard (introduced November 2024) that lets Claude connect directly to your tools and data sources. Think of it as a USB port for AI - a standardized way for Claude to interact with external systems.

## Why MCP Matters for Your Memory System

**Without MCP:**
- You manually copy and paste information to Claude
- Claude can't remember between sessions
- No direct access to your knowledge graph

**With MCP and Graphiti:**
- Claude directly searches your memory graph
- Automatically captures coding solutions
- Maintains context across sessions
- Links memories to GTD tasks

## How Your Memory System Uses MCP

### 1. Tools - Actions Claude Can Take
When you see Claude using tools like:
```
capture_solution: Saving a coding fix to memory
search_memory: Finding similar past problems
find_cross_insights: Discovering GTD connections
```

These are MCP tools that let Claude interact with your Neo4j memory graph.

### 2. Resources - Data Claude Can Read
Claude has access to:
- `memory://shared-knowledge` - Your entire knowledge graph
- `langfuse://traces` - Recent coding session data
- `memory://patterns` - Captured coding patterns

### 3. Security - You're Always in Control
- Every action requires your explicit approval
- You see exactly what Claude wants to do
- You can deny any request
- All data stays local on your machine

## Quick Verification

Ask Claude: **"What MCP tools do you have access to?"**

You should see:
```
Available tools:
- capture_solution: Capture coding solutions and fixes
- capture_tdd_pattern: Record TDD cycles
- search_memory: Search the knowledge graph
- find_cross_insights: Discover cross-domain connections
- get_gtd_context: Retrieve GTD tasks
[... and more]
```

If you don't see these tools, check your MCP server is running:
```bash
docker ps | grep graphiti-mcp
```

## How MCP Connects Everything

```
┌─────────────────────┐
│   Claude Code       │
│   (You type here)   │
└──────────┬──────────┘
           │
           ▼ MCP Protocol
┌─────────────────────┐
│   MCP Server        │
│ (graphiti-mcp)      │
└──────────┬──────────┘
           │
           ▼ Graph Queries
┌─────────────────────┐
│   Neo4j Database    │
│  (Your memories)    │
└─────────────────────┘
```

## Common MCP Interactions

### When you solve a problem:
```
You: "That Docker fix worked!"
Claude: [Uses capture_solution tool]
Result: Solution saved to memory graph
```

### When you need help:
```
You: "How did I fix SSL certificates before?"
Claude: [Uses search_memory tool]
Result: Finds 3 similar past solutions
```

### When planning work:
```
You: "What should I work on?"
Claude: [Uses get_gtd_context tool]
Result: Shows current GTD tasks and priorities
```

## Troubleshooting MCP

### MCP Server Not Connected?
```bash
# Check if running
docker ps | grep graphiti-mcp

# Restart if needed
docker compose restart graphiti-mcp

# Check logs
docker logs graphiti-mcp --tail 50
```

### Tools Not Available?
1. Verify Claude Code configuration includes MCP server
2. Check `~/.claude/claude_code_config.json` has correct settings
3. Restart Claude Code after configuration changes

## Next Steps

Now that you understand MCP, let's:
1. [Set up your Neo4j memory graph](01-neo4j-quickstart.md)
2. [Connect Claude Code to your system](02-claude-code-setup.md)
3. [Capture your first memory](03-first-memory-capture.md)

---

**Remember:** MCP is just the protocol - like HTTP for web browsers. Your actual memories live in Neo4j, and Graphiti manages them. MCP simply lets Claude access this system securely and efficiently.
