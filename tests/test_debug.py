#!/usr/bin/env ./venv/bin/python
"""Debug test to see where it's hanging"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load configuration
load_dotenv(".env.graphiti")

# Load OPENAI_API_KEY from home
home_env = Path.home() / ".env"
if home_env.exists():
    with open(home_env) as f:
        for line in f:
            if "OPENAI_API_KEY" in line and "=" in line:
                key, value = line.strip().split("=", 1)
                os.environ["OPENAI_API_KEY"] = value.strip('"').strip("'")
                break

print(f"Neo4j: {os.getenv('NEO4J_HOST')}:{os.getenv('NEO4J_PORT')}")
print(
    f"OpenAI key set: {bool(os.getenv('OPENAI_API_KEY') and not os.getenv('OPENAI_API_KEY').startswith('placeholder'))}"
)


async def test():
    print("1. Importing graphiti_memory...")
    from graphiti_memory import SharedMemory

    print("2. Creating SharedMemory instance...")
    memory = SharedMemory()

    print("3. Initializing connection...")
    try:
        await memory.initialize()
        print("✅ Initialized")
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


asyncio.run(test())
