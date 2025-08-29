#!/bin/bash

# Patch Graphiti-Core for FalkorDB Compatibility
# This script applies necessary patches to graphiti-core v0.18.9+ for FalkorDB support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find the graphiti-core installation
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    # Try to find venv in project root
    if [ -d "$PROJECT_ROOT/venv" ]; then
        VENV_PATH="$PROJECT_ROOT/venv"
    else
        echo -e "${RED}Error: No virtual environment found${NC}"
        echo "Please activate your virtual environment or ensure venv exists in project root"
        exit 1
    fi
else
    VENV_PATH="$VIRTUAL_ENV"
fi

# Find graphiti_core in site-packages
GRAPHITI_PATH=""
for dir in "$VENV_PATH"/lib/python*/site-packages/graphiti_core; do
    if [ -d "$dir" ]; then
        GRAPHITI_PATH="$dir"
        break
    fi
done

if [ -z "$GRAPHITI_PATH" ]; then
    echo -e "${RED}Error: graphiti-core not found in virtual environment${NC}"
    echo "Please install graphiti-core first: pip install graphiti-core[falkordb]"
    exit 1
fi

echo -e "${GREEN}Found graphiti-core at: $GRAPHITI_PATH${NC}"

# Function to apply a patch
apply_patch() {
    local file="$1"
    local backup="${file}.backup"

    # Create backup if it doesn't exist
    if [ ! -f "$backup" ]; then
        cp "$file" "$backup"
        echo -e "${YELLOW}Created backup: $backup${NC}"
    fi
}

# Function to check if patches are already applied
check_patches() {
    local search_utils="$GRAPHITI_PATH/search/search_utils.py"
    local graph_queries="$GRAPHITI_PATH/graph_queries.py"

    # Check quote syntax patch
    if grep -q "group_id:'{g}'" "$search_utils" 2>/dev/null; then
        echo -e "${GREEN}✓ Quote syntax patch already applied${NC}"
        QUOTE_PATCHED=true
    else
        echo -e "${YELLOW}○ Quote syntax patch needed${NC}"
        QUOTE_PATCHED=false
    fi

    # Check Neo4j procedures patch
    if grep -q "FalkorDB v4.2 doesn't support db.idx.fulltext.queryRelationships" "$graph_queries" 2>/dev/null; then
        echo -e "${GREEN}✓ Neo4j procedures patch already applied${NC}"
        PROCEDURES_PATCHED=true
    else
        echo -e "${YELLOW}○ Neo4j procedures patch needed${NC}"
        PROCEDURES_PATCHED=false
    fi

    # Check edge fulltext patch
    if grep -q "Check if FalkorDB - it doesn't support edge fulltext search" "$search_utils" 2>/dev/null; then
        echo -e "${GREEN}✓ Edge fulltext search patch already applied${NC}"
        EDGE_PATCHED=true
    else
        echo -e "${YELLOW}○ Edge fulltext search patch needed${NC}"
        EDGE_PATCHED=false
    fi
}

# Main patching logic
echo "======================================"
echo "FalkorDB Compatibility Patcher"
echo "======================================"
echo ""

# Check current patch status
echo "Checking patch status..."
check_patches
echo ""

# If all patches are applied, we're done
if [ "$QUOTE_PATCHED" = true ] && [ "$PROCEDURES_PATCHED" = true ] && [ "$EDGE_PATCHED" = true ]; then
    echo -e "${GREEN}All patches are already applied!${NC}"
    exit 0
fi

# Ask for confirmation
echo "This script will patch graphiti-core for FalkorDB compatibility."
echo "Backups will be created for all modified files."
echo ""
read -p "Do you want to continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Applying patches..."

# Apply quote syntax patch
if [ "$QUOTE_PATCHED" = false ]; then
    search_utils="$GRAPHITI_PATH/search/search_utils.py"
    apply_patch "$search_utils"

    # Use Python to apply the patch more reliably
    python3 << EOF
import re

with open("$search_utils", 'r') as f:
    content = f.read()

# Replace double quotes with single quotes in group_id
pattern = r'(\[fulltext_syntax \+ f[\'"])group_id:"(\{g\})"([\'"])'
replacement = r'\1group_id:\'\2\'\3'
new_content = re.sub(pattern, replacement, content)

if new_content != content:
    with open("$search_utils", 'w') as f:
        f.write(new_content)
    print("✓ Applied quote syntax patch")
else:
    print("⚠ Quote syntax patch pattern not found or already applied")
EOF
fi

# Apply Neo4j procedures patch
if [ "$PROCEDURES_PATCHED" = false ]; then
    graph_queries="$GRAPHITI_PATH/graph_queries.py"
    apply_patch "$graph_queries"

    python3 << 'EOF'
import sys

graph_queries = sys.argv[1]

with open(graph_queries, 'r') as f:
    lines = f.readlines()

# Find and replace the get_relationships_query function
in_function = False
function_start = -1
for i, line in enumerate(lines):
    if 'def get_relationships_query' in line:
        in_function = True
        function_start = i
    elif in_function and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
        # End of function
        in_function = False
        # Replace the FalkorDB part
        for j in range(function_start, i):
            if 'if provider == GraphProvider.FALKORDB:' in lines[j]:
                # Found the FalkorDB condition
                lines[j+1] = '        # FalkorDB v4.2 doesn\'t support db.idx.fulltext.queryRelationships\n'
                lines[j+2] = '        # Return empty string - the calling code should handle this differently\n'
                lines[j+3] = '        return ""\n'
                break
        break

with open(graph_queries, 'w') as f:
    f.writelines(lines)

print("✓ Applied Neo4j procedures patch")
EOF "$graph_queries"
fi

# Apply edge fulltext search patch
if [ "$EDGE_PATCHED" = false ]; then
    search_utils="$GRAPHITI_PATH/search/search_utils.py"

    python3 << 'EOF'
import sys

search_utils = sys.argv[1]

with open(search_utils, 'r') as f:
    content = f.read()

# Find the edge_fulltext_search function and add the check
import re

# Pattern to find the function and its first lines
pattern = r'(async def edge_fulltext_search\([^)]+\) -> list\[EntityEdge\]:)\s*\n(\s+)(.*?)(\s+fuzzy_query = fulltext_query)'

def replacement(match):
    func_def = match.group(1)
    indent = match.group(2)
    existing_code = match.group(3)
    fuzzy_line = match.group(4)

    # Check if patch is already applied
    if 'Check if FalkorDB' in existing_code:
        return match.group(0)

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

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Also update the query construction
new_content = re.sub(
    r'query = \(\s*get_relationships_query\([^)]+\)',
    'query = (\n        relationships_query',
    new_content
)

with open(search_utils, 'w') as f:
    f.write(new_content)

print("✓ Applied edge fulltext search patch")
EOF "$search_utils"
fi

echo ""
echo -e "${GREEN}======================================"
echo -e "Patches applied successfully!"
echo -e "======================================${NC}"
echo ""

# Test the patches
echo "Testing patches..."
python3 -c "
import asyncio
import sys
sys.path.insert(0, '$PROJECT_ROOT')

try:
    from graphiti_memory import get_shared_memory

    async def test():
        memory = await get_shared_memory()
        results = await memory.search_with_temporal_weight('test')
        print(f'✅ All patches working! Found {len(results)} results')
        return True

    asyncio.run(test())
except Exception as e:
    print(f'❌ Error testing patches: {e}')
    sys.exit(1)
"

echo ""
echo "Note: These patches will be lost if you reinstall or upgrade graphiti-core."
echo "Run this script again after any pip install/upgrade operations."
