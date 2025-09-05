#!/usr/bin/env python3
"""
Debug what Ollama is returning
"""

import asyncio
import json
from openai import AsyncOpenAI


async def test_ollama_response():
    print("\n" + "=" * 60)
    print("DEBUG: TEST OLLAMA JSON RESPONSE")
    print("=" * 60)

    client = AsyncOpenAI(api_key="abc", base_url="http://localhost:11434/v1")

    # Test simple JSON response
    print("\n1. Testing JSON mode...")

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that responds in JSON.",
        },
        {
            "role": "user",
            "content": """Extract entities from this text: 'Alice likes the search feature.'

Respond with JSON in this format:
{
  "extracted_entities": [
    {"name": "entity_name", "summary": "entity_summary"}
  ]
}""",
        },
    ]

    try:
        response = await client.chat.completions.create(
            model="llama3.2:3b",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        print(f"\n   Raw response:\n   {content}")

        # Try to parse
        parsed = json.loads(content)
        print(f"\n   Parsed successfully!")
        print(f"   Keys: {list(parsed.keys())}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_ollama_response())
