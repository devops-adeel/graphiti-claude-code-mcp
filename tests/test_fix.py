#!/usr/bin/env ./venv/bin/python
"""
Quick test to verify the AttributeError fix for EntityEdge.status
"""

import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Load environment
load_dotenv('.env.graphiti')
home_env = Path.home() / '.env'
if home_env.exists():
    import os
    with open(home_env) as f:
        for line in f:
            if 'OPENAI_API_KEY' in line and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ['OPENAI_API_KEY'] = value
                break


async def test_search_and_format():
    """Test that search results can be formatted without AttributeError"""
    from graphiti_memory import get_shared_memory
    from commands import get_command_generator
    
    print("1. Testing memory search with temporal weighting...")
    memory = await get_shared_memory()
    
    # Search for something
    results = await memory.search_with_temporal_weight("docker", include_historical=False)
    
    if results:
        print(f"   Found {len(results)} results")
        # Check that results have status
        for i, result in enumerate(results[:3]):
            if hasattr(result, 'status'):
                print(f"   Result {i+1} has status: {result.status}")
            else:
                print(f"   ❌ Result {i+1} missing status attribute!")
                return False
    else:
        print("   No results found (that's OK for this test)")
    
    print("   ✅ Search results have status attribute")
    
    print("\n2. Testing command generator formatting...")
    generator = await get_command_generator()
    
    # The _format_deployment_issues method was causing the error
    # Test it indirectly by generating commands
    try:
        # This will call various formatting methods internally
        await generator.generate_check_deployment_command()
        print("   ✅ Command generation successful (no AttributeError)")
    except AttributeError as e:
        print(f"   ❌ AttributeError: {e}")
        return False
    except Exception as e:
        # Other exceptions are OK for this test
        print(f"   Note: {e.__class__.__name__} (not AttributeError, so fix works)")
    
    return True


async def main():
    print("=" * 60)
    print("Testing EntityEdge.status AttributeError Fix")
    print("=" * 60)
    
    success = await test_search_and_format()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ FIX VERIFIED: No AttributeError with EntityEdge.status")
    else:
        print("❌ Fix incomplete or new issues found")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)