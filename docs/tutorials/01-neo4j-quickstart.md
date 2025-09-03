# Neo4j Memory Graph in 5 Minutes

Get your memory graph running with Neo4j - a powerful graph database that stores your coding patterns, solutions, and insights as interconnected nodes.

## Prerequisites

✅ Docker Desktop or OrbStack installed
✅ 1Password account (free trial works)
✅ 8GB RAM available
✅ Port 7474 and 7687 free

## Step 1: Start Neo4j (1 minute)

```bash
# Clone if you haven't already
git clone https://github.com/devops-adeel/graphiti-claude-code-mcp.git
cd graphiti-claude-code-mcp

# Start Neo4j with optimized settings
docker compose up -d neo4j

# Wait for Neo4j to be ready (takes ~30 seconds)
docker logs neo4j --follow
# Look for: "Started."
```

## Step 2: Set Up Authentication (2 minutes)

### Create 1Password Item

```bash
# Run the setup script
./scripts/setup-neo4j-1password.sh
```

This script:
1. Generates a secure password
2. Creates "Neo4j GraphitiCore" item in 1Password
3. Tests the connection

**Manual Alternative:**
```bash
# Generate secure password
openssl rand -base64 32

# Create 1Password item manually
op item create \
  --category=password \
  --title="Neo4j GraphitiCore" \
  --vault=Personal \
  password="<your-generated-password>"
```

## Step 3: Open Neo4j Browser (1 minute)

Open your browser and navigate to:
```
http://localhost:7474
```

### First Login
- **Username:** neo4j
- **Password:** (from 1Password item "Neo4j GraphitiCore")

You'll see the Neo4j Browser interface:

```
[Neo4j Browser Interface]
┌─────────────────────────────────┐
│  (:Play intro)  ○ ○ ○           │
├─────────────────────────────────┤
│                                  │
│     Welcome to Neo4j Browser     │
│                                  │
│  Type queries above or click:    │
│  • :play intro - Tutorial        │
│  • :help - Command help          │
│                                  │
└─────────────────────────────────┘
```

## Step 4: Verify Your Memory Graph (1 minute)

Run this query to see if you have any existing memories:

```cypher
// Count all nodes
MATCH (n)
RETURN count(n) as totalNodes
```

Expected for fresh install:
```
totalNodes
----------
0
```

Check that indexes are created:
```cypher
SHOW INDEXES
```

You should see:
- `node_name_and_summary` - For fast memory search
- `edge_name_and_fact` - For relationship queries
- UUID and timestamp indexes

## Understanding Your Memory Graph

### Graph Components

**Nodes (Memories)**
- Blue circles in the visualization
- Each represents a memory, pattern, or solution
- Contains properties like timestamp, content, source

**Relationships (Connections)**
- Lines between nodes
- Show how memories relate (SUPERSEDES, RELATES_TO, etc.)
- Help discover patterns and insights

**Properties (Metadata)**
- Data stored in each node
- Includes: title, content, timestamp, decay_score
- Searchable and filterable

### Your First Memory Query

Once you have memories, try this:

```cypher
// Find recent memories
MATCH (m:Memory)
WHERE m.source = 'claude_code'
RETURN m.title, m.timestamp
ORDER BY m.timestamp DESC
LIMIT 10
```

## Quick Health Check

Run this script to verify everything is working:

```bash
./scripts/check-neo4j-health.sh
```

Expected output:
```
✅ Neo4j running on port 7687
✅ Neo4j Browser accessible on port 7474
✅ Authentication configured
✅ Indexes created: 5
✅ Memory usage: 512MB/2GB
✅ Ready for memories!
```

## Performance Notes

### Initial Setup
- First start: ~45 seconds (downloads image)
- Subsequent starts: ~10 seconds
- Index creation: ~5 seconds

### Resource Usage
- Memory: 2GB heap + 1GB pagecache (default)
- Disk: ~500MB initial, grows with memories
- CPU: Low usage except during queries

### Scaling
- Good for: Up to 100,000 memories
- Beyond that: See [performance optimization](05-optimizing-performance.md)

## Common Issues

### Can't Connect to Neo4j?
```bash
# Check if running
docker ps | grep neo4j

# Check logs for errors
docker logs neo4j --tail 50

# Restart if needed
docker compose restart neo4j
```

### Authentication Failed?
```bash
# Verify 1Password item exists
op item get "Neo4j GraphitiCore"

# Reset password if needed
docker exec -it neo4j cypher-shell -u neo4j -p neo4j \
  "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO '<new-password>'"
```

### Port Already in Use?
```bash
# Find what's using port 7474
lsof -i :7474

# Change ports in docker-compose.yml if needed
# NEO4J_server_http_listen__address: :7475
```

## What's Next?

Your Neo4j memory graph is ready! Now:

1. **[Connect Claude Code](02-claude-code-setup.md)** - Link Claude to your memory graph
2. **[Capture First Memory](03-first-memory-capture.md)** - Start building your knowledge
3. **[Explore Your Graph](04-exploring-memories.md)** - Learn Cypher queries

## Visual Guide to Neo4j Browser

### Main Interface Areas

```
┌──────────────────────────────────────┐
│  Query Editor                         │  <- Write Cypher here
├──────────────────────────────────────┤
│                                      │
│         Graph Visualization          │  <- See your memories
│                                      │
├──────────────────────────────────────┤
│  Results Table                       │  <- Query results
└──────────────────────────────────────┘
```

### Useful Browser Commands
- `:help` - Show all commands
- `:clear` - Clear the view
- `:style` - Customize graph appearance
- `:param` - Set query parameters
- `:history` - See query history

---

**🎉 Congratulations!** You now have a running Neo4j graph database ready to store your coding memories. The graph will grow as you work with Claude Code, building a personalized knowledge base of your solutions and patterns.
