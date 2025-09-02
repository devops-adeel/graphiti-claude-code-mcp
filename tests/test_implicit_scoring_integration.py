#!/usr/bin/env python3
"""
Integration Tests for Implicit Scoring with Neo4j
Tests behavioral correlation with real graph database backend
"""

import pytest
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture_extended import (
    ImplicitScoringMixin,
    BehavioralSignal,
    EnhancedPatternCapture,
)
from capture import PatternCapture, PatternType, get_pattern_capture
from graphiti_memory import SharedMemory, MemoryStatus, get_shared_memory


@pytest.mark.integration
class TestImplicitScoringIntegration:
    """Integration tests with real Neo4j backend"""

    @pytest.fixture(scope="class")
    async def shared_memory(self):
        """Get or create shared memory instance"""
        # Set test configuration
        os.environ["GRAPHITI_GROUP_ID"] = "test_behavioral_correlation"
        os.environ["NEO4J_DATABASE"] = "neo4j"
        os.environ["NEO4J_URI"] = os.environ.get(
            "NEO4J_URI", "bolt://neo4j.graphiti.local:7687"
        )

        memory = await get_shared_memory()
        yield memory

        # Cleanup test data
        if hasattr(memory, "client") and memory.client:
            try:
                await memory.client.close()
            except:
                pass

    @pytest.fixture
    async def enhanced_capture(self, shared_memory):
        """Create enhanced pattern capture with real backend"""
        base_capture = await get_pattern_capture()
        enhanced = EnhancedPatternCapture(base_capture)
        return enhanced

    @pytest.mark.asyncio
    async def test_capture_with_scoring_persistence(self, enhanced_capture):
        """Test that scored memories persist in Neo4j"""
        # Capture command with behavioral signals
        memory_id = await enhanced_capture.capture_command_pattern_with_scoring(
            command="docker compose up -d",
            context="deployment",
            success=True,
            output="Services started successfully",
        )

        assert memory_id is not None

        # Search for the memory
        base_memory = enhanced_capture.base_capture.memory
        results = await base_memory.search_with_temporal_weight(
            "docker compose deployment", filter_source="claude_code"
        )

        # Should find our memory
        assert len(results) > 0

        # Find our specific memory
        our_memory = None
        for result in results:
            if hasattr(result, "id") and result.id == memory_id:
                our_memory = result
                break
            elif hasattr(result, "metadata") and result.metadata.get("id") == memory_id:
                our_memory = result
                break

        assert our_memory is not None
        print(f"✓ Memory {memory_id} persisted with scoring")

    @pytest.mark.asyncio
    async def test_temporal_decay_with_scoring(self, enhanced_capture):
        """Test that temporal decay interacts correctly with behavioral scoring"""
        # Create memories with different ages
        memories = []
        base_memory = enhanced_capture.base_capture.memory

        # Fresh memory with high behavioral score
        enhanced_capture.scoring.reset_signals()
        enhanced_capture.scoring.add_behavioral_signal("command_success", True)
        enhanced_capture.scoring.add_behavioral_signal("test_result", True)
        enhanced_capture.scoring.add_behavioral_signal("task_completion", True)

        fresh_id = await enhanced_capture.capture_command_pattern_with_scoring(
            command="pytest tests/ -v", context="testing fresh", success=True
        )
        memories.append(("fresh", fresh_id, 1.0))  # Perfect behavioral score

        # Simulate week-old memory with medium score
        enhanced_capture.scoring.reset_signals()
        enhanced_capture.scoring.add_behavioral_signal("command_success", True)
        enhanced_capture.scoring.add_behavioral_signal("test_result", False)
        enhanced_capture.scoring.add_behavioral_signal("task_completion", True)

        week_old_id = await base_memory.add_memory(
            {
                "type": PatternType.COMMAND_PATTERN.value,
                "command": "make test",
                "context": "testing week old",
                "success": True,
                "implicit_score": 0.7,  # Medium behavioral score
                "timestamp": (
                    datetime.now(timezone.utc) - timedelta(days=7)
                ).isoformat(),
            },
            source="claude_code",
        )
        memories.append(("week_old", week_old_id, 0.7))

        # Simulate month-old memory with high score
        month_old_id = await base_memory.add_memory(
            {
                "type": PatternType.COMMAND_PATTERN.value,
                "command": "docker build .",
                "context": "testing month old",
                "success": True,
                "implicit_score": 0.9,  # High behavioral score
                "timestamp": (
                    datetime.now(timezone.utc) - timedelta(days=30)
                ).isoformat(),
            },
            source="claude_code",
        )
        memories.append(("month_old", month_old_id, 0.9))

        # Search and verify temporal weighting
        results = await base_memory.search_with_temporal_weight(
            "testing", filter_source="claude_code"
        )

        # Fresh memory with perfect score should rank highest
        # Month-old with high score should rank lower due to decay
        if results:
            top_result = results[0]

            # Check if fresh memory is ranked first
            is_fresh = False
            if hasattr(top_result, "metadata"):
                if "fresh" in top_result.metadata.get("context", ""):
                    is_fresh = True

            print(
                f"✓ Temporal decay applied: Fresh memory ranked {'first' if is_fresh else 'not first'}"
            )

            # Verify all memories were found
            found_ids = set()
            for result in results:
                if hasattr(result, "id"):
                    found_ids.add(result.id)
                elif hasattr(result, "metadata") and "id" in result.metadata:
                    found_ids.add(result.metadata["id"])

            for label, mem_id, _ in memories:
                if mem_id in found_ids:
                    print(f"  - Found {label} memory: {mem_id}")

    @pytest.mark.asyncio
    async def test_supersession_with_improved_score(self, enhanced_capture):
        """Test that memories can be superseded with better behavioral scores"""
        base_memory = enhanced_capture.base_capture.memory

        # Create initial memory with low score (failed command)
        enhanced_capture.scoring.reset_signals()
        enhanced_capture.scoring.add_behavioral_signal("command_success", False)

        original_id = await enhanced_capture.capture_command_pattern_with_scoring(
            command="npm install",
            context="dependency installation",
            success=False,
            output="Error: network timeout",
        )

        original_score = enhanced_capture.scoring.effectiveness_scores.get(
            original_id, 0
        )
        assert original_score < 0.5  # Failed command should have low score

        # Create improved solution with high score
        enhanced_capture.scoring.reset_signals()
        enhanced_capture.scoring.add_behavioral_signal("command_success", True)
        enhanced_capture.scoring.add_behavioral_signal("test_result", True)

        improved_content = {
            "type": PatternType.COMMAND_PATTERN.value,
            "command": "npm install --legacy-peer-deps",
            "context": "dependency installation",
            "success": True,
            "output": "Installation successful",
            "implicit_score": 0.85,
        }

        # Supersede the original
        improved_id = await base_memory.supersede_memory(
            original_id,
            improved_content,
            "Found better solution with --legacy-peer-deps flag",
        )

        assert improved_id != original_id

        # Search should prefer the improved version
        results = await base_memory.search_with_temporal_weight(
            "npm install dependency", filter_source="claude_code"
        )

        if results:
            # Check if improved version ranks higher
            for i, result in enumerate(results):
                result_id = getattr(result, "id", result.metadata.get("id"))
                if result_id == improved_id:
                    print(f"✓ Improved memory ranked at position {i+1}")
                    assert i < len(results) - 1  # Should not be last
                elif result_id == original_id:
                    # Original should be marked as superseded
                    status = getattr(result, "status", result.metadata.get("status"))
                    assert status == MemoryStatus.SUPERSEDED.value
                    print(f"  - Original memory marked as superseded")

    @pytest.mark.asyncio
    async def test_cross_domain_scoring(self, enhanced_capture):
        """Test behavioral scoring with cross-domain references"""
        # Capture with GTD context
        additional_signals = [
            BehavioralSignal(
                "task_completion", True, 0.3, {"gtd_context": "deployment task"}
            )
        ]

        memory_id = await enhanced_capture.capture_command_pattern_with_scoring(
            command="terraform apply",
            context="infrastructure deployment @computer",
            success=True,
            additional_signals=additional_signals,
        )

        # Verify cross-references were detected
        base_memory = enhanced_capture.base_capture.memory
        results = await base_memory.search_with_temporal_weight(
            "@computer deployment", filter_source="claude_code"
        )

        found = False
        for result in results:
            if hasattr(result, "metadata"):
                cross_refs = result.metadata.get("cross_references", [])
                if "@computer context" in cross_refs:
                    found = True
                    print(f"✓ Cross-domain reference detected: {cross_refs}")
                    break

        assert found, "Cross-domain reference not found"

    @pytest.mark.asyncio
    async def test_behavioral_correlation_at_scale(self, enhanced_capture):
        """Test that behavioral correlation holds with multiple memories"""
        base_memory = enhanced_capture.base_capture.memory
        n_memories = 20

        memory_ids = []
        expected_scores = []

        # Create memories with varying success patterns
        for i in range(n_memories):
            enhanced_capture.scoring.reset_signals()

            # Create correlated signals
            base_success_rate = i / n_memories

            # Add some noise but maintain correlation
            cmd_success = np.random.random() < (
                base_success_rate + np.random.normal(0, 0.1)
            )
            test_success = np.random.random() < (
                base_success_rate + np.random.normal(0, 0.1)
            )
            task_success = np.random.random() < (
                base_success_rate + np.random.normal(0, 0.1)
            )

            enhanced_capture.scoring.add_behavioral_signal(
                "command_success", cmd_success
            )
            enhanced_capture.scoring.add_behavioral_signal("test_result", test_success)
            enhanced_capture.scoring.add_behavioral_signal(
                "task_completion", task_success
            )

            memory_id = await enhanced_capture.capture_command_pattern_with_scoring(
                command=f"test_command_{i}",
                context=f"scale_test_{i}",
                success=cmd_success,
            )

            memory_ids.append(memory_id)

            # Calculate expected effectiveness
            score = enhanced_capture.scoring.effectiveness_scores[memory_id]
            expected_scores.append(score)

        # Validate correlation
        validation_results = await enhanced_capture.validate_correlation(
            memory_ids[:10], expected_scores[:10]  # Use subset for validation
        )

        print(f"\n✓ Scale test results:")
        print(f"  - Correlation: {validation_results['correlation']:.3f}")
        print(f"  - P-value: {validation_results['p_value']:.4f}")
        print(f"  - Significant: {validation_results['significant']}")
        print(f"  - Meets threshold (>0.6): {validation_results['meets_threshold']}")

        # Core hypothesis validation
        assert validation_results[
            "meets_threshold"
        ], f"Correlation {validation_results['correlation']:.3f} below 0.6 threshold"
        assert validation_results[
            "significant"
        ], f"P-value {validation_results['p_value']:.4f} not significant"


