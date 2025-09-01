#!/usr/bin/env ./venv/bin/python
"""
Test script to verify all Graphiti MCP tools are working
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphiti_memory import get_shared_memory
from capture import get_pattern_capture, PatternType
from commands import get_command_generator


async def test_capture_solution():
    """Test capture_solution tool"""
    print("\n1. Testing capture_solution...")
    try:
        capture = await get_pattern_capture()
        memory_id = await capture.capture_deployment_solution(
            error="Docker container fails to start",
            solution="Fix port mapping in docker-compose.yml",
            context={"environment": "production", "service": "api"},
        )
        print(f"   ✅ Success: Created memory {memory_id}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def test_capture_tdd_pattern():
    """Test capture_tdd_pattern tool"""
    print("\n2. Testing capture_tdd_pattern...")
    try:
        capture = await get_pattern_capture()
        memory_id = await capture.capture_tdd_cycle(
            test_code="def test_add(): assert add(2, 3) == 5",
            implementation="def add(a, b): return a + b",
            feature_name="addition_function",
        )
        print(f"   ✅ Success: Created TDD pattern {memory_id}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def test_search_memory():
    """Test search_memory tool"""
    print("\n3. Testing search_memory...")
    try:
        memory = await get_shared_memory()
        results = await memory.search_with_temporal_weight(
            query="docker error", include_historical=False, filter_source="claude_code"
        )
        print(f"   ✅ Success: Found {len(results)} results")

        # Test that results can be formatted without errors
        for r in results[:2]:
            # Check if we can access expected fields
            score = getattr(r, "final_score", getattr(r, "score", 0))
            status = getattr(r, "status", "unknown")
            print(f"      - Score: {score}, Status: {status}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def test_find_cross_insights():
    """Test find_cross_insights tool"""
    print("\n4. Testing find_cross_insights...")
    try:
        memory = await get_shared_memory()
        insights = await memory.find_cross_domain_insights("deployment")
        print(f"   ✅ Success: Found {len(insights)} cross-domain insights")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def test_get_gtd_context():
    """Test get_gtd_context tool"""
    print("\n5. Testing get_gtd_context...")
    try:
        memory = await get_shared_memory()

        # Get GTD context
        tasks = await memory.search_with_temporal_weight(
            "computer task active", filter_source="gtd_coach"
        )
        projects = await memory.search_with_temporal_weight(
            "project active", filter_source="gtd_coach"
        )

        context = {"active_tasks": len(tasks), "active_projects": len(projects)}

        print(
            f"   ✅ Success: Got GTD context (tasks: {context['active_tasks']}, projects: {context['active_projects']})"
        )
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def test_supersede_memory():
    """Test supersede_memory tool"""
    print("\n6. Testing supersede_memory...")
    try:
        memory = await get_shared_memory()

        # First create a memory to supersede
        old_id = await memory.add_memory(
            {"title": "Old solution", "content": "Old approach"}, source="test"
        )

        # Now supersede it
        new_id = await memory.supersede_memory(
            old_id=old_id,
            new_content={"title": "New solution", "content": "Better approach"},
            reason="Found better solution",
        )

        print(f"   ✅ Success: Superseded {old_id} with {new_id}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def test_capture_command():
    """Test capture_command tool"""
    print("\n7. Testing capture_command...")
    try:
        capture = await get_pattern_capture()
        memory_id = await capture.capture_command_pattern(
            command="docker-compose up -d",
            context="deployment",
            success=True,
            output="Services started successfully",
        )
        print(f"   ✅ Success: Captured command pattern {memory_id}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def test_get_memory_evolution():
    """Test get_memory_evolution tool"""
    print("\n8. Testing get_memory_evolution...")
    try:
        memory = await get_shared_memory()
        evolution = await memory.get_memory_evolution("docker")
        print(f"   ✅ Success: Got evolution with {len(evolution)} chains")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def test_generate_commands():
    """Test generate_commands tool"""
    print("\n9. Testing generate_commands...")
    try:
        generator = await get_command_generator()
        # Don't actually generate files, just test initialization
        print(f"   ✅ Success: Command generator initialized")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Graphiti MCP Tools")
    print("=" * 60)

    # Load environment - only .env.graphiti for Neo4j settings
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv(".env.graphiti")

    # Only load OpenAI key from home .env
    home_env = Path.home() / ".env"
    if home_env.exists():
        import os

        with open(home_env) as f:
            for line in f:
                if "OPENAI_API_KEY" in line and "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ["OPENAI_API_KEY"] = value
                    break

    # Run tests
    results = []
    results.append(await test_capture_solution())
    results.append(await test_capture_tdd_pattern())
    results.append(await test_search_memory())
    results.append(await test_find_cross_insights())
    results.append(await test_get_gtd_context())
    results.append(await test_supersede_memory())
    results.append(await test_capture_command())
    results.append(await test_get_memory_evolution())
    results.append(await test_generate_commands())

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✅ All tests passed!")
    else:
        print(f"❌ {total - passed} tests failed")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
