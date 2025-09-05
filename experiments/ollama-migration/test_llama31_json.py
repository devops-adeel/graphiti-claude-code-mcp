#!/usr/bin/env python3
"""
Test llama3.1:8b model's ability to handle Pydantic JSON schemas
"""

import asyncio
import json
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import List


class Entity(BaseModel):
    """Simple entity model to test extraction"""

    name: str
    summary: str


class ExtractedData(BaseModel):
    """Container for extracted entities"""

    entities: List[Entity]


async def test_model_extraction():
    print("\n" + "=" * 60)
    print("TESTING LLAMA3.1:8B JSON EXTRACTION")
    print("=" * 60)

    # Test with both models for comparison
    models = ["llama3.2:3b", "llama3.1:8b"]

    client = AsyncOpenAI(api_key="abc", base_url="http://localhost:11434/v1")

    # The text to extract from
    test_text = "Alice likes the search feature. Bob thinks the UI needs improvement."

    # Get the JSON schema from Pydantic
    schema = ExtractedData.model_json_schema()

    for model in models:
        print(f"\n{'='*40}")
        print(f"Testing {model}")
        print(f"{'='*40}")

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that extracts entities from text and returns them in JSON format.",
            },
            {
                "role": "user",
                "content": f"""Extract entities from this text: '{test_text}'

Respond with JSON that matches this schema:
{json.dumps(schema, indent=2)}

Return ONLY the JSON data, not the schema itself.""",
            },
        ]

        try:
            print(f"\n1. Sending request to {model}...")
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            content = response.choices[0].message.content
            print(f"\n2. Raw response:\n{content[:500]}...")  # First 500 chars

            # Try to parse
            print("\n3. Attempting to parse JSON...")
            parsed = json.loads(content)

            # Check if it's the schema or actual data
            if "$defs" in parsed or "type" in parsed and parsed.get("type") == "object":
                print("   ❌ Model returned the schema definition instead of data!")
            else:
                print(f"   ✅ Parsed successfully!")
                print(f"   Keys: {list(parsed.keys())}")

                # Try to validate with Pydantic
                print("\n4. Validating with Pydantic model...")
                try:
                    validated = ExtractedData.model_validate(parsed)
                    print(f"   ✅ Validation successful!")
                    print(f"   Found {len(validated.entities)} entities:")
                    for entity in validated.entities:
                        print(f"      - {entity.name}: {entity.summary}")
                except Exception as e:
                    print(f"   ❌ Validation failed: {e}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("CONCLUSIONS:")
    print("- llama3.2:3b likely returns the schema itself")
    print("- llama3.1:8b should extract actual data correctly")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_model_extraction())
