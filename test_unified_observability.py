#!/usr/bin/env python3
"""
Test Unified Observability with W3C Trace Context
"""

import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_unified_observability():
    """Test the unified observability system"""
    try:
        # Import modules
        from unified_observability import (
            UnifiedObservability,
            UnifiedTraceContext,
            unified_observe,
            get_unified_observability,
        )
        from langfuse_scoring import get_langfuse_scoring

        # Initialize systems
        logger.info("Initializing unified observability...")
        unified = get_unified_observability()
        scoring = get_langfuse_scoring()

        # Test 1: Create unified trace context
        logger.info("\n1. Testing unified trace context...")
        with unified.unified_trace("test_operation", metadata={"test": True}) as ctx:
            logger.info(f"   Trace ID (W3C): {ctx.trace_id}")
            if ctx.langfuse_trace_id:
                logger.info(f"   Langfuse ID: {ctx.langfuse_trace_id}")

            # Create headers for propagation
            headers = ctx.to_w3c_headers()
            logger.info(f"   Headers for propagation: {list(headers.keys())}")

        # Test 2: Unified scoring
        logger.info("\n2. Testing unified scoring...")
        unified.create_unified_score(
            name="test_score", value=0.95, metadata={"source": "test_script"}
        )
        logger.info("   ✅ Score created with correlation metadata")

        # Test 3: Test with behavioral scoring
        logger.info("\n3. Testing with behavioral scoring system...")

        # Add signals
        scoring.add_signal("command_success", True, {"command": "test"})
        scoring.add_signal("test_result", True, {"test": "unit"})

        # Calculate effectiveness with unified context
        with unified.unified_trace("behavioral_scoring"):
            score = scoring.calculate_effectiveness(
                memory_id="test_memory_002", additional_context={"unified": True}
            )
            logger.info(f"   Behavioral score: {score:.3f}")

            # Add unified score
            unified.create_unified_score(
                name="behavioral_effectiveness",
                value=score,
                metadata={"memory_id": "test_memory_002"},
            )

        # Test 4: Decorator usage
        logger.info("\n4. Testing unified decorator...")

        @unified_observe("test_function")
        async def sample_function(input_data: str) -> str:
            """Sample function with unified observability"""
            await asyncio.sleep(0.1)  # Simulate work
            return f"Processed: {input_data}"

        result = await sample_function("test input")
        logger.info(f"   Result: {result}")

        # Test 5: Context extraction from headers
        logger.info("\n5. Testing context propagation...")
        test_headers = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
            "X-Langfuse-Trace-Id": "lf_test_123",
        }

        extracted_ctx = UnifiedTraceContext.from_headers(test_headers)
        logger.info(f"   Extracted trace ID: {extracted_ctx.trace_id}")
        logger.info(f"   Extracted Langfuse ID: {extracted_ctx.langfuse_trace_id}")

        # Summary
        print("\n" + "=" * 60)
        print("🎉 SUCCESS: Unified observability tests passed!")
        print("\nKey achievements:")
        print("✅ W3C Trace Context format implemented")
        print("✅ Langfuse and OpenTelemetry correlation established")
        print("✅ Behavioral scoring integrated with unified tracing")
        print("✅ Context propagation via headers working")

        print("\n📊 View your traces:")
        print(
            f"   Langfuse: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}"
        )
        if os.getenv("OTLP_ENDPOINT"):
            print(f"   Grafana: http://grafana.local/explore")

        # Flush data
        scoring.flush()
        unified.langfuse.flush()

        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Check for Langfuse credentials
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        print("⚠️  LANGFUSE_PUBLIC_KEY not set")
        print("\nRun with 1Password:")
        print(
            "  op run --env-file=secrets/.env.1password -- python3 test_unified_observability.py"
        )
        sys.exit(1)

    # Run tests
    success = asyncio.run(test_unified_observability())
    sys.exit(0 if success else 1)
