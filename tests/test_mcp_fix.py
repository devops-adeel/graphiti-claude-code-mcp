#!/usr/bin/env python3
"""
Test script to verify the MCP capture_solution fix
Tests that complex JSON context objects can be stored without RediSearch errors
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from capture import PatternCapture


async def test_capture_solution():
    """Test that capture_solution works with complex JSON context"""

    capture = PatternCapture()
    await capture.initialize()

    # Test case 1: Original problematic context
    test_context_1 = {
        "test_type": "connection_test",
        "timestamp": "2025-01-18",
        "purpose": "verify_mcp_write_access",
    }

    print("Testing with original context that caused error...")
    try:
        memory_id = await capture.capture_deployment_solution(
            error="Testing MCP write connection",
            solution="Successfully connected to Graphiti memory MCP tools",
            context=test_context_1,
        )
        print(f"✅ Test 1 passed! Memory ID: {memory_id}")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False

    # Test case 2: Deeply nested context
    test_context_2 = {
        "level1": {
            "level2": {
                "level3": {
                    "data": "nested_value",
                    "array": [1, 2, 3],
                    "special_chars": "test:value@symbol",
                }
            }
        },
        "timestamp": datetime.now().isoformat(),
    }

    print("\nTesting with deeply nested context...")
    try:
        memory_id = await capture.capture_deployment_solution(
            error="Complex nested structure test",
            solution="Serialization handles nested structures",
            context=test_context_2,
        )
        print(f"✅ Test 2 passed! Memory ID: {memory_id}")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False

    # Test case 3: Context with special characters (but not @ in keys)
    test_context_3 = {
        "computer": "task",
        "test-type": "special_chars",
        "url": "https://example.com:8080/path",
        "json": '{"nested": "json_string"}',
    }

    print("\nTesting with special characters in context...")
    try:
        memory_id = await capture.capture_deployment_solution(
            error="Special characters test",
            solution="Handles special characters correctly",
            context=test_context_3,
        )
        print(f"✅ Test 3 passed! Memory ID: {memory_id}")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        return False

    # Test case 4: Project structure capture
    test_structure = {
        "src": {
            "components": ["Header.tsx", "Footer.tsx"],
            "utils": ["api.ts", "helpers.ts"],
        },
        "tests": ["unit", "integration"],
        "docs": "README.md",
    }

    print("\nTesting project structure capture...")
    try:
        memory_id = await capture.capture_project_structure(
            structure=test_structure, description="Test project structure"
        )
        print(f"✅ Test 4 passed! Memory ID: {memory_id}")
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        return False

    print("\n✅ All tests passed! The fix is working correctly.")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_capture_solution())
    if not success:
        print("\n⚠️ Some tests failed. Please check the error messages above.")
        exit(1)
