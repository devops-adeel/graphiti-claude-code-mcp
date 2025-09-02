#!/usr/bin/env python3
"""
Extended Pattern Capture with Implicit Scoring for Behavioral Correlation
Enhances existing capture methods with effectiveness scoring from behavioral signals
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BehavioralSignal:
    """Represents a behavioral signal for implicit scoring"""

    signal_type: str  # command_success, test_result, task_completion
    value: bool  # success/failure
    weight: float  # importance weight
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ImplicitScoringMixin:
    """
    Mixin for calculating memory effectiveness from behavioral signals
    Designed to enhance Graphiti's existing temporal weighting system
    """

    # Weight distribution based on POC validation
    SIGNAL_WEIGHTS = {
        "command_success": 0.4,  # 40% - Command execution outcomes
        "test_result": 0.3,  # 30% - Test pass/fail signals
        "task_completion": 0.3,  # 30% - Task completion status
    }

    # Normalization bounds
    MIN_SCORE = 0.0
    MAX_SCORE = 1.0

    def __init__(self):
        """Initialize signal tracking"""
        self.behavioral_signals: List[BehavioralSignal] = []
        self.effectiveness_scores: Dict[str, float] = {}

    def add_behavioral_signal(
        self, signal_type: str, value: bool, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a behavioral signal for scoring

        Args:
            signal_type: Type of signal (command_success, test_result, task_completion)
            value: Success (True) or failure (False)
            context: Additional context for the signal
        """
        if signal_type not in self.SIGNAL_WEIGHTS:
            logger.warning(f"Unknown signal type: {signal_type}")
            return

        signal = BehavioralSignal(
            signal_type=signal_type,
            value=value,
            weight=self.SIGNAL_WEIGHTS[signal_type],
            context=context or {},
        )
        self.behavioral_signals.append(signal)
        logger.debug(f"Added behavioral signal: {signal_type}={value}")

    def calculate_effectiveness_score(
        self,
        memory_id: str,
        additional_signals: Optional[List[BehavioralSignal]] = None,
    ) -> float:
        """
        Calculate effectiveness score from behavioral signals

        Args:
            memory_id: ID of the memory to score
            additional_signals: Extra signals to include in calculation

        Returns:
            Effectiveness score between 0.0 and 1.0
        """
        signals = self.behavioral_signals.copy()
        if additional_signals:
            signals.extend(additional_signals)

        if not signals:
            # No signals = neutral score
            return 0.5

        # Group signals by type
        signal_groups = {}
        for signal in signals:
            if signal.signal_type not in signal_groups:
                signal_groups[signal.signal_type] = []
            signal_groups[signal.signal_type].append(signal)

        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0

        for signal_type, group_signals in signal_groups.items():
            # Calculate success rate for this signal type
            successes = sum(1 for s in group_signals if s.value)
            success_rate = successes / len(group_signals)

            # Apply weight
            weight = self.SIGNAL_WEIGHTS.get(signal_type, 0.0)
            total_score += success_rate * weight
            total_weight += weight

        # Normalize
        if total_weight > 0:
            normalized_score = total_score / total_weight
        else:
            normalized_score = 0.5

        # Clamp to bounds
        final_score = max(self.MIN_SCORE, min(self.MAX_SCORE, normalized_score))

        # Store for later retrieval
        self.effectiveness_scores[memory_id] = final_score

        logger.info(
            f"Calculated effectiveness score for {memory_id}: {final_score:.3f}"
        )
        return final_score

    def correlate_signals_with_effectiveness(
        self, signals: List[BehavioralSignal], observed_effectiveness: List[float]
    ) -> Tuple[float, float]:
        """
        Calculate correlation between behavioral signals and observed effectiveness
        Used for validation and tuning

        Args:
            signals: List of behavioral signals
            observed_effectiveness: Actual effectiveness measurements

        Returns:
            Tuple of (correlation_coefficient, p_value)
        """
        if len(signals) != len(observed_effectiveness):
            raise ValueError("Signals and effectiveness lists must have same length")

        # Convert signals to numeric scores
        signal_scores = []
        for signal in signals:
            score = 1.0 if signal.value else 0.0
            weighted_score = score * signal.weight
            signal_scores.append(weighted_score)

        # Calculate Pearson correlation
        correlation = np.corrcoef(signal_scores, observed_effectiveness)[0, 1]

        # Simple p-value approximation (for demonstration)
        # In production, use scipy.stats.pearsonr
        n = len(signals)
        t_stat = correlation * np.sqrt(n - 2) / np.sqrt(1 - correlation**2)
        # Approximate p-value (two-tailed)
        p_value = 2 * (1 - min(0.99, max(0.01, 0.5 + 0.5 * correlation)))

        return correlation, p_value

    def adjust_score_for_temporal_decay(
        self,
        base_score: float,
        age_days: float,
        decay_factor: float = 0.97,  # 3% daily decay from Graphiti default
    ) -> float:
        """
        Combine implicit score with temporal decay
        This enhances Graphiti's existing temporal weighting

        Args:
            base_score: Initial effectiveness score from signals
            age_days: Age of memory in days
            decay_factor: Daily decay factor (default 0.97)

        Returns:
            Adjusted score accounting for time
        """
        # Apply exponential decay
        temporal_multiplier = decay_factor**age_days

        # Combine with base score
        # Use 60% behavioral, 40% temporal (from POC insights)
        behavioral_weight = 0.6
        temporal_weight = 0.4

        adjusted_score = (
            base_score * behavioral_weight + temporal_multiplier * temporal_weight
        )

        # Clamp to bounds
        return max(self.MIN_SCORE, min(self.MAX_SCORE, adjusted_score))

    def get_scoring_metadata(self, memory_id: str) -> Dict[str, Any]:
        """
        Get scoring metadata for storage with memory

        Args:
            memory_id: ID of the memory

        Returns:
            Dictionary of scoring metadata
        """
        score = self.effectiveness_scores.get(memory_id, 0.5)

        # Calculate signal statistics
        signal_stats = {}
        for signal_type in self.SIGNAL_WEIGHTS:
            type_signals = [
                s for s in self.behavioral_signals if s.signal_type == signal_type
            ]
            if type_signals:
                successes = sum(1 for s in type_signals if s.value)
                signal_stats[signal_type] = {
                    "success_rate": successes / len(type_signals),
                    "count": len(type_signals),
                }

        return {
            "implicit_score": score,
            "signal_stats": signal_stats,
            "scoring_timestamp": datetime.now(timezone.utc).isoformat(),
            "scoring_version": "1.0.0",
            "enhancement_type": "behavioral_correlation",
        }

    def reset_signals(self) -> None:
        """Reset signal tracking for new memory capture"""
        self.behavioral_signals.clear()
        logger.debug("Reset behavioral signals")


