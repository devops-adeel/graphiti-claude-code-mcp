#!/usr/bin/env python3
"""
Step 4b: Test Ollama embedding generation directly
"""

import asyncio
import httpx


async def test_ollama_embedding():
    print("\n" + "=" * 60)
    print("STEP 4b: TEST OLLAMA EMBEDDING DIRECTLY")
    print("=" * 60)

    # Test embedding generation
    print("\n1. Testing Ollama embedding endpoint...")

    url = "http://localhost:11434/v1/embeddings"
    headers = {"Content-Type": "application/json"}
    data = {"model": "nomic-embed-text", "input": "Test embedding generation"}

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.post(url, json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                result = response.json()
                embedding = result["data"][0]["embedding"]
                print(f"   ✅ Embedding generated successfully")
                print(f"   Dimensions: {len(embedding)}")
                print(f"   First 5 values: {embedding[:5]}")
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Connection error: {e}")

    # Test with OpenAI client
    print("\n2. Testing with OpenAI client (no SSL)...")
    try:
        from openai import AsyncOpenAI

        # Create client without SSL verification
        client = AsyncOpenAI(
            api_key="abc",
            base_url="http://localhost:11434/v1",
            http_client=httpx.AsyncClient(verify=False),  # Disable SSL verification
        )

        response = await client.embeddings.create(
            model="nomic-embed-text", input="Test embedding with OpenAI client"
        )

        embedding = response.data[0].embedding
        print(f"   ✅ OpenAI client worked!")
        print(f"   Dimensions: {len(embedding)}")

    except Exception as e:
        print(f"   ❌ OpenAI client error: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_ollama_embedding())
