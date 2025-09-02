#!/usr/bin/env python3
"""
Langfuse-First Behavioral Scoring System
All behavioral signals flow through Langfuse for observability and evaluation
"""

import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from langfuse import Langfuse, observe

logger = logging.getLogger(__name__)


@dataclass
class BehavioralScore:
    """Represents a behavioral effectiveness score in Langfuse"""

    trace_id: str
    value: float
    name: str = "behavioral_effectiveness"
    data_type: str = "NUMERIC"
    comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LangfuseScoringSystem:
    """
    Primary scoring system that sends all behavioral signals to Langfuse
    This is the ONLY scoring system - no parallel implementations

    Credentials are injected at runtime via 1Password CLI:
    - op run --env-file=secrets/.env.1password
    - Item UUID: ctyxybforywkjp2krbdpeulzzq
    """

    # Weight distribution validated through testing
    WEIGHTS = {
        "command_success": 0.4,  # 40% - Immediate feedback
        "test_result": 0.3,  # 30% - Validation signal
        "task_completion": 0.3,  # 30% - Goal achievement
    }

    def __init__(self):
        """Initialize with mandatory Langfuse client"""
        # Get credentials from environment (injected by 1Password CLI)
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        # Langfuse is MANDATORY - fail fast if credentials missing
        if not public_key or not secret_key:
            error_msg = (
                "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are REQUIRED. "
                "Langfuse is mandatory for observability, scoring, and evaluation. "
                "Ensure you're running with: op run --env-file=secrets/.env.1password "
                "or have set these environment variables directly."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Initialize Langfuse with credentials
        self.langfuse = Langfuse(
            public_key=public_key, secret_key=secret_key, host=host
        )

        self.current_signals: List[Dict[str, Any]] = []
        self.active_traces: Dict[str, str] = {}  # memory_id -> trace_id mapping
        logger.info(f"LangfuseScoringSystem initialized with Langfuse at {host}")

    def _create_trace_id(self, prefix: str = "") -> str:
        """Create a unique trace ID"""
        return f"{prefix}{uuid.uuid4()}"

    @observe(name="add_behavioral_signal")
    def add_signal(
        self, signal_type: str, success: bool, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a behavioral signal that will contribute to effectiveness score

        Args:
            signal_type: Type of signal (command_success, test_result, task_completion)
            success: Whether the signal indicates success
            context: Additional context for the signal
        """
        if signal_type not in self.WEIGHTS:
            logger.warning(f"Unknown signal type: {signal_type}, skipping")
            return

        signal = {
            "type": signal_type,
            "success": success,
            "weight": self.WEIGHTS[signal_type],
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.current_signals.append(signal)
        logger.debug(f"Added behavioral signal: {signal_type}={success}")

    @observe(name="calculate_behavioral_effectiveness")
    def calculate_effectiveness(
        self, memory_id: str, additional_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate effectiveness score from accumulated signals and send to Langfuse

        Args:
            memory_id: ID of the memory being scored
            additional_context: Extra context for scoring

        Returns:
            Effectiveness score between 0.0 and 1.0
        """
        # Create trace ID for this memory
        trace_id = self._create_trace_id(f"memory_{memory_id}_")
        self.active_traces[memory_id] = trace_id

        if not self.current_signals:
            # No signals = neutral score
            score = 0.5
            comment = "No behavioral signals available"
            signal_summary = {}
        else:
            # Calculate weighted score
            total_score = 0.0
            total_weight = 0.0
            signal_summary = {}

            for signal in self.current_signals:
                signal_type = signal["type"]
                weight = signal["weight"]
                value = 1.0 if signal["success"] else 0.0

                total_score += value * weight
                total_weight += weight

                # Track summary
                if signal_type not in signal_summary:
                    signal_summary[signal_type] = {"success": 0, "total": 0}
                signal_summary[signal_type]["total"] += 1
                if signal["success"]:
                    signal_summary[signal_type]["success"] += 1

            # Normalize score
            score = total_score / total_weight if total_weight > 0 else 0.5

            # Build comment
            comment_parts = []
            for signal_type, stats in signal_summary.items():
                rate = stats["success"] / stats["total"]
                comment_parts.append(
                    f"{signal_type}: {stats['success']}/{stats['total']} ({rate:.0%})"
                )
            comment = " | ".join(comment_parts)

        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))

        # Send score to Langfuse
        self.langfuse.create_score(
            trace_id=trace_id,
            name="behavioral_effectiveness",
            value=score,
            data_type="NUMERIC",
            comment=f"Memory: {memory_id} | {comment}",
            metadata={
                "memory_id": memory_id,
                "effectiveness_score": score,
                "signal_summary": signal_summary,
                "additional_context": additional_context,
            },
        )

        logger.info(
            f"Calculated effectiveness for {memory_id}: {score:.3f} - {comment}"
        )

        # Reset signals for next calculation
        self.current_signals.clear()

        return score

    @observe(name="score_command_execution")
    def score_command(
        self,
        command: str,
        success: bool,
        output: Optional[str] = None,
        error: Optional[str] = None,
    ) -> float:
        """
        Score a command execution and send to Langfuse

        Args:
            command: Command that was executed
            success: Whether command succeeded
            output: Command output if available
            error: Error message if failed

        Returns:
            Command effectiveness score
        """
        score = 1.0 if success else 0.0
        trace_id = self._create_trace_id("command_")

        # Send score to Langfuse
        self.langfuse.create_score(
            trace_id=trace_id,
            name="command_success",
            value=score,
            data_type="NUMERIC",
            comment=f"Command: {command[:100]} | Success: {success}",
            metadata={
                "command": command,
                "success": success,
                "has_output": output is not None,
                "has_error": error is not None,
            },
        )

        return score

    @observe(name="score_test_result")
    def score_test(
        self,
        test_name: str,
        passed: bool,
        assertions: Optional[int] = None,
        failures: Optional[List[str]] = None,
    ) -> float:
        """
        Score a test result and send to Langfuse

        Args:
            test_name: Name of the test
            passed: Whether test passed
            assertions: Number of assertions
            failures: List of failure messages

        Returns:
            Test effectiveness score
        """
        score = 1.0 if passed else 0.0
        trace_id = self._create_trace_id("test_")

        # Send score to Langfuse
        self.langfuse.create_score(
            trace_id=trace_id,
            name="test_success",
            value=score,
            data_type="NUMERIC",
            comment=f"Test: {test_name} | Passed: {passed} | Assertions: {assertions or 0}",
            metadata={
                "test_name": test_name,
                "passed": passed,
                "assertions": assertions,
                "failure_count": len(failures) if failures else 0,
            },
        )

        return score

    @observe(name="score_task_completion")
    def score_task(
        self,
        task_description: str,
        completed: bool,
        partial_success: Optional[float] = None,
        gtd_link: Optional[str] = None,
    ) -> float:
        """
        Score a task completion and send to Langfuse

        Args:
            task_description: Description of the task
            completed: Whether task was completed
            partial_success: Partial success score (0.0-1.0)
            gtd_link: Link to GTD task if available

        Returns:
            Task effectiveness score
        """
        if partial_success is not None:
            score = partial_success
        else:
            score = 1.0 if completed else 0.0

        trace_id = self._create_trace_id("task_")

        # Build metadata
        metadata = {
            "task_description": task_description,
            "completed": completed,
            "score": score,
        }
        if gtd_link:
            metadata["gtd_link"] = gtd_link

        # Send score to Langfuse
        self.langfuse.create_score(
            trace_id=trace_id,
            name="task_success",
            value=score,
            data_type="NUMERIC",
            comment=f"Task: {task_description[:100]} | Score: {score:.2f}",
            metadata=metadata,
        )

        return score

    @observe(name="apply_temporal_decay")
    def apply_temporal_decay(
        self, base_score: float, age_days: float, decay_factor: float = 0.97
    ) -> float:
        """
        Apply temporal decay to a score and track in Langfuse

        Args:
            base_score: Original effectiveness score
            age_days: Age of memory in days
            decay_factor: Daily decay factor (default 0.97 = 3% daily)

        Returns:
            Adjusted score with temporal decay
        """
        # Calculate temporal multiplier
        temporal_multiplier = decay_factor**age_days

        # Combine behavioral and temporal (60/40 split from testing)
        behavioral_weight = 0.6
        temporal_weight = 0.4

        adjusted_score = (
            base_score * behavioral_weight + temporal_multiplier * temporal_weight
        )

        # Ensure within bounds
        adjusted_score = max(0.0, min(1.0, adjusted_score))

        # Track decay in Langfuse
        trace_id = self._create_trace_id("temporal_")
        self.langfuse.create_score(
            trace_id=trace_id,
            name="temporal_adjusted",
            value=adjusted_score,
            data_type="NUMERIC",
            comment=f"Base: {base_score:.3f} | Age: {age_days:.1f} days | Adjusted: {adjusted_score:.3f}",
            metadata={
                "base_score": base_score,
                "age_days": age_days,
                "decay_factor": decay_factor,
                "temporal_multiplier": temporal_multiplier,
                "adjusted_score": adjusted_score,
            },
        )

        return adjusted_score

    @observe(name="create_evaluation_score")
    def create_evaluation_score(
        self,
        dataset_name: str,
        item_id: str,
        predicted: Any,
        expected: Any,
        accuracy: float,
    ) -> None:
        """
        Create an evaluation score in Langfuse for dataset evaluation

        Args:
            dataset_name: Name of the dataset being evaluated
            item_id: ID of the dataset item
            predicted: Predicted output
            expected: Expected output
            accuracy: Accuracy score (0.0-1.0)
        """
        trace_id = self._create_trace_id(f"eval_{dataset_name}_")

        # Create evaluation score
        self.langfuse.create_score(
            trace_id=trace_id,
            name="evaluation_accuracy",
            value=accuracy,
            data_type="NUMERIC",
            comment=f"Dataset: {dataset_name} | Item: {item_id} | Accuracy: {accuracy:.2%}",
            metadata={
                "dataset": dataset_name,
                "item_id": item_id,
                "accuracy": accuracy,
                "predicted_type": type(predicted).__name__,
                "expected_type": type(expected).__name__,
            },
        )

        logger.info(
            f"Created evaluation score for {dataset_name}/{item_id}: {accuracy:.2%}"
        )

    def get_scoring_report(self) -> Dict[str, Any]:
        """
        Get a summary report of current scoring state

        Returns:
            Dictionary with scoring statistics
        """
        signal_stats = {}
        for signal in self.current_signals:
            signal_type = signal["type"]
            if signal_type not in signal_stats:
                signal_stats[signal_type] = {"success": 0, "failure": 0}

            if signal["success"]:
                signal_stats[signal_type]["success"] += 1
            else:
                signal_stats[signal_type]["failure"] += 1

        return {
            "total_signals": len(self.current_signals),
            "signal_statistics": signal_stats,
            "weights": self.WEIGHTS,
            "langfuse_enabled": True,
            "active_traces": len(self.active_traces),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def flush(self):
        """Flush all pending Langfuse data"""
        self.langfuse.flush()
        logger.info("Flushed all pending Langfuse data")


# Singleton instance
_scoring_instance: Optional[LangfuseScoringSystem] = None


def get_langfuse_scoring() -> LangfuseScoringSystem:
    """
    Get or create singleton LangfuseScoringSystem instance

    Returns:
        Singleton scoring system instance
    """
    global _scoring_instance

    if _scoring_instance is None:
        _scoring_instance = LangfuseScoringSystem()

    return _scoring_instance
