#!/usr/bin/env ./venv/bin/python
"""Final test to verify FalkorDB integration"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load configuration
load_dotenv(".env.graphiti")
load_dotenv(Path.home() / ".env", override=True)  # For OPENAI_API_KEY

print("=" * 60)
print("FalkorDB Integration Test")
print("=" * 60)
print(f"FalkorDB: {os.getenv('FALKORDB_HOST')}:{os.getenv('FALKORDB_PORT')}")
print(f"Database: {os.getenv('FALKORDB_DATABASE')}")
print(f"Group ID: {os.getenv('GRAPHITI_GROUP_ID')}")
print()

async def test():
    try:
        # Test 1: Basic connection
        print("1. Testing connection...")
        from graphiti_memory import get_shared_memory
        memory = await get_shared_memory()
        print("   ✅ Connected to FalkorDB")
        
        # Test 2: Add memory
        print("2. Testing add_memory...")
        memory_id = await memory.add_memory(
            {"title": "FalkorDB Test", "content": "Successfully integrated with FalkorDB"},
            source="test"
        )
        print(f"   ✅ Added memory: {memory_id}")
        
        # Test 3: Search
        print("3. Testing search...")
        results = await memory.search_with_temporal_weight("FalkorDB")
        print(f"   ✅ Search found {len(results)} results")
        
        # Test 4: Pattern capture
        print("4. Testing pattern capture...")
        from capture import get_pattern_capture
        capture = await get_pattern_capture()
        pattern_id = await capture.capture_command_pattern(
            command="redis-cli -h falkordb.local -p 6379 ping",
            context="testing",
            success=True,
            output="PONG"
        )
        print(f"   ✅ Captured pattern: {pattern_id}")
        
        # Test 5: Cross-domain insights
        print("5. Testing cross-domain insights...")
        insights = await memory.find_cross_domain_insights("docker deployment")
        print(f"   ✅ Found {len(insights)} cross-domain insights")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("FalkorDB integration is working correctly")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

success = asyncio.run(test())
exit(0 if success else 1)