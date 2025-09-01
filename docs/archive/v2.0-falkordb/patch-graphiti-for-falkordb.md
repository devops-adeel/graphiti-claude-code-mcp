# Patching Graphiti-Core for FalkorDB Compatibility

This guide explains how to apply necessary patches to graphiti-core v0.18.9+ for FalkorDB compatibility.

## Background

FalkorDB v4.2 uses RediSearch for fulltext indexing instead of Neo4j's procedures. This requires specific patches to graphiti-core after installation.

## Required Patches

After installing graphiti-claude-code-mcp, you need to apply three patches to graphiti-core:

### 1. Quote Syntax Patch

FalkorDB's RediSearch requires single quotes instead of double quotes in fulltext queries.

**File**: `venv/lib/python*/site-packages/graphiti_core/search/search_utils.py`

Find line ~67:
```python
[fulltext_syntax + f'group_id:"{g}"' for g in group_ids] if group_ids is not None else []
```

Replace with:
```python
[fulltext_syntax + f"group_id:'{g}'" for g in group_ids] if group_ids is not None else []
```

### 2. Neo4j Procedures Patch

FalkorDB v4.2 doesn't support `db.idx.fulltext.queryRelationships`.

**File**: `venv/lib/python*/site-packages/graphiti_core/graph_queries.py`

Find the `get_relationships_query` function (~line 99):
```python
def get_relationships_query(name: str, provider: GraphProvider) -> str:
    if provider == GraphProvider.FALKORDB:
        label = NEO4J_TO_FALKORDB_MAPPING[name]
        return f"CALL db.idx.fulltext.queryRelationships('{label}', $query)"

    return f'CALL db.index.fulltext.queryRelationships("{name}", $query, {{limit: $limit}})'
```

Replace with:
```python
def get_relationships_query(name: str, provider: GraphProvider) -> str:
    if provider == GraphProvider.FALKORDB:
        # FalkorDB v4.2 doesn't support db.idx.fulltext.queryRelationships
        # Return empty string - the calling code should handle this differently
        return ""

    return f'CALL db.index.fulltext.queryRelationships("{name}", $query, {{limit: $limit}})'
```

### 3. Edge Fulltext Search Patch

Disable edge fulltext search for FalkorDB.

**File**: `venv/lib/python*/site-packages/graphiti_core/search/search_utils.py`

Find the `edge_fulltext_search` function (~line 142):
```python
async def edge_fulltext_search(
    driver: GraphDriver,
    query: str,
    search_filter: SearchFilters,
    group_ids: list[str] | None = None,
    limit=RELEVANT_SCHEMA_LIMIT,
) -> list[EntityEdge]:
    # fulltext search over facts
    fuzzy_query = fulltext_query(query, group_ids, driver.fulltext_syntax)
    if fuzzy_query == '':
        return []

    filter_query, filter_params = edge_search_filter_query_constructor(search_filter)

    query = (
        get_relationships_query('edge_name_and_fact', provider=driver.provider)
        + """
        YIELD relationship AS rel, score
```

Replace the beginning with:
```python
async def edge_fulltext_search(
    driver: GraphDriver,
    query: str,
    search_filter: SearchFilters,
    group_ids: list[str] | None = None,
    limit=RELEVANT_SCHEMA_LIMIT,
) -> list[EntityEdge]:
    # Check if FalkorDB - it doesn't support edge fulltext search
    relationships_query = get_relationships_query('edge_name_and_fact', provider=driver.provider)
    if relationships_query == '':
        # FalkorDB doesn't support edge fulltext search
        return []

    # fulltext search over facts
    fuzzy_query = fulltext_query(query, group_ids, driver.fulltext_syntax)
    if fuzzy_query == '':
        return []

    filter_query, filter_params = edge_search_filter_query_constructor(search_filter)

    query = (
        relationships_query
        + """
        YIELD relationship AS rel, score
```

## Automated Patching

You can use the provided patch script from the FalkorDB tests:

```bash
# Apply patches
python /path/to/falkordb/tests/patch_graphiti_falkordb.py

# Verify patches
python /path/to/falkordb/tests/patch_graphiti_falkordb.py --check

# Revert patches if needed
python /path/to/falkordb/tests/patch_graphiti_falkordb.py --revert
```

Or use our convenience script:

```bash
# From the project root
./scripts/patch-graphiti.sh
```

## Verification

After applying patches, verify they work:

```bash
python -c "
import asyncio
from graphiti_memory import get_shared_memory

async def test():
    memory = await get_shared_memory()
    results = await memory.search_with_temporal_weight('test')
    print(f'✅ Patches applied successfully! Found {len(results)} results')

asyncio.run(test())
"
```

## Important Notes

1. **Patches are temporary**: These patches will be lost if you reinstall or upgrade graphiti-core
2. **Re-apply after upgrades**: Run the patch script again after any pip install/upgrade
3. **Version specific**: These patches are for graphiti-core v0.18.9+
4. **Upstream issue**: We're working with the graphiti-core team for a permanent fix

## Troubleshooting

If you encounter errors after patching:

1. **Check graphiti-core version**:
   ```bash
   pip show graphiti-core
   ```

2. **Verify FalkorDB is running**:
   ```bash
   redis-cli -p 6379 ping  # Should return PONG
   ```

3. **Check patch status**:
   ```bash
   python /path/to/falkordb/tests/patch_graphiti_falkordb.py --check
   ```

4. **Review error logs**: The error message will indicate which procedure failed

## Alternative Solution

If patching is problematic, consider using Neo4j instead of FalkorDB for full compatibility.

## Future Plans

We're tracking this issue and working on:
- Submitting patches upstream to graphiti-core
- Creating a FalkorDB-compatible fork if needed
- Implementing automatic post-install patching

## References

- [FalkorDB Documentation](https://docs.falkordb.com/)
- [Graphiti-Core Repository](https://github.com/getzep/graphiti)
- [Original Issue Analysis](../explanations/root-cause-analysis.md)
