# GitHub Issue Draft for getzep/graphiti

## Title
[BUG] Three critical issues break Ollama integration: Embedder parameter mismatch, structured output endpoint, and Pydantic validation

## Labels
- bug

## Body

## Bug Description

When using Ollama with graphiti-core, there are three critical issues that completely break the integration:

### Issue 1: Embedder Parameter Mismatch
The graphiti-core library internally calls `embedder.create(input=...)` but `OpenAIEmbedder` expects `create(input_data=...)`. This causes immediate failure with `TypeError: create() got an unexpected keyword argument 'input'`.

### Issue 2: Structured Output Endpoint Not Supported
Even after fixing the embedder parameter issue, Ollama integration fails because:
- `OpenAIClient` uses OpenAI's beta structured output endpoint: `/v1/chat/completions/parse`
- Ollama only supports the standard `/v1/chat/completions` endpoint
- This results in `404 page not found` errors when trying to add episodes

### Issue 3: Pydantic Validation Failures
Even with both above issues fixed using `OpenAIGenericClient`, entity extraction still fails:
- Ollama's responses don't match the strict Pydantic model validation
- Results in `ValidationError: Field required` for ExtractedEntities
- The JSON structure from Ollama doesn't align with graphiti-core's expected schema

These bugs prevent anyone from using Ollama as a local alternative to OpenAI, which is critical for users who need to run everything locally due to corporate policies, privacy requirements, or cost considerations.

## Root Cause Analysis

The issue occurs in the call chain:
1. `graphiti_core` calls embeddings with: `await self.embedder.create(input=[text])`
2. `OpenAIEmbedder.create()` expects: `async def create(self, input_data: Union[str, List[str]], **kwargs)`
3. Result: Parameter name mismatch causes immediate failure

## Steps to Reproduce

```python
import asyncio
import os
from graphiti_core import Graphiti
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

# Configure for Ollama
llm_config = LLMConfig(
    api_key="ollama",
    model="llama3.2:3b",
    base_url="http://localhost:11434/v1",
)

embedder_config = OpenAIEmbedderConfig(
    api_key="ollama",
    embedding_model="nomic-embed-text",
    base_url="http://localhost:11434/v1",
)

# This will fail when trying to generate embeddings
graphiti = Graphiti(
    "bolt://localhost:7687",
    "neo4j",
    "password",
    llm_client=OpenAIClient(config=llm_config),
    embedder=OpenAIEmbedder(config=embedder_config)
)

# Attempt to add episode - fails with parameter mismatch
await graphiti.add_episode(
    name="test",
    episode_body="test content",
    source="text"
)
```

## Expected Behavior

The embedder should accept the `input` parameter and generate embeddings successfully, allowing Ollama to work as a drop-in replacement for OpenAI.

## Actual Behavior

### Error 1: Embedder parameter mismatch
```
TypeError: OpenAIEmbedder.create() got an unexpected keyword argument 'input'
```

### Error 2: After fixing embedder (using OpenAIClient)
```
404 page not found
```

### Error 3: After using OpenAIGenericClient
```
ValidationError: 1 validation error for ExtractedEntities
extracted_entities
  Field required [type=missing, input_value={'$defs': {'ExtractedEnti...ties', 'type': 'object'}, input_type=dict]
```

These errors prevent any episodes from being added to the graph when using Ollama.

## Environment

- **Graphiti Version**: 0.18.9 - 0.20.1 (affects all recent versions)
- **Python Version**: 3.9+
- **Operating System**: All
- **Database Backend**: Neo4j 5.x
- **LLM Provider & Model**: Ollama with any model (llama3.2, nomic-embed-text, etc.)

## Partial Workaround

Note: Even with these fixes, entity extraction may still fail due to Pydantic validation issues. A complete solution requires additional work on structured output handling.

To partially make Ollama work with graphiti-core, users need TWO fixes:

### Fix 1: Embedder Wrapper for Parameter Mismatch

