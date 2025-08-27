#!/usr/bin/env python3
"""
Test FalkorDB connection with different OrbStack configurations
"""

import os
import sys
import asyncio
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_connection():
    """Test different FalkorDB connection configurations"""
    
    # Test configurations for OrbStack
    configs = [
        {
            "name": "localhost with mapped port",
            "FALKORDB_HOST": "localhost", 
            "FALKORDB_PORT": "6379"
        },
        {
            "name": "OrbStack custom domain",
            "FALKORDB_HOST": "falkordb.local", 
            "FALKORDB_PORT": "6379"
        },
        {
            "name": "Direct container IP",
            "FALKORDB_HOST": "192.168.148.2", 
            "FALKORDB_PORT": "6379"
        },
        {
            "name": "OrbStack automatic domain",
            "FALKORDB_HOST": "falkordb.orb.local",
            "FALKORDB_PORT": "6379"
        }
    ]
    
    print("=" * 60)
    print("Testing FalkorDB Connections for OrbStack")
    print("=" * 60)
    
    # Test each configuration
    for config in configs:
        print(f"\nTesting: {config['name']}")
        print(f"  Host: {config['FALKORDB_HOST']}")
        print(f"  Port: {config['FALKORDB_PORT']}")
        
        # Update environment
        os.environ["FALKORDB_HOST"] = config["FALKORDB_HOST"]
        os.environ["FALKORDB_PORT"] = config["FALKORDB_PORT"]
        
        try:
            # Test with FalkorDB client directly
            from falkordb import FalkorDB
            db = FalkorDB(
                host=config["FALKORDB_HOST"],
                port=int(config["FALKORDB_PORT"])
            )
            graph = db.select_graph("test")
            print(f"  ✅ FalkorDB client connected")
            
            # Test with graphiti_memory
            from graphiti_memory import get_shared_memory
            memory = await get_shared_memory()
            print(f"  ✅ SharedMemory initialized")
            print(f"     Group ID: {memory.group_id}")
            print(f"     Database: {memory.database}")
            
            # Test a simple search
            results = await memory.search_with_temporal_weight("test")
            print(f"  ✅ Search executed (found {len(results)} results)")
            
            await memory.close()
            
            print(f"\n🎉 SUCCESS: {config['name']} works!")
            print("=" * 60)
            
            # Return the working configuration
            return config
            
        except Exception as e:
            print(f"  ❌ Failed: {str(e)[:100]}")
            continue
    
    print("\n❌ All connection attempts failed")
    return None


async def test_mcp_tools():
    """Test MCP tools after finding working configuration"""
    print("\n" + "=" * 60)
    print("Testing MCP Tools")
    print("=" * 60)
    
    try:
        # Import MCP server components
        from mcp_server import server
        from graphiti_memory import get_shared_memory
        
        # Test memory search
        memory = await get_shared_memory()
        print("\n1. Testing memory search...")
        results = await memory.search_with_temporal_weight(
            "docker error"
        )
        print(f"   Found {len(results)} results")
        
        # Test GTD context retrieval
        print("\n2. Testing GTD context retrieval...")
        gtd_tasks = await memory.search_with_temporal_weight(
            "task @computer",
            filter_source="gtd_coach"
        )
        print(f"   Found {len(gtd_tasks)} GTD tasks")
        
        # Test cross-domain insights
        print("\n3. Testing cross-domain insights...")
        insights = await memory.find_cross_domain_insights("docker")
        print(f"   Found {len(insights)} cross-domain connections")
        
        await memory.close()
        print("\n✅ All MCP tool tests passed!")
        
    except Exception as e:
        print(f"\n❌ MCP tool test failed: {e}")


async def main():
    """Main test runner"""
    # First find a working connection
    working_config = await test_connection()
    
    if working_config:
        # Apply the working configuration
        os.environ["FALKORDB_HOST"] = working_config["FALKORDB_HOST"]
        os.environ["FALKORDB_PORT"] = working_config["FALKORDB_PORT"]
        
        print(f"\n✨ Using configuration: {working_config['name']}")
        print(f"   FALKORDB_HOST={working_config['FALKORDB_HOST']}")
        print(f"   FALKORDB_PORT={working_config['FALKORDB_PORT']}")
        
        # Test MCP tools with working configuration
        await test_mcp_tools()
        
        # Save working configuration
        print("\n📝 To make this permanent, add to .env.graphiti:")
        print(f"   FALKORDB_HOST={working_config['FALKORDB_HOST']}")
        print(f"   FALKORDB_PORT={working_config['FALKORDB_PORT']}")
    else:
        print("\n⚠️ Could not establish FalkorDB connection")
        print("Please check:")
        print("1. FalkorDB container is running: docker ps | grep falkor")
        print("2. OrbStack networking is enabled")
        print("3. Port mappings are correct")


if __name__ == "__main__":
    # Ensure we're in the virtual environment
    venv_path = Path(__file__).parent / "venv"
    if venv_path.exists() and sys.prefix != str(venv_path):
        print("⚠️ Not in virtual environment. Please run:")
        print("   source venv/bin/activate")
        print("   python test_connection.py")
        sys.exit(1)
    
    asyncio.run(main())