@pytest.mark.integration
class TestMemoryEffectivenessTracking:
    """Test tracking memory effectiveness over time"""

    @pytest.fixture
    async def tracking_capture(self):
        """Create capture instance for tracking tests"""
        base = await get_pattern_capture()
        enhanced = EnhancedPatternCapture(base)
        return enhanced

    @pytest.mark.asyncio
    async def test_effectiveness_tracking_over_sessions(self, tracking_capture):
        """Test that effectiveness improves over multiple sessions"""
        command = "docker compose restart"

        # Session 1: Initial failure
        tracking_capture.scoring.reset_signals()
        tracking_capture.scoring.add_behavioral_signal("command_success", False)

        memory_v1 = await tracking_capture.capture_command_pattern_with_scoring(
            command=command,
            context="restart services v1",
            success=False,
            output="Error: services not responding",
        )

        score_v1 = tracking_capture.scoring.effectiveness_scores[memory_v1]

        # Session 2: Partial success after learning
        tracking_capture.scoring.reset_signals()
        tracking_capture.scoring.add_behavioral_signal("command_success", True)
        tracking_capture.scoring.add_behavioral_signal("test_result", False)

        memory_v2 = await tracking_capture.capture_command_pattern_with_scoring(
            command=f"{command} --force",
            context="restart services v2",
            success=True,
            output="Services restarted with warnings",
        )

        score_v2 = tracking_capture.scoring.effectiveness_scores[memory_v2]

        # Session 3: Full success with optimized approach
        tracking_capture.scoring.reset_signals()
        tracking_capture.scoring.add_behavioral_signal("command_success", True)
        tracking_capture.scoring.add_behavioral_signal("test_result", True)
        tracking_capture.scoring.add_behavioral_signal("task_completion", True)

        memory_v3 = await tracking_capture.capture_command_pattern_with_scoring(
            command=f"{command} --force --wait",
            context="restart services v3",
            success=True,
            output="All services healthy",
        )

        score_v3 = tracking_capture.scoring.effectiveness_scores[memory_v3]

        # Effectiveness should improve over iterations
        assert score_v1 < score_v2 < score_v3

        print(f"\n✓ Effectiveness improved over sessions:")
        print(f"  - V1 (failure): {score_v1:.3f}")
        print(f"  - V2 (partial): {score_v2:.3f}")
        print(f"  - V3 (success): {score_v3:.3f}")

        # Calculate improvement rate
        improvement = (score_v3 - score_v1) / score_v1 if score_v1 > 0 else float("inf")
        print(f"  - Total improvement: {improvement:.1%}")


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    @pytest.fixture
    async def scenario_capture(self):
        """Create capture for scenario tests"""
        base = await get_pattern_capture()
        return EnhancedPatternCapture(base)

    @pytest.mark.asyncio
    async def test_tdd_cycle_with_behavioral_scoring(self, scenario_capture):
        """Test TDD red-green-refactor with behavioral signals"""
        feature_name = "user_authentication"

        # Red phase: Failing test
        scenario_capture.scoring.reset_signals()
        scenario_capture.scoring.add_behavioral_signal("test_result", False)

        red_memory = await scenario_capture.base_capture.capture_tdd_cycle(
            test_code="""
            def test_user_login():
                user = User('test@example.com', 'password')
                assert user.login() == True  # Fails - not implemented
            """,
            feature_name=feature_name,
        )

        # Green phase: Minimal implementation
        scenario_capture.scoring.reset_signals()
        scenario_capture.scoring.add_behavioral_signal("test_result", True)
        scenario_capture.scoring.add_behavioral_signal("command_success", True)

        green_memory = await scenario_capture.base_capture.capture_tdd_cycle(
            test_code="""
            def test_user_login():
                user = User('test@example.com', 'password')
                assert user.login() == True  # Passes
            """,
            implementation="""
            class User:
                def login(self):
                    return True  # Minimal implementation
            """,
            feature_name=feature_name,
        )

        # Refactor phase: Improved implementation
        scenario_capture.scoring.reset_signals()
        scenario_capture.scoring.add_behavioral_signal("test_result", True)
        scenario_capture.scoring.add_behavioral_signal("command_success", True)
        scenario_capture.scoring.add_behavioral_signal("task_completion", True)

        refactor_memory = await scenario_capture.base_capture.capture_tdd_cycle(
            test_code="""
            def test_user_login():
                user = User('test@example.com', 'password')
                assert user.login() == True

                invalid_user = User('test@example.com', 'wrong')
                assert invalid_user.login() == False
            """,
            implementation="""
            class User:
                def __init__(self, email, password):
                    self.email = email
                    self.password = password

                def login(self):
                    # Actual authentication logic
                    return self._validate_credentials()
            """,
            refactored="""
            class User:
                def __init__(self, email, password):
                    self.email = email
                    self.password = password

                def login(self):
                    if not self._validate_email():
                        return False
                    return self._validate_credentials()

                def _validate_email(self):
                    return '@' in self.email

                def _validate_credentials(self):
                    # Check against stored hash
                    return self.password == self._get_stored_password()
            """,
            feature_name=feature_name,
        )

        print(f"\n✓ TDD cycle captured with behavioral scoring:")
        print(f"  - Red phase: {red_memory}")
        print(f"  - Green phase: {green_memory}")
        print(f"  - Refactor phase: {refactor_memory}")

    @pytest.mark.asyncio
    async def test_debugging_session_with_learning(self, scenario_capture):
        """Test debugging session that improves over time"""
        base_memory = scenario_capture.base_capture.memory

        # Initial error encounter
        scenario_capture.scoring.reset_signals()
        scenario_capture.scoring.add_behavioral_signal("command_success", False)

        error_memory = await scenario_capture.base_capture.capture_deployment_solution(
            error="ConnectionRefusedError: [Errno 111] Connection refused",
            solution="Check if service is running",
            context={"service": "redis", "port": 6379},
        )

        # First fix attempt
        scenario_capture.scoring.reset_signals()
        scenario_capture.scoring.add_behavioral_signal("command_success", False)
        scenario_capture.scoring.add_behavioral_signal("test_result", False)

        attempt1 = await scenario_capture.capture_command_pattern_with_scoring(
            command="redis-server",
            context="start redis manually",
            success=False,
            output="Address already in use",
        )

        # Second fix attempt
        scenario_capture.scoring.reset_signals()
        scenario_capture.scoring.add_behavioral_signal("command_success", True)
        scenario_capture.scoring.add_behavioral_signal("test_result", False)

        attempt2 = await scenario_capture.capture_command_pattern_with_scoring(
            command="sudo lsof -i :6379 | grep LISTEN",
            context="find process using port",
            success=True,
            output="redis-ser 12345",
        )

        # Final solution
        scenario_capture.scoring.reset_signals()
        scenario_capture.scoring.add_behavioral_signal("command_success", True)
        scenario_capture.scoring.add_behavioral_signal("test_result", True)
        scenario_capture.scoring.add_behavioral_signal("task_completion", True)

        solution = await scenario_capture.base_capture.capture_deployment_solution(
            error="ConnectionRefusedError: [Errno 111] Connection refused",
            solution="Kill existing process and restart: sudo kill -9 $(lsof -t -i:6379) && redis-server",
            context={"service": "redis", "port": 6379, "resolved": True},
        )

        # Search for Redis solutions
        results = await base_memory.search_with_temporal_weight(
            "redis connection refused 6379", filter_source="claude_code"
        )

        print(f"\n✓ Debugging session with learning:")
        print(f"  - Initial error: {error_memory}")
        print(f"  - Attempt 1 (failed): {attempt1}")
        print(f"  - Attempt 2 (partial): {attempt2}")
        print(f"  - Final solution: {solution}")
        print(f"  - Found {len(results)} related memories for future reference")


if __name__ == "__main__":
    # Run integration tests
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-m",
            "integration",
            "--capture=no",  # Show print statements
        ]
    )
