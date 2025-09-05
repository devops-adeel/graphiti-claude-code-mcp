#!/usr/bin/env python3
"""
Step 2: Initialize Graphiti with Ollama using OpenAI compatibility
Following: https://help.getzep.com/graphiti/configuration/llm-configuration#ollama-local-llms
"""

import asyncio
import logging

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def init_graphiti():
    print("\n" + "=" * 60)
    print("STEP 2: INITIALIZE GRAPHITI WITH OLLAMA")
    print("=" * 60)

    try:
        from graphiti_core import Graphiti
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_client import OpenAIClient
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )

        print("\n1. Configuring LLM client...")
        # Configure Ollama LLM client (from official docs)
        llm_config = LLMConfig(
            api_key="abc",  # Ollama doesn't require a real API key
            model="llama3.2:3b",
            base_url="http://localhost:11434/v1",  # Ollama OpenAI-compatible endpoint
        )

        llm_client = OpenAIClient(config=llm_config)
        print("   ✅ LLM client configured")

        print("\n2. Configuring embedder...")
        embedder_config = OpenAIEmbedderConfig(
            api_key="abc",
            embedding_model="nomic-embed-text",
            embedding_dim=768,  # Critical: specify dimensions
            base_url="http://localhost:11434/v1",
        )
        embedder = OpenAIEmbedder(config=embedder_config)
        print("   ✅ Embedder configured with 768 dimensions")

        print("\n3. Initializing Graphiti...")
        graphiti = Graphiti(
            "bolt://localhost:7688",
            "neo4j",
            "password",
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
        )
        print("   ✅ Graphiti initialized successfully")

        # Save graphiti instance for next step
        return graphiti

    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        import traceback

        traceback.print_exc()
        return None


async def main():
    graphiti = await init_graphiti()
    if graphiti:
        print("\n" + "=" * 60)
        print("SUCCESS: Graphiti initialized and ready")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("FAILED: Could not initialize Graphiti")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
