#!/usr/bin/env ./venv/bin/python
"""Test FalkorDB connection with correct configuration"""

import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

# Load only .env.graphiti (not ~/.env which has Docker settings)
load_dotenv('.env.graphiti')
# Only load OpenAI key from home
home_env = Path.home() / '.env'
if home_env.exists():
    with open(home_env) as f:
        for line in f:
            if 'OPENAI_API_KEY' in line and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ['OPENAI_API_KEY'] = value
                break

print(f"FALKORDB_HOST: {os.getenv('FALKORDB_HOST')}")
print(f"FALKORDB_PORT: {os.getenv('FALKORDB_PORT')}")
print(f"OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY') and not os.getenv('OPENAI_API_KEY').startswith('placeholder'))}")

async def test_connection():
    """Test connection to FalkorDB"""
    try:
        from graphiti_memory import get_shared_memory
        
        print("\nTesting FalkorDB connection...")
        memory = await get_shared_memory()
        print("✅ Successfully connected to FalkorDB!")
        
        # Try a simple search
        results = await memory.search_with_temporal_weight("test", include_historical=False)
        print(f"✅ Search executed successfully (found {len(results)} results)")
        
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)