```python
from typing import Union, List, Iterable
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

class OllamaEmbedderWrapper(OpenAIEmbedder):
    """
    Wrapper that fixes the parameter name mismatch between graphiti-core and OpenAIEmbedder.
    Graphiti-core calls create(input=...) but OpenAIEmbedder expects create(input_data=...)
    """

    async def create(
        self,
        input: Union[str, List[str], Iterable[int], Iterable[Iterable[int]]] = None,
        input_data: Union[str, List[str], Iterable[int], Iterable[Iterable[int]]] = None,
        **kwargs
    ) -> list[float]:
        # Use input_data if provided, otherwise fall back to input parameter
        data = input_data if input_data is not None else input

        if data is None:
            raise ValueError("Either 'input' or 'input_data' must be provided")

        # Call parent with correct parameter name
        return await super().create(input_data=data, **kwargs)
```

### Fix 2: Use OpenAIGenericClient Instead of OpenAIClient

```python
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.llm_client.config import LLMConfig

# Use OpenAIGenericClient which doesn't use the /parse endpoint
llm_config = LLMConfig(
    api_key="ollama",
    model="llama3.2:3b",
    base_url="http://localhost:11434/v1",
)

llm_client = OpenAIGenericClient(config=llm_config)  # NOT OpenAIClient!
embedder = OllamaEmbedderWrapper(config=embedder_config)

graphiti = Graphiti(
    "bolt://localhost:7687",
    "neo4j",
    "password",
    llm_client=llm_client,  # Use OpenAIGenericClient
    embedder=embedder  # Use wrapper
)
```

## Proposed Solutions

### Option 1: Comprehensive Ollama Support (Recommended)
Create dedicated Ollama support in graphiti-core:
1. Fix the embedder parameter mismatch (use `input_data` consistently)
2. Use `OpenAIGenericClient` or create `OllamaClient` for non-structured endpoints
3. Implement JSON parsing fallback for entity extraction when Pydantic validation fails
4. Add official Ollama examples and documentation

### Option 2: Fix Individual Issues
1. **Embedder Fix**: Make OpenAIEmbedder accept both `input` and `input_data` parameters
2. **Client Fix**: Auto-detect Ollama base URL and use OpenAIGenericClient
3. **Validation Fix**: Add relaxed validation mode for non-OpenAI providers

### Option 3: Create Official OllamaEmbedder and OllamaClient Classes
Create dedicated classes that handle all Ollama-specific requirements:
```python
class OllamaEmbedder(BaseEmbedder):
    # Handle parameter naming and dimension differences

class OllamaClient(BaseLLMClient):
    # Handle non-structured output and relaxed validation
```

## Additional Issues Found

Even with the parameter mismatch fixed, there are additional issues with Ollama integration:

1. **Transaction Commit Failures**: Neo4j transactions don't commit properly, leaving all memory IDs with a "pending_" prefix
2. **Embedding Dimension Mismatch**: Some Ollama models have different embedding dimensions than expected
3. **Missing Examples**: No official documentation or examples for Ollama setup

## Impact

- **Severity**: High - Completely breaks Ollama integration
- **Affected Users**: Anyone trying to use local models instead of OpenAI
- **Workaround Available**: Yes, but requires custom wrapper code

## Related Issues

- #868 - User getting "Field required" errors with Ollama
- #759 - Embedding issues with Ollama showing missing properties
- #337 - Request for Ollama examples (closed without proper solution)

## Community Impact

This bug is particularly impactful because:
1. Many users need local LLM solutions for privacy/security reasons
2. Ollama is one of the most popular local LLM solutions
3. The error message doesn't clearly indicate the root cause
4. Users waste significant time debugging what appears to be configuration issues

## Request

Please consider this a high-priority fix as it blocks a significant use case (local LLM deployment) and affects multiple users based on the related issues. The fix is relatively simple but has high impact for the community.

Thank you for maintaining this excellent library! Happy to provide more details or test fixes if needed.
