"""
Embedder wrapper for Ollama that handles parameter name compatibility.
Fixes the mismatch between Graphiti calling create(input=...) and OpenAIEmbedder expecting create(input_data=...).
"""

import logging
from typing import Union, List, Optional, Iterable
from ollama import AsyncClient
from graphiti_core.embedder.client import EmbedderClient

logger = logging.getLogger(__name__)


class OllamaEmbedder(EmbedderClient):
    """
    Native Ollama embedder that works with Graphiti's expectations.
    Accepts both 'input' and 'input_data' parameters for compatibility.
    """

    def __init__(
        self,
        model: str = "mxbai-embed-large",
        host: str = "http://localhost:11434",
        embedding_dim: int = 1024,  # mxbai-embed-large dimension
    ):
        """
        Initialize the Ollama embedder.

        Args:
            model: The embedding model to use (default: mxbai-embed-large)
            host: The Ollama host URL
            embedding_dim: The dimension of embeddings (for compatibility)
        """
        # Remove /v1 suffix if present (from OpenAI compatibility)
        if host.endswith("/v1"):
            host = host[:-3]

        # Set NO_PROXY to ensure localhost connections bypass any proxy
        import os

        current_no_proxy = os.environ.get("NO_PROXY", "")
        if current_no_proxy:
            os.environ["NO_PROXY"] = f"{current_no_proxy},localhost,127.0.0.1,::1"
        else:
            os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"

        # Create client with trust_env=False to avoid SSL/proxy environment interference
        # This prevents httpx from using environment variables that might force SSL on HTTP connections
        self.client = AsyncClient(host=host, trust_env=False)
        self.model = model
        self.embedding_dim = embedding_dim
        logger.info(
            f"Initialized OllamaEmbedder with model: {model} at {host} (trust_env=False)"
        )

    async def create(
        self,
        input_data: Union[
            str, List[str], Iterable[int], Iterable[Iterable[int]]
        ] = None,
        input: Union[str, List[str]] = None,
        **kwargs,
    ) -> List[float] | List[List[float]]:
        """
        Generate embeddings using Ollama's native API.
        Accepts both 'input' and 'input_data' parameters for compatibility.

        Args:
            input_data: Text or list of texts to embed (EmbedderClient expects this)
            input: Alternative parameter name (for backward compatibility)
            **kwargs: Additional parameters (ignored)

        Returns:
            List of embedding vectors (list[float] for single, list[list[float]] for multiple)
        """
        # Handle both parameter names - this is the key fix!
        data = input_data if input_data is not None else input

        if data is None:
            raise ValueError("Either 'input' or 'input_data' must be provided")

        # Handle integer iterables (token IDs) - convert to string for Ollama
        if isinstance(data, Iterable) and not isinstance(data, (str, list)):
            data = str(list(data))

        # Track if we need to return single embedding or list
        is_single = isinstance(data, str)

        # Ensure it's a list for consistent processing
        if is_single:
            data = [data]

        logger.debug(f"Generating embeddings for {len(data)} text(s)")

        # Generate embeddings using native Ollama API
        embeddings = []
        for i, text in enumerate(data):
            try:
                # Call Ollama's embeddings endpoint
                response = await self.client.embeddings(model=self.model, prompt=text)

                # Extract the embedding vector
                embedding = response["embedding"]
                embeddings.append(embedding)

                logger.debug(
                    f"Generated embedding {i+1}/{len(data)} with dimension {len(embedding)}"
                )

            except Exception as e:
                logger.error(f"Failed to generate embedding for text {i}: {e}")
                raise

        logger.debug(f"Successfully generated {len(embeddings)} embeddings")

        # Return single embedding if input was single string
        if is_single and len(embeddings) == 1:
            return embeddings[0]

        return embeddings

    async def create_batch(
        self, input_data_list: List[str], **kwargs
    ) -> List[List[float]]:
        """
        Batch embedding generation for compatibility with Graphiti.

        Args:
            input_data_list: List of texts to embed
            **kwargs: Additional parameters (ignored)

        Returns:
            List of embedding vectors
        """
        return await self.create(input_data=input_data_list, **kwargs)

    # Add these properties for compatibility with OpenAIEmbedder interface
    @property
    def config(self):
        """Mock config property for interface compatibility."""

        class MockConfig:
            def __init__(self, model, dim):
                self.embedding_model = model
                self.embedding_dim = dim

        return MockConfig(self.model, self.embedding_dim)
