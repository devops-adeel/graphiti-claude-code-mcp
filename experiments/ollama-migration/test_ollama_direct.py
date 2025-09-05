#!/usr/bin/env python3
"""
Direct test of Ollama connection to isolate the issue.
"""

import asyncio
from ollama import AsyncClient


async def test_ollama_direct():
    """Test Ollama connection directly"""

    print("Testing Ollama connection...")

    # Test 1: Direct async client
    print("\n1. Testing AsyncClient with localhost:11434")
    try:
        client = AsyncClient(host="http://localhost:11434")
        response = await client.chat(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "Say hello"}],
            stream=False,
        )
        print(f"   ✅ Success! Response: {response['message']['content'][:50]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Test 2: Without http://
    print("\n2. Testing AsyncClient with just localhost:11434")
    try:
        client = AsyncClient(host="localhost:11434")
        response = await client.chat(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "Say hello"}],
            stream=False,
        )
        print(f"   ✅ Success! Response: {response['message']['content'][:50]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Test 3: Default (no host specified)
    print("\n3. Testing AsyncClient with default host")
    try:
        client = AsyncClient()
        response = await client.chat(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "Say hello"}],
            stream=False,
        )
        print(f"   ✅ Success! Response: {response['message']['content'][:50]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Test 4: Test our wrapper
    print("\n4. Testing OllamaNativeClient wrapper")
    try:
        from ollama_native_client import OllamaNativeClient
        from graphiti_core.llm_client.config import LLMConfig

        config = LLMConfig(
            api_key="ollama",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            temperature=0.1,
            max_tokens=4096,
        )

        llm_client = OllamaNativeClient(config=config)
        response = await llm_client._generate_response(
            messages=[{"role": "user", "content": "Say hello"}], temperature=0.1
        )
        print(f"   ✅ Success! Response: {response[:50]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ollama_direct())
