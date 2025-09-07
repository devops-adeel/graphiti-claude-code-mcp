#!/usr/bin/env python3
"""Debug Ollama connection"""

import asyncio
import os
from ollama import AsyncClient


async def test_ollama():
    """Test Ollama connection directly"""

    # Set NO_PROXY to ensure localhost connections bypass any proxy
    os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"

    # Test different host configurations
    hosts = [
        "http://localhost:11434",
        "http://localhost:11434/v1",
        "http://127.0.0.1:11434",
    ]

    for host in hosts:
        print(f"\n🔍 Testing host: {host}")

        # Remove /v1 if present (like OllamaEmbedder does)
        test_host = host[:-3] if host.endswith("/v1") else host

        try:
            # Use trust_env=False to avoid SSL/proxy environment interference
            client = AsyncClient(host=test_host, trust_env=False)
            response = await client.embeddings(model="mxbai-embed-large", prompt="test")
            print(
                f"   ✅ SUCCESS! Got embedding with {len(response['embedding'])} dimensions"
            )
        except Exception as e:
            print(f"   ❌ FAILED: {e}")

    # Now test what the memory system sees
    print("\n🔍 Testing what graphiti_memory sees:")
    os.environ["OLLAMA_HOST"] = "http://localhost:11434"
    ollama_host = os.getenv("OLLAMA_HOST")
    if not ollama_host.endswith("/v1"):
        ollama_host = f"{ollama_host}/v1"
    print(f"   Original: {os.getenv('OLLAMA_HOST')}")
    print(f"   Modified: {ollama_host}")

    # Test with the modified host (removing /v1 in OllamaEmbedder)
    if ollama_host.endswith("/v1"):
        final_host = ollama_host[:-3]
    print(f"   Final in OllamaEmbedder: {final_host}")

    try:
        # Use trust_env=False to avoid SSL/proxy environment interference
        client = AsyncClient(host=final_host, trust_env=False)
        response = await client.embeddings(model="mxbai-embed-large", prompt="test")
        print(f"   ✅ Would work! Got embedding")
    except Exception as e:
        print(f"   ❌ Would fail: {e}")


if __name__ == "__main__":
    asyncio.run(test_ollama())
