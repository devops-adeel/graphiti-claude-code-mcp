"""
Adaptive Infrastructure Sampler for trace budget management.

Dynamically adjusts sampling rate based on:
- Memory pressure
- Operation latency
- Error conditions
- Cascade patterns
"""

import os
import random
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field

try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil not available - memory-based sampling disabled")

logger = logging.getLogger(__name__)


@dataclass
class SamplingMetrics:
    """Tracks metrics for adaptive sampling decisions."""

    total_decisions: int = 0
    sampled_count: int = 0
    memory_triggered: int = 0
    latency_triggered: int = 0
    error_triggered: int = 0
    cascade_triggered: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)

    @property
    def current_rate(self) -> float:
        """Calculate current sampling rate."""
        if self.total_decisions == 0:
            return 0.0
        return self.sampled_count / self.total_decisions

    def reset(self):
        """Reset metrics for new period."""
        self.__init__()


class AdaptiveInfrastructureSampler:
    """
    Samples infrastructure operations based on system state.

    Implements a trace budget mechanism that increases sampling during:
    - High memory pressure
    - Slow operations
    - Errors
    - Cascade patterns
    """

    def __init__(self):
        """Initialize the adaptive sampler with configuration."""
        # Base sampling configuration
        self.base_rate = float(os.getenv("INFRASTRUCTURE_BASE_SAMPLE_RATE", "0.1"))
        self.max_rate = float(os.getenv("INFRASTRUCTURE_MAX_SAMPLE_RATE", "1.0"))

        # Thresholds
        self.memory_threshold = float(os.getenv("MEMORY_PRESSURE_THRESHOLD", "70"))
        self.latency_threshold = float(os.getenv("LATENCY_THRESHOLD_SECONDS", "5.0"))
        self.cascade_window_seconds = int(os.getenv("CASCADE_WINDOW_SECONDS", "60"))

        # Adaptive rate management
        self.current_rate = self.base_rate
        self.rate_adjustment_factor = 0.2  # How much to adjust rate
        self.rate_decay_factor = 0.95  # How fast to decay back to baseline

        # Recent operations tracking for cascade detection
        self.recent_operations: deque = deque(maxlen=100)
        self.cascade_patterns: List[Dict] = []

        # Metrics tracking
        self.metrics = SamplingMetrics()
        self.metrics_window = timedelta(minutes=5)

        # Escalation tracking
        self.escalation_level = 0
        self.max_escalation = 5
        self.last_escalation = datetime.utcnow()

        logger.info(
            f"Adaptive sampler initialized: base_rate={self.base_rate}, "
            f"memory_threshold={self.memory_threshold}%, "
            f"latency_threshold={self.latency_threshold}s"
        )

    def should_sample_infrastructure(self, context: Dict[str, Any]) -> bool:
        """
        Determine if infrastructure operations should be sampled.

        Args:
            context: Dictionary containing operation context:
                - episode_size: Size of the episode
                - langfuse_error: Whether Langfuse detected an error
                - operation_name: Name of the operation
                - start_time: Operation start time

        Returns:
            Boolean indicating whether to sample this operation
        """
        self.metrics.total_decisions += 1

        # Reset metrics if window expired
        if datetime.utcnow() - self.metrics.last_reset > self.metrics_window:
            logger.info(
                f"Sampling metrics for last window: rate={self.metrics.current_rate:.2%}, "
                f"memory_triggered={self.metrics.memory_triggered}, "
                f"cascade_triggered={self.metrics.cascade_triggered}"
            )
            self.metrics.reset()

        # Always sample errors
        if context.get("langfuse_error") or context.get("error"):
            self.metrics.error_triggered += 1
            self.metrics.sampled_count += 1
            self._escalate_sampling("error")
            return True

        # Check memory pressure
        if self._check_memory_pressure():
            self.metrics.memory_triggered += 1
            self.metrics.sampled_count += 1
            self._escalate_sampling("memory")
            return True

        # Check for cascade patterns
        if self._detect_cascade_pattern(context):
            self.metrics.cascade_triggered += 1
            self.metrics.sampled_count += 1
            self._escalate_sampling("cascade")
            return True

        # Check episode size (large episodes more likely to cause issues)
        episode_size = context.get("episode_size", 0)
        if episode_size > 10000:  # Large episode
            self.metrics.sampled_count += 1
            return True

        # Apply adaptive sampling rate
        rate = self._get_adaptive_rate()
        should_sample = random.random() < rate

        if should_sample:
            self.metrics.sampled_count += 1

        # Track operation for cascade detection
        self._track_operation(context)

        # Decay escalation level over time
        self._decay_escalation()

        return should_sample

    def _check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        if not psutil:
            return False

        try:
            memory_percent = psutil.virtual_memory().percent

            # Also check process-specific memory
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / 1024 / 1024

            # Log if approaching threshold
            if memory_percent > self.memory_threshold - 10:
                logger.warning(
                    f"Memory pressure increasing: {memory_percent:.1f}% "
                    f"(process: {process_memory_mb:.1f}MB)"
                )

            return memory_percent > self.memory_threshold
        except Exception as e:
            logger.error(f"Error checking memory pressure: {e}")
            return False

    def _detect_cascade_pattern(self, context: Dict[str, Any]) -> bool:
        """
        Detect memory cascade patterns.

        A cascade is detected when:
        - Multiple slow operations in quick succession
        - Rapidly increasing memory usage
        - Episode size growing over time
        """
        current_time = datetime.utcnow()

        # Check recent operations for cascade indicators
        recent_slow_ops = 0
        memory_increases = 0

        for op in self.recent_operations:
            # Operations within cascade window
            if current_time - op["timestamp"] <= timedelta(
                seconds=self.cascade_window_seconds
            ):
                if op.get("duration", 0) > self.latency_threshold:
                    recent_slow_ops += 1
                if op.get("memory_delta", 0) > 100:  # MB
                    memory_increases += 1

        # Cascade detected if multiple indicators present
        cascade_detected = recent_slow_ops >= 3 or memory_increases >= 2

        if cascade_detected:
            # Record cascade pattern for analysis
            self.cascade_patterns.append(
                {
                    "timestamp": current_time,
                    "slow_ops": recent_slow_ops,
                    "memory_increases": memory_increases,
                    "context": context,
                }
            )
            logger.warning(
                f"Cascade pattern detected: {recent_slow_ops} slow ops, "
                f"{memory_increases} memory increases"
            )

        return cascade_detected

    def _track_operation(self, context: Dict[str, Any]) -> None:
        """Track operation for cascade detection."""
        operation = {
            "timestamp": datetime.utcnow(),
            "operation": context.get("operation_name", "unknown"),
            "episode_size": context.get("episode_size", 0),
        }

        # Add duration if operation completed
        if "start_time" in context:
            operation["duration"] = time.time() - context["start_time"]

        # Add memory info if available
        if psutil:
            try:
                operation["memory_percent"] = psutil.virtual_memory().percent
            except:
                pass

        self.recent_operations.append(operation)

    def _escalate_sampling(self, reason: str) -> None:
        """Increase sampling rate due to detected condition."""
        if self.escalation_level < self.max_escalation:
            self.escalation_level += 1
            self.last_escalation = datetime.utcnow()
            logger.info(
                f"Escalating sampling due to {reason}: level {self.escalation_level}"
            )

    def _decay_escalation(self) -> None:
        """Gradually reduce escalation level over time."""
        if self.escalation_level > 0:
            time_since_escalation = datetime.utcnow() - self.last_escalation
            if time_since_escalation > timedelta(minutes=1):
                self.escalation_level = max(0, self.escalation_level - 1)

    def _get_adaptive_rate(self) -> float:
        """Calculate current adaptive sampling rate."""
        # Start with base rate
        rate = self.base_rate

        # Add escalation adjustment
        rate += self.escalation_level * self.rate_adjustment_factor

        # Apply decay towards baseline
        self.current_rate = self.current_rate * self.rate_decay_factor + rate * (
            1 - self.rate_decay_factor
        )

        # Cap at maximum rate
        return min(self.current_rate, self.max_rate)

    def record_operation_result(
        self,
        context: Dict[str, Any],
        duration: float,
        memory_before: Optional[float] = None,
        memory_after: Optional[float] = None,
    ) -> None:
        """
        Record operation results for adaptive learning.

        Args:
            context: Original operation context
            duration: Operation duration in seconds
            memory_before: Memory usage before operation (MB)
            memory_after: Memory usage after operation (MB)
        """
        # Update context with results
        context["duration"] = duration
        if memory_before and memory_after:
            context["memory_delta"] = memory_after - memory_before

        # Check if this was a slow operation
        if duration > self.latency_threshold:
            self.metrics.latency_triggered += 1
            logger.warning(
                f"Slow operation detected: {context.get('operation_name')} "
                f"took {duration:.2f}s"
            )

        # Track for future cascade detection
        self._track_operation(context)

    def get_sampling_stats(self) -> Dict[str, Any]:
        """Get current sampling statistics."""
        return {
            "current_rate": self._get_adaptive_rate(),
            "base_rate": self.base_rate,
            "escalation_level": self.escalation_level,
            "metrics": {
                "total_decisions": self.metrics.total_decisions,
                "sampled_count": self.metrics.sampled_count,
                "actual_rate": self.metrics.current_rate,
                "memory_triggered": self.metrics.memory_triggered,
                "latency_triggered": self.metrics.latency_triggered,
                "error_triggered": self.metrics.error_triggered,
                "cascade_triggered": self.metrics.cascade_triggered,
            },
            "cascade_patterns": len(self.cascade_patterns),
            "recent_operations": len(self.recent_operations),
        }
