# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# NO build-essential needed! All packages have ARM64 wheels

# Copy only requirements first for better caching
COPY pyproject.toml ./

# Use BuildKit cache mount for pip packages
# This caches downloaded wheels between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install \
        "graphiti-core[falkordb]>=0.18.9,<0.19.0" \
        onepassword-sdk==0.1.3 \
        openai>=1.7.0 \
        python-dotenv>=1.0.0 \
        pydantic>=2.5.0 \
        pydantic-settings>=2.0.0 \
        mcp>=1.0.0 \
        falkordb>=1.0.10 \
        redis>=5.0.0 \
        tiktoken>=0.5.0 \
        langfuse>=2.0.0

# Copy only necessary source files
COPY *.py ./
COPY config/ ./config/
COPY langfuse_integration/ ./langfuse_integration/

# Install package with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e . --no-deps

# Apply FalkorDB compatibility patches to graphiti-core
# Create a patch script and run it
RUN cat > /tmp/patch_graphiti.py << 'EOF'
import os
import re
import sys

try:
    # Find graphiti_core installation
    import graphiti_core
    graphiti_path = os.path.dirname(graphiti_core.__file__)

    # Patch 1: Quote syntax in search_utils.py
    search_utils = os.path.join(graphiti_path, 'search', 'search_utils.py')
    with open(search_utils, 'r') as f:
        lines = f.readlines()

    # Find and fix the group_id line
    for i, line in enumerate(lines):
        if 'group_id:"{' in line and 'for g in group_ids' in line:
            # Replace double quotes with single quotes for group_id
            lines[i] = line.replace('f\'group_id:"{g}"\'', 'f"group_id:\'{g}\'"')
            lines[i] = lines[i].replace('f"group_id:\\"{g}\\""', 'f"group_id:\'{g}\'"')
            print(f"Fixed line {i+1}: {lines[i].strip()}")
            break

    with open(search_utils, 'w') as f:
        f.writelines(lines)
    print("✓ Applied quote syntax patch")

    # Patch 2: Neo4j procedures in graph_queries.py
    graph_queries = os.path.join(graphiti_path, 'graph_queries.py')
    with open(graph_queries, 'r') as f:
        lines = f.readlines()

    patched = False
    for i, line in enumerate(lines):
        if 'def get_relationships_query' in line:
            for j in range(i, min(i+10, len(lines))):
                if 'if provider == GraphProvider.FALKORDB:' in lines[j]:
                    lines[j+1] = '        # FalkorDB v4.2 does not support db.idx.fulltext.queryRelationships\n'
                    lines[j+2] = '        # Return empty string - the calling code should handle this differently\n'
                    lines[j+3] = '        return ""\n'
                    patched = True
                    break
            break

    if patched:
        with open(graph_queries, 'w') as f:
            f.writelines(lines)
        print("✓ Applied Neo4j procedures patch")

    # Patch 3: Edge fulltext search in search_utils.py
    with open(search_utils, 'r') as f:
        content = f.read()

    # Check if patch is already applied
    if 'Check if FalkorDB' not in content:
        # Find the edge_fulltext_search function and add the check
        pattern = r'(async def edge_fulltext_search\([^)]+\) -> list\[EntityEdge\]:)\s*\n(\s+)(.*?)(\s+fuzzy_query = fulltext_query)'

        def replacement(match):
            func_def = match.group(1)
            indent = match.group(2)
            existing = match.group(3)
            fuzzy_line = match.group(4)

            new_code = f'''{func_def}
{indent}# Check if FalkorDB - it doesn't support edge fulltext search
{indent}relationships_query = get_relationships_query('edge_name_and_fact', provider=driver.provider)
{indent}if relationships_query == '':
{indent}    # FalkorDB doesn't support edge fulltext search
{indent}    return []
{indent}
{indent}# fulltext search over facts
{fuzzy_line}'''
            return new_code

        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        # Update query construction
        content = re.sub(
            r'query = \(\s*get_relationships_query\([^)]+\)',
            'query = (\n        relationships_query',
            content
        )

        with open(search_utils, 'w') as f:
            f.write(content)
        print("✓ Applied edge fulltext search patch")

    print('✅ All FalkorDB compatibility patches applied successfully!')

except Exception as e:
    print(f'❌ Error applying patches: {e}')
    sys.exit(1)
EOF

RUN python /tmp/patch_graphiti.py && rm /tmp/patch_graphiti.py

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q .

# Pre-download tiktoken encodings to avoid SSL issues at runtime
# Set environment variables to disable SSL verification for tiktoken download
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache
ENV REQUESTS_CA_BUNDLE=""
RUN mkdir -p /app/.tiktoken_cache && \
    python -c "import os; os.environ['REQUESTS_CA_BUNDLE']=''; import tiktoken; tiktoken.encoding_for_model('gpt-4o-mini'); tiktoken.encoding_for_model('text-embedding-3-small')" || true
# Reset CA bundle for runtime (OrbStack cert will be used)
ENV REQUESTS_CA_BUNDLE=/usr/local/share/ca-certificates/orbstack-root.crt

# Verify critical imports still work
RUN python -c "import memory_models, capture, graphiti_memory, commands, secrets_manager"

ENV PYTHONUNBUFFERED=1

CMD ["python", "mcp_server.py"]
