#!/usr/bin/env ./venv/bin/python
"""Simple test to verify basic functionality"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load configuration properly
load_dotenv(".env.graphiti")
home_env = Path.home() / '.env'
if home_env.exists():
    with open(home_env) as f:
        for line in f:
            if 'OPENAI_API_KEY' in line and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ['OPENAI_API_KEY'] = value
                break

print(f"FalkorDB: {os.getenv('FALKORDB_HOST')}:{os.getenv('FALKORDB_PORT')}")

async def test():
    from graphiti_memory import get_shared_memory
    
    print("1. Getting shared memory...")
    memory = await get_shared_memory()
    print("✅ Connected")
    
    print("2. Adding a test memory...")
    memory_id = await memory.add_memory(
        {"title": "Test", "content": "Test memory from simple test"},
        source="test"
    )
    print(f"✅ Added memory: {memory_id}")
    
    print("3. Searching...")
    results = await memory.search_with_temporal_weight("test")
    print(f"✅ Found {len(results)} results")
    
    return True

asyncio.run(test())