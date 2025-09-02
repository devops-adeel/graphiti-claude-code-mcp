#!/usr/bin/env python3
"""
Unit Tests for Implicit Scoring with Behavioral Correlation
Validates that behavioral signals correlate with memory effectiveness
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture_extended import (
    ImplicitScoringMixin,
    BehavioralSignal,
    EnhancedPatternCapture,
)
from capture import PatternCapture, PatternType


class TestImplicitScoringMixin:
    """Test the ImplicitScoringMixin functionality"""

    def setup_method(self):
        """Set up test instance"""
        self.scorer = ImplicitScoringMixin()

    def test_add_behavioral_signal(self):
        """Test adding behavioral signals"""
        # Add command success signal
        self.scorer.add_behavioral_signal(
            signal_type="command_success",
            value=True,
            context={"command": "docker compose up"},
        )

        assert len(self.scorer.behavioral_signals) == 1
        signal = self.scorer.behavioral_signals[0]
        assert signal.signal_type == "command_success"
        assert signal.value == True
        assert signal.weight == 0.4

    def test_calculate_effectiveness_score_no_signals(self):
        """Test scoring with no signals returns neutral score"""
        score = self.scorer.calculate_effectiveness_score("test_memory_id")
        assert score == 0.5  # Neutral score

    def test_calculate_effectiveness_score_all_success(self):
        """Test scoring with all successful signals"""
        # Add successful signals of each type
        self.scorer.add_behavioral_signal("command_success", True)
        self.scorer.add_behavioral_signal("test_result", True)
        self.scorer.add_behavioral_signal("task_completion", True)

        score = self.scorer.calculate_effectiveness_score("test_memory_id")
        assert score == 1.0  # Perfect score

    def test_calculate_effectiveness_score_all_failure(self):
        """Test scoring with all failed signals"""
        # Add failed signals of each type
        self.scorer.add_behavioral_signal("command_success", False)
        self.scorer.add_behavioral_signal("test_result", False)
        self.scorer.add_behavioral_signal("task_completion", False)

        score = self.scorer.calculate_effectiveness_score("test_memory_id")
        assert score == 0.0  # Worst score

    def test_calculate_effectiveness_score_mixed_signals(self):
        """Test scoring with mixed success/failure signals"""
        # Command success (40% weight) - success
        self.scorer.add_behavioral_signal("command_success", True)
        # Test result (30% weight) - failure
        self.scorer.add_behavioral_signal("test_result", False)
        # Task completion (30% weight) - success
        self.scorer.add_behavioral_signal("task_completion", True)

        score = self.scorer.calculate_effectiveness_score("test_memory_id")
        # Expected: 0.4 * 1.0 + 0.3 * 0.0 + 0.3 * 1.0 = 0.7
        assert pytest.approx(score, rel=1e-3) == 0.7

    def test_calculate_effectiveness_score_multiple_same_type(self):
        """Test scoring with multiple signals of same type"""
        # Add 3 command signals: 2 success, 1 failure
        self.scorer.add_behavioral_signal("command_success", True)
        self.scorer.add_behavioral_signal("command_success", True)
        self.scorer.add_behavioral_signal("command_success", False)

        score = self.scorer.calculate_effectiveness_score("test_memory_id")
        # Success rate: 2/3 = 0.667, weight: 0.4, normalized: 0.667
        assert pytest.approx(score, rel=1e-2) == 0.667

    def test_score_bounds_clamping(self):
        """Test that scores are clamped to 0.0-1.0 bounds"""
        # This should naturally stay within bounds, but test the clamping logic
        score = self.scorer.calculate_effectiveness_score("test_memory_id")
        assert 0.0 <= score <= 1.0

        # Add many successful signals
        for _ in range(10):
            self.scorer.add_behavioral_signal("command_success", True)

        score = self.scorer.calculate_effectiveness_score("test_memory_id_2")
        assert score == 1.0  # Should not exceed 1.0

    def test_correlate_signals_with_effectiveness(self):
        """Test correlation calculation between signals and effectiveness"""
        # Create test signals
        signals = [
            BehavioralSignal("command_success", True, 0.4),
            BehavioralSignal("command_success", True, 0.4),
            BehavioralSignal("command_success", False, 0.4),
            BehavioralSignal("test_result", True, 0.3),
            BehavioralSignal("test_result", False, 0.3),
        ]

        # Create corresponding effectiveness (correlated with success)
        effectiveness = [0.9, 0.85, 0.3, 0.8, 0.2]

        correlation, p_value = self.scorer.correlate_signals_with_effectiveness(
            signals, effectiveness
        )

        # Should have positive correlation
        assert correlation > 0.6
        assert p_value < 0.05  # Statistically significant

    def test_adjust_score_for_temporal_decay(self):
        """Test temporal decay adjustment"""
        base_score = 0.8

        # Fresh memory (0 days old)
        adjusted = self.scorer.adjust_score_for_temporal_decay(base_score, 0)
        # 0.8 * 0.6 + 1.0 * 0.4 = 0.48 + 0.4 = 0.88
        assert pytest.approx(adjusted, rel=1e-2) == 0.88

        # Week-old memory
        adjusted = self.scorer.adjust_score_for_temporal_decay(base_score, 7)
        # 0.8 * 0.6 + (0.97^7) * 0.4
        expected = 0.8 * 0.6 + (0.97**7) * 0.4
        assert pytest.approx(adjusted, rel=1e-2) == expected

        # Month-old memory
        adjusted = self.scorer.adjust_score_for_temporal_decay(base_score, 30)
        # Should be significantly lower
        assert adjusted < 0.7

        # Very old memory
        adjusted = self.scorer.adjust_score_for_temporal_decay(base_score, 365)
        # Should be very low but not negative
        assert 0.0 <= adjusted <= 0.5

    def test_get_scoring_metadata(self):
        """Test metadata generation for storage"""
        # Add some signals
        self.scorer.add_behavioral_signal("command_success", True)
        self.scorer.add_behavioral_signal("command_success", False)
        self.scorer.add_behavioral_signal("test_result", True)

        # Calculate score
        memory_id = "test_memory_123"
        self.scorer.calculate_effectiveness_score(memory_id)

        # Get metadata
        metadata = self.scorer.get_scoring_metadata(memory_id)

        assert "implicit_score" in metadata
        assert "signal_stats" in metadata
        assert "scoring_timestamp" in metadata
        assert "scoring_version" in metadata
        assert metadata["enhancement_type"] == "behavioral_correlation"

        # Check signal stats
        assert "command_success" in metadata["signal_stats"]
        assert metadata["signal_stats"]["command_success"]["count"] == 2
        assert metadata["signal_stats"]["command_success"]["success_rate"] == 0.5

    def test_reset_signals(self):
        """Test signal reset functionality"""
        # Add signals
        self.scorer.add_behavioral_signal("command_success", True)
        self.scorer.add_behavioral_signal("test_result", False)

        assert len(self.scorer.behavioral_signals) == 2

        # Reset
        self.scorer.reset_signals()

        assert len(self.scorer.behavioral_signals) == 0


class TestEnhancedPatternCapture:
    """Test the EnhancedPatternCapture integration"""

    @pytest.fixture
    async def mock_base_capture(self):
        """Create mock base PatternCapture"""
        base = Mock(spec=PatternCapture)
        base.capture_command_pattern = AsyncMock(return_value="memory_123")

        # Mock memory client
        base.memory = Mock()
        base.memory.client = Mock()
        base.memory.client.add_observations = AsyncMock()

        return base

    @pytest.mark.asyncio
    async def test_capture_command_pattern_with_scoring(self, mock_base_capture):
        """Test enhanced command capture with scoring"""
        enhanced = EnhancedPatternCapture(mock_base_capture)

        memory_id = await enhanced.capture_command_pattern_with_scoring(
            command="docker compose up -d",
            context="deployment",
            success=True,
            output="Services started",
        )

        assert memory_id == "memory_123"

        # Verify base method was called
        mock_base_capture.capture_command_pattern.assert_called_once_with(
            command="docker compose up -d",
            context="deployment",
            success=True,
            output="Services started",
        )

        # Verify scoring was calculated
        assert "memory_123" in enhanced.scoring.effectiveness_scores
        score = enhanced.scoring.effectiveness_scores["memory_123"]
        assert score > 0.5  # Success should yield positive score

    @pytest.mark.asyncio
    async def test_capture_with_additional_signals(self, mock_base_capture):
        """Test capture with additional behavioral signals"""
        enhanced = EnhancedPatternCapture(mock_base_capture)

        additional_signals = [
            BehavioralSignal("test_result", True, 0.3),
            BehavioralSignal("task_completion", True, 0.3),
        ]

        memory_id = await enhanced.capture_command_pattern_with_scoring(
            command="pytest tests/",
            context="testing",
            success=True,
            additional_signals=additional_signals,
        )

        # All signals successful, should have high score
        score = enhanced.scoring.effectiveness_scores[memory_id]
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_scoring_metadata_storage(self, mock_base_capture):
        """Test that scoring metadata is stored with memory"""
        enhanced = EnhancedPatternCapture(mock_base_capture)

        await enhanced.capture_command_pattern_with_scoring(
            command="make test", context="testing", success=False
        )

        # Verify observation was added with scoring metadata
        mock_base_capture.memory.client.add_observations.assert_called_once()

        call_args = mock_base_capture.memory.client.add_observations.call_args
        observations = call_args.kwargs["observations"]

        assert len(observations) == 1
        memory_id, observation = observations[0]
        assert memory_id == "memory_123"
        assert observation["type"] == "implicit_scoring"

        # Parse stored metadata
        metadata = json.loads(observation["contents"])
        assert "implicit_score" in metadata
        assert metadata["implicit_score"] < 0.5  # Failure should yield low score

    @pytest.mark.asyncio
    async def test_validate_correlation(self, mock_base_capture):
        """Test correlation validation functionality"""
        enhanced = EnhancedPatternCapture(mock_base_capture)

        # Simulate capturing memories with varying success
        test_memories = []
        expected_effectiveness = []

        for i in range(10):
            success = i >= 5  # Half succeed, half fail
            memory_id = f"memory_{i}"

            # Manually set score for testing
            score = 0.8 if success else 0.2
            enhanced.scoring.effectiveness_scores[memory_id] = score

            test_memories.append(memory_id)
            expected_effectiveness.append(score + np.random.normal(0, 0.1))

        # Validate correlation
        results = await enhanced.validate_correlation(
            test_memories, expected_effectiveness
        )

        assert "correlation" in results
        assert "p_value" in results
        assert "significant" in results
        assert "meets_threshold" in results
        assert results["sample_size"] == 10

        # Should have positive correlation
        assert results["correlation"] > 0.5


class TestBehavioralSignalCorrelation:
    """Test the core innovation: behavioral signals correlate with effectiveness"""

    def test_signal_correlation_hypothesis(self):
        """Test that our signal weighting produces meaningful correlation"""
        scorer = ImplicitScoringMixin()

        # Generate synthetic data simulating real usage
        n_samples = 100
        np.random.seed(42)  # For reproducibility

        calculated_scores = []
        observed_effectiveness = []

        for _ in range(n_samples):
            # Simulate correlated signals
            base_success = np.random.random()

            # Command success influenced by base
            command_success = base_success + np.random.normal(0, 0.1) > 0.5
            scorer.add_behavioral_signal("command_success", command_success)

            # Test result correlated with command
            test_success = base_success + np.random.normal(0, 0.15) > 0.5
            scorer.add_behavioral_signal("test_result", test_success)

            # Task completion correlated with both
            task_success = base_success + np.random.normal(0, 0.2) > 0.5
            scorer.add_behavioral_signal("task_completion", task_success)

            # Calculate score
            score = scorer.calculate_effectiveness_score(f"memory_{_}")
            calculated_scores.append(score)

            # Simulate observed effectiveness (correlated with signals)
            observed = base_success + np.random.normal(0, 0.1)
            observed = max(0.0, min(1.0, observed))
            observed_effectiveness.append(observed)

            # Reset for next iteration
            scorer.reset_signals()

        # Calculate correlation
        correlation = np.corrcoef(calculated_scores, observed_effectiveness)[0, 1]

        # Core hypothesis: behavioral signals correlate with effectiveness
        assert correlation > 0.6, f"Correlation {correlation:.3f} below threshold 0.6"

        # Calculate p-value (simplified)
        n = len(calculated_scores)
        t_stat = correlation * np.sqrt(n - 2) / np.sqrt(1 - correlation**2)
        # For n=100 and correlation>0.6, p-value should be very small
        assert abs(t_stat) > 2.0  # Significant at p<0.05

        print(
            f"✓ Behavioral correlation validated: r={correlation:.3f}, t={t_stat:.2f}"
        )

    def test_weight_distribution_impact(self):
        """Test that our 40/30/30 weight distribution is effective"""
        scorer = ImplicitScoringMixin()

        # Test different weight scenarios
        scenarios = [
            # (command, test, task) success rates -> expected score
            ([True, True, True], 1.0),  # All success
            ([False, False, False], 0.0),  # All failure
            ([True, False, False], 0.4),  # Only command succeeds
            ([False, True, False], 0.3),  # Only test succeeds
            ([False, False, True], 0.3),  # Only task succeeds
            ([True, True, False], 0.7),  # Command + test succeed
            ([True, False, True], 0.7),  # Command + task succeed
            ([False, True, True], 0.6),  # Test + task succeed
        ]

        for (command, test, task), expected in scenarios:
            scorer.reset_signals()
            scorer.add_behavioral_signal("command_success", command)
            scorer.add_behavioral_signal("test_result", test)
            scorer.add_behavioral_signal("task_completion", task)

            score = scorer.calculate_effectiveness_score("test_memory")
            assert pytest.approx(score, rel=1e-3) == expected

        print("✓ Weight distribution (40/30/30) validated")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
