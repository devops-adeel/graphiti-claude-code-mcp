#!/usr/bin/env python3
"""
Test script to verify MCP server doesn't analyze its own traces
This prevents observability loops while maintaining full monitoring
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langfuse_integration.langfuse_analyzer import get_langfuse_analyzer
from langfuse import Langfuse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_loop_prevention():
    """
    Test that MCP analyzer ignores its own traces
    """
    print("\n🔍 Testing Observability Loop Prevention")
    print("=" * 60)

    # Initialize analyzer
    analyzer = await get_langfuse_analyzer()
    await analyzer.initialize()

    # Step 1: Create a test trace with MCP tags (simulating MCP operation)
    print("\n1️⃣ Creating MCP-tagged test trace...")

    # Initialize Langfuse v3 SDK
    from langfuse import Langfuse, get_client

    Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host="http://langfuse.local",
    )
    langfuse = get_client()

    # Create a trace that should be filtered out (v3 pattern)
    mcp_trace_id = None
    with langfuse.start_as_current_span(
        name="mcp_tool_test_loop_prevention"
    ) as mcp_span:
        mcp_span.update_trace(
            tags=["mcp-internal", "mcp-analyzer", "test"],
            metadata={
                "source": "mcp-server",
                "component": "test-script",
                "purpose": "verify-loop-prevention",
            },
        )

        # Add some operations to the trace
        with langfuse.start_as_current_span(
            name="test_operation", metadata={"test": True}
        ):
            pass  # Span auto-closes

        mcp_span.update_trace(output="Test trace for loop prevention")
        mcp_trace_id = mcp_span.trace_id

    # Force flush to ensure trace is sent
    langfuse.flush()
    print(f"   Created trace ID: {mcp_trace_id}")
    print("   Tags: ['mcp-internal', 'mcp-analyzer', 'test']")

    # Step 2: Create a normal application trace (should NOT be filtered)
    print("\n2️⃣ Creating normal application trace...")
    app_trace_id = None
    with langfuse.start_as_current_span(name="application_operation") as app_span:
        app_span.update_trace(
            tags=["production", "api-call"],
            metadata={"source": "application", "endpoint": "/api/test"},
        )
        app_span.update_trace(output="Normal application trace")
        app_trace_id = app_span.trace_id

    langfuse.flush()
    print(f"   Created trace ID: {app_trace_id}")
    print("   Tags: ['production', 'api-call']")

    # Wait a moment for traces to be indexed
    print("\n⏳ Waiting 3 seconds for traces to be indexed...")
    await asyncio.sleep(3)

    # Step 3: Analyze recent traces
    print("\n3️⃣ Analyzing recent traces (last 1 minute)...")
    result = await analyzer.analyze_recent_traces(hours_back=0.0167)  # 1 minute

    # Step 4: Verify results
    print("\n4️⃣ Verifying results...")

    # Check if MCP trace was filtered out
    mcp_trace_found = False
    app_trace_found = False

    for trace in result.get("traces", []):
        if trace.get("trace_id") == mcp_trace_id:
            mcp_trace_found = True
            print(f"   ❌ MCP trace was NOT filtered: {trace.get('trace_id')}")
        if trace.get("trace_id") == app_trace_id:
            app_trace_found = True
            print(f"   ✅ Application trace was found: {trace.get('trace_id')}")

    # Print summary
    print("\n📊 Test Results:")
    print("-" * 40)
    print(f"   Total traces analyzed: {len(result.get('traces', []))}")
    print(f"   MCP trace filtered out: {'✅ Yes' if not mcp_trace_found else '❌ No'}")
    print(f"   App trace included: {'✅ Yes' if app_trace_found else '❌ No'}")

    # Overall test result
    print("\n🎯 Loop Prevention Test:")
    if not mcp_trace_found:
        print("   ✅ SUCCESS: MCP traces are properly filtered")
        print("   The analyzer correctly ignores its own traces")
    else:
        print("   ❌ FAILURE: MCP traces were not filtered")
        print("   This could lead to observability loops!")

    # Additional verification with direct API call
    print("\n5️⃣ Direct API verification...")
    from langfuse.client import FernLangfuse

    # Use direct API to fetch all recent traces
    direct_client = FernLangfuse(
        x_langfuse_sdk_name="test-verification",
        x_langfuse_sdk_version="1.0.0",
        x_langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        username=os.getenv("LANGFUSE_PUBLIC_KEY"),
        password=os.getenv("LANGFUSE_SECRET_KEY"),
        base_url=os.getenv("LANGFUSE_HOST"),
    )

    from_timestamp = datetime.now() - timedelta(minutes=1)
    all_traces = direct_client.trace.list(from_timestamp=from_timestamp, limit=10).data

    print(f"   Total traces in Langfuse: {len(all_traces)}")

    # Count MCP vs non-MCP traces
    mcp_count = 0
    for trace in all_traces:
        if hasattr(trace, "tags") and trace.tags:
            if any(tag in ["mcp-internal", "mcp-analyzer"] for tag in trace.tags):
                mcp_count += 1

    print(f"   MCP-tagged traces: {mcp_count}")
    print(f"   Other traces: {len(all_traces) - mcp_count}")

    return not mcp_trace_found


async def test_metadata_filtering():
    """
    Test that metadata-based filtering also works
    """
    print("\n\n🔍 Testing Metadata-Based Filtering")
    print("=" * 60)

    analyzer = await get_langfuse_analyzer()

    # Initialize Langfuse v3 SDK
    from langfuse import Langfuse, get_client

    Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host="http://langfuse.local",
    )
    langfuse = get_client()

    # Create trace with metadata but no tags
    print("\n1️⃣ Creating trace with MCP metadata (no tags)...")
    metadata_trace_id = None
    with langfuse.start_as_current_span(name="metadata_test_trace") as metadata_span:
        metadata_span.update_trace(
            metadata={
                "source": "mcp-server",
                "component": "langfuse-analyzer",
                "version": "1.0.0",
            }
        )
        metadata_trace_id = metadata_span.trace_id

    langfuse.flush()
    print(f"   Created trace ID: {metadata_trace_id}")

    await asyncio.sleep(3)

    print("\n2️⃣ Analyzing traces...")
    result = await analyzer.analyze_recent_traces(hours_back=0.0167)

    metadata_trace_found = False
    for trace in result.get("traces", []):
        if trace.get("trace_id") == metadata_trace.id:
            metadata_trace_found = True

    print("\n📊 Metadata Filtering Result:")
    if not metadata_trace_found:
        print("   ✅ SUCCESS: Metadata-based filtering works")
    else:
        print("   ❌ FAILURE: Metadata filtering not working")

    return not metadata_trace_found


async def main():
    """
    Run all loop prevention tests
    """
    print("🚀 MCP Observability Loop Prevention Test Suite")
    print("=" * 60)
    print("This test verifies that the MCP server can be fully monitored")
    print("by Langfuse and Grafana while preventing analysis loops.\n")

    # Check environment
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        print("❌ Error: LANGFUSE_PUBLIC_KEY not set")
        print("   Please configure your environment variables")
        return

    try:
        # Run tests
        test1_passed = await test_loop_prevention()
        test2_passed = await test_metadata_filtering()

        # Final summary
        print("\n\n" + "=" * 60)
        print("📋 FINAL TEST SUMMARY")
        print("=" * 60)
        print(f"   Tag-based filtering: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"   Metadata filtering: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

        if test1_passed and test2_passed:
            print("\n🎉 All tests passed! Loop prevention is working correctly.")
            print("   The MCP server is fully observable without creating loops.")
        else:
            print("\n⚠️ Some tests failed. Please review the configuration.")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
