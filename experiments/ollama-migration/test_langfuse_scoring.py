#!/usr/bin/env python3
"""
Test Langfuse scoring system with 1Password credentials
"""

import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_langfuse_scoring():
    """Test the Langfuse scoring system"""
    try:
        # Import the scoring system
        from langfuse_scoring import LangfuseScoringSystem, get_langfuse_scoring

        # Initialize the scoring system (should use env vars from 1Password)
        logger.info("Initializing LangfuseScoringSystem...")
        scoring = get_langfuse_scoring()

        # Add some test signals
        logger.info("Adding behavioral signals...")
        scoring.add_signal("command_success", True, {"command": "docker ps"})
        scoring.add_signal("test_result", True, {"test": "unit_test_1"})
        scoring.add_signal("task_completion", False, {"task": "deploy_service"})

        # Calculate effectiveness score
        logger.info("Calculating effectiveness score...")
        score = scoring.calculate_effectiveness(
            memory_id="test_memory_001", additional_context={"source": "test_script"}
        )

        logger.info(f"✅ Effectiveness score calculated: {score:.3f}")

        # Test command scoring
        logger.info("Testing command scoring...")
        cmd_score = scoring.score_command(
            command="make test", success=True, output="All tests passed"
        )
        logger.info(f"✅ Command score: {cmd_score:.3f}")

        # Test test result scoring
        logger.info("Testing test result scoring...")
        test_score = scoring.score_test(
            test_name="test_behavioral_correlation", passed=True, assertions=15
        )
        logger.info(f"✅ Test score: {test_score:.3f}")

        # Test task completion scoring
        logger.info("Testing task completion scoring...")
        task_score = scoring.score_task(
            task_description="Implement Langfuse integration",
            completed=True,
            gtd_link="gtd://task/123",
        )
        logger.info(f"✅ Task score: {task_score:.3f}")

        # Test temporal decay
        logger.info("Testing temporal decay...")
        fresh_score = scoring.apply_temporal_decay(0.8, 0)
        week_score = scoring.apply_temporal_decay(0.8, 7)
        month_score = scoring.apply_temporal_decay(0.8, 30)

        logger.info(
            f"✅ Temporal decay - Fresh: {fresh_score:.3f}, Week: {week_score:.3f}, Month: {month_score:.3f}"
        )

        # Get scoring report
        report = scoring.get_scoring_report()
        logger.info(f"✅ Scoring report: {report}")

        print("\n🎉 SUCCESS: All Langfuse scoring tests passed!")
        print("📊 Data has been sent to Langfuse for observability")
        print(f"🔍 Check your Langfuse dashboard at: {os.getenv('LANGFUSE_HOST')}")

        return True

    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        print("\nTo run this test with 1Password:")
        print(
            "  op run --env-file=secrets/.env.1password -- python3 test_langfuse_scoring.py"
        )
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Check if Langfuse credentials are available
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        print("⚠️  LANGFUSE_PUBLIC_KEY not set")
        print("\nRun with 1Password:")
        print(
            "  op run --env-file=secrets/.env.1password -- python3 test_langfuse_scoring.py"
        )
        print("\nOr set environment variables directly:")
        print("  export LANGFUSE_PUBLIC_KEY=your_key")
        print("  export LANGFUSE_SECRET_KEY=your_secret")
        sys.exit(1)

    success = test_langfuse_scoring()
    sys.exit(0 if success else 1)
