#!/usr/bin/env python3
"""
Test script for Langfuse integration with graphiti-claude-code-mcp
Verifies that all Langfuse tools and resources are working correctly
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from langfuse_integration.langfuse_analyzer import get_langfuse_analyzer
from langfuse_integration.langfuse_patterns import PatternDetector
from langfuse_integration.langfuse_models import (
    LangfuseTrace,
    LangfuseObservation,
    DetectedPattern,
    AnalysisResult,
    ObservationType,
)


async def test_analyzer_creation():
    """Test that we can create the Langfuse analyzer"""
    print("\n=== Testing Analyzer Creation ===")
    try:
        analyzer = await get_langfuse_analyzer()
        print("✓ Langfuse analyzer created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create analyzer: {e}")
        return False


async def test_pattern_detector():
    """Test pattern detection and signature generation"""
    print("\n=== Testing Pattern Detector ===")
    try:
        detector = PatternDetector()

        # Test signature generation
        signatures = [
            detector.generate_signature(
                "state_loss", from_phase="planning", to_phase="review"
            ),
            detector.generate_signature("interrupt", tool="check_in"),
            detector.generate_signature("error", observation="test_runner"),
        ]

        print(f"✓ Generated signatures: {signatures}")

        # Test confidence calculation
        from langfuse_integration.langfuse_patterns import PatternType

        confidence = detector.calculate_confidence(
            PatternType.STATE_LOSS, {"state_changes": 5, "continuity_failures": 2}
        )
        print(f"✓ Calculated confidence: {confidence:.2f}")

        return True
    except Exception as e:
        print(f"✗ Pattern detector failed: {e}")
        return False


async def test_models():
    """Test Pydantic models for data validation"""
    print("\n=== Testing Data Models ===")
    try:
        # Create a sample observation
        obs = LangfuseObservation(
            id="test-obs-1",
            type=ObservationType.SPAN,
            trace_id="test-trace-1",
            name="test_observation",
            start_time=datetime.now(),
            metadata={"test": "data"},
        )
        print(f"✓ Created observation: {obs.id}")

        # Create a sample trace
        trace = LangfuseTrace(
            id="test-trace-1",
            timestamp=datetime.now(),
            observations=[obs],
            tags=["test", "integration"],
        )
        print(f"✓ Created trace with {trace.observation_count} observations")

        # Create a detected pattern
        pattern = DetectedPattern(
            signature="test_pattern_signature",
            type="test",
            confidence=0.85,
            trace_id="test-trace-1",
        )
        print(
            f"✓ Created pattern with confidence level: {pattern.confidence_level.value}"
        )

        # Create analysis result
        result = AnalysisResult(status="success", traces_analyzed=1, hours_analyzed=1)
        result.add_trace(trace)
        result.add_pattern(pattern)
        print(
            f"✓ Created analysis result with {result.unique_patterns} unique patterns"
        )

        return True
    except Exception as e:
        print(f"✗ Model validation failed: {e}")
        return False


async def test_recent_traces_analysis():
    """Test analyzing recent traces (may not have data)"""
    print("\n=== Testing Recent Traces Analysis ===")
    try:
        analyzer = await get_langfuse_analyzer()
        result = await analyzer.analyze_recent_traces(hours_back=1)

        print(f"✓ Analysis completed")
        print(f"  - Traces analyzed: {result.get('traces_analyzed', 0)}")
        print(f"  - Errors found: {len(result.get('errors', []))}")
        print(f"  - Patterns detected: {len(result.get('patterns', []))}")

        if result.get("traces_analyzed", 0) == 0:
            print(
                "  ℹ No traces found in the last hour (this is normal if no activity)"
            )

        return True
    except Exception as e:
        print(f"✗ Trace analysis failed: {e}")
        print(f"  Hint: Check if Langfuse credentials are valid in ~/.env")
        return False


async def test_phase_transitions():
    """Test phase transition analysis"""
    print("\n=== Testing Phase Transition Analysis ===")
    try:
        analyzer = await get_langfuse_analyzer()
        # Create a mock trace ID for testing
        result = await analyzer.analyze_phase_transitions("test-trace-id")

        print(f"✓ Phase transition analysis completed")
        print(f"  - Transitions found: {len(result.get('transitions', []))}")

        if len(result.get("transitions", [])) == 0:
            print("  ℹ No transitions found (expected for test trace ID)")

        return True
    except Exception as e:
        print(f"✗ Phase transition analysis failed: {e}")
        return False


async def test_memory_integration():
    """Test that patterns can be stored in Graphiti memory"""
    print("\n=== Testing Memory Integration ===")
    try:
        from graphiti_memory import get_shared_memory

        memory = await get_shared_memory()
        print(f"✓ Connected to Graphiti memory: {memory.group_id}")

        # Search for any existing Langfuse patterns
        patterns = await memory.search_with_temporal_weight(
            "langfuse pattern", filter_source="claude_code"
        )
        print(f"✓ Found {len(patterns)} existing Langfuse patterns in memory")

        return True
    except Exception as e:
        print(f"✗ Memory integration failed: {e}")
        print(f"  Hint: Check if FalkorDB is running and accessible")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Langfuse Integration Test Suite")
    print("=" * 60)

    tests = [
        test_analyzer_creation(),
        test_pattern_detector(),
        test_models(),
        test_recent_traces_analysis(),
        test_phase_transitions(),
        test_memory_integration(),
    ]

    results = await asyncio.gather(*tests, return_exceptions=True)

    # Count successes
    successes = sum(1 for r in results if r is True)
    failures = len(results) - successes

    print("\n" + "=" * 60)
    print(f"Test Results: {successes}/{len(results)} passed")

    if failures > 0:
        print(f"⚠️  {failures} test(s) failed")
        print("\nTroubleshooting:")
        print("1. Ensure Langfuse credentials are in ~/.env")
        print("2. Verify FalkorDB is running (docker ps | grep falkordb)")
        print("3. Check that analyze_langfuse_traces.py is accessible")
        return 1
    else:
        print("✅ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