class EnhancedPatternCapture:
    """
    Enhanced pattern capture that integrates implicit scoring
    Extends the existing PatternCapture with behavioral correlation
    """

    def __init__(self, base_capture):
        """
        Initialize with existing PatternCapture instance

        Args:
            base_capture: Original PatternCapture instance
        """
        self.base_capture = base_capture
        self.scoring = ImplicitScoringMixin()

    async def capture_command_pattern_with_scoring(
        self,
        command: str,
        context: str,
        success: bool,
        output: str = None,
        additional_signals: Optional[List[BehavioralSignal]] = None,
    ) -> str:
        """
        Capture command pattern with implicit scoring

        Args:
            command: Command that was run
            context: Context where command is useful
            success: Whether command succeeded
            output: Command output if relevant
            additional_signals: Extra behavioral signals

        Returns:
            Memory ID with enhanced scoring
        """
        # Add command success signal
        self.scoring.add_behavioral_signal(
            signal_type="command_success",
            value=success,
            context={"command": command, "context": context},
        )

        # Add any additional signals
        if additional_signals:
            for signal in additional_signals:
                self.scoring.add_behavioral_signal(
                    signal_type=signal.signal_type,
                    value=signal.value,
                    context=signal.context,
                )

        # Capture using base method
        memory_id = await self.base_capture.capture_command_pattern(
            command=command, context=context, success=success, output=output
        )

        # Calculate effectiveness score
        effectiveness = self.scoring.calculate_effectiveness_score(memory_id)

        # Get scoring metadata
        scoring_metadata = self.scoring.get_scoring_metadata(memory_id)

        # Add scoring metadata to memory
        # This would be stored as additional metadata in Neo4j
        if hasattr(self.base_capture, "memory") and self.base_capture.memory:
            await self._add_scoring_metadata(memory_id, scoring_metadata)

        # Reset for next capture
        self.scoring.reset_signals()

        logger.info(
            f"Captured command pattern {memory_id} with effectiveness score: {effectiveness:.3f}"
        )

        return memory_id

    async def _add_scoring_metadata(
        self, memory_id: str, metadata: Dict[str, Any]
    ) -> None:
        """
        Add scoring metadata to existing memory

        Args:
            memory_id: ID of the memory
            metadata: Scoring metadata to add
        """
        try:
            # Add as observation to preserve history
            observation = {
                "type": "implicit_scoring",
                "contents": json.dumps(metadata),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if hasattr(self.base_capture.memory.client, "add_observations"):
                await self.base_capture.memory.client.add_observations(
                    observations=[(memory_id, observation)]
                )
                logger.debug(f"Added scoring metadata to memory {memory_id}")
        except Exception as e:
            logger.warning(f"Could not add scoring metadata: {e}")

    async def validate_correlation(
        self, test_memories: List[str], expected_effectiveness: List[float]
    ) -> Dict[str, Any]:
        """
        Validate that behavioral signals correlate with effectiveness

        Args:
            test_memories: List of memory IDs to validate
            expected_effectiveness: Expected effectiveness for each memory

        Returns:
            Validation results including correlation coefficient
        """
        # Collect signals for test memories
        test_signals = []
        for memory_id in test_memories:
            # This would retrieve signals from stored metadata
            score = self.scoring.effectiveness_scores.get(memory_id, 0.5)
            signal = BehavioralSignal(
                signal_type="command_success", value=score > 0.5, weight=1.0
            )
            test_signals.append(signal)

        # Calculate correlation
        correlation, p_value = self.scoring.correlate_signals_with_effectiveness(
            test_signals, expected_effectiveness
        )

        return {
            "correlation": correlation,
            "p_value": p_value,
            "significant": p_value < 0.05,
            "meets_threshold": correlation > 0.6,
            "sample_size": len(test_memories),
        }
