# Graphiti + Ollama Integration: 1024-Dimension Solution

## Problem Statement
Graphiti hardcodes vector indexes to 1024 dimensions but we were using nomic-embed-text with 768 dimensions, causing "Invalid input for 'vector.similarity.cosine()'" errors.

## Root Cause Analysis
1. Graphiti's `build_dynamic_indexes()` function hardcodes 1024 dimensions for all vector indexes
2. This is found in `graphiti_core/utils/maintenance/graph_data_operations.py`
3. Vector indexes are created dynamically during `add_episode()`, not during `build_indices_and_constraints()`
4. Dimension mismatch between embeddings (768) and indexes (1024) causes Neo4j errors

## Solution: Architectural Alignment
Instead of fighting Graphiti's design, align with it by using a 1024-dimension embedding model.

### Selected Model: mxbai-embed-large
- **Dimensions**: 1024 (perfect match for Graphiti)
- **Size**: 670MB
- **Performance**: Outperforms OpenAI's text-embedding-3-large
- **Compatibility**: Works seamlessly with Ollama's OpenAI-compatible API

## Implementation Steps

### 1. Update Neo4j with APOC Plugin
```yaml
# docker-compose.yml in graphiti-neo4j project
environment:
  - NEO4J_PLUGINS=["apoc"]
```

### 2. Pull the 1024-Dimension Model
```bash
ollama pull mxbai-embed-large
```

### 3. Configure Graphiti with Aligned Dimensions
```python
from graphiti_core import Graphiti
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

llm_config = LLMConfig(
    api_key="ollama",
    model="llama3.1:8b",
    base_url="http://localhost:11434/v1",
    temperature=0.1,  # Lower for consistency
)

llm_client = OpenAIGenericClient(config=llm_config)

graphiti = Graphiti(
    "bolt://neo4j.graphiti.local:7687",
    "neo4j",
    "your-password",
    llm_client=llm_client,
    embedder=OpenAIEmbedder(
        config=OpenAIEmbedderConfig(
            api_key="ollama",
            embedding_model="mxbai-embed-large",  # 1024 dimensions
            embedding_dim=1024,  # Must be 1024
            base_url="http://localhost:11434/v1",
        )
    ),
    cross_encoder=OpenAIRerankerClient(
        client=llm_client,
        config=llm_config
    ),
)
```

## Verification Results
✅ Vector indexes created automatically with 1024 dimensions
✅ Embeddings generated correctly at 1024 dimensions
✅ Vector similarity search works without errors
✅ Cosine similarity calculations function properly

## Remaining Challenge: LLM JSON Schema Extraction
While vector operations work perfectly, Ollama models struggle with Graphiti's complex JSON schema prompts. The models tend to return the schema itself rather than data following the schema.

### Workarounds:
1. Use larger models (70B+) for better schema understanding
2. Create custom LLM client with clearer prompting (see ollama_graphiti_client.py)
3. Use temperature=0.1 for more consistent JSON output
4. Simplify episode content for easier extraction

## Key Insights
1. **Work WITH frameworks, not against them**: Instead of modifying Graphiti or creating manual indexes, we aligned our embedding model choice with Graphiti's expectations
2. **Vector indexes are created dynamically**: Graphiti creates them during first entity/edge insertion, not during initial setup
3. **Dimension alignment is critical**: All components (embedder, indexes, queries) must use the same dimensions
4. **APOC plugin is required**: Neo4j needs APOC for vector operations

## Benefits of This Approach
- Clean, maintainable solution
- No code modifications to Graphiti
- Automatic vector index management
- Better embedding model performance
- Future-proof (works with Graphiti updates)

## Testing Commands
```bash
# Test vector index creation
python test_vector_index_creation.py

# Test vector search functionality
python test_vector_search.py

# Check embedding dimensions
python -c "
import asyncio
from neo4j import AsyncGraphDatabase
async def check():
    driver = AsyncGraphDatabase.driver('bolt://neo4j.graphiti.local:7687', auth=('neo4j', 'password'))
    async with driver.session() as session:
        result = await session.run('MATCH (n:Entity) WHERE n.name_embedding IS NOT NULL RETURN size(n.name_embedding) as dim LIMIT 1')
        data = await result.single()
        print(f'Embedding dimensions: {data[\"dim\"]}')
    await driver.close()
asyncio.run(check())
"
```

## Conclusion
The 1024-dimension alignment strategy successfully resolves the vector index issues while maintaining compatibility with Graphiti's architecture. This solution is production-ready for vector operations, though LLM extraction may need additional refinement based on specific use cases.
