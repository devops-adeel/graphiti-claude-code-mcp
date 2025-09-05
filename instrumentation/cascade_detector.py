"""
Memory cascade pattern detector for Graphiti operations.

Identifies patterns where one slow operation triggers a chain of
memory pressure events, enabling proactive mitigation.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CascadeType(Enum):
    """Types of cascade patterns including Gen AI specific patterns."""

    MEMORY_EXHAUSTION = "memory_exhaustion"
    LATENCY_PROPAGATION = "latency_propagation"
    SEMAPHORE_STARVATION = "semaphore_starvation"
    BATCH_OVERFLOW = "batch_overflow"
    LLM_TIMEOUT = "llm_timeout"
    # Gen AI specific cascade types
    TOKEN_OVERFLOW = "token_overflow"  # Context window exceeded
    MODEL_STRUGGLING = "model_struggling"  # Temperature adjustments, retries
    CONVERSATION_LOOP = "conversation_loop"  # Repetitive tool calls
    GPU_SATURATION = "gpu_saturation"  # Local model resource exhaustion


@dataclass
class CascadeEvent:
    """Individual event in a cascade pattern with Gen AI attributes."""

    timestamp: datetime
    operation: str
    duration: float
    memory_delta: float
    memory_percent: float
    error: Optional[str] = None
    trace_id: Optional[str] = None
    # Gen AI specific attributes
    finish_reason: Optional[str] = None  # stop, length, error, etc.
    temperature: Optional[float] = None  # Model temperature setting
    token_count: Optional[int] = None  # Total tokens used
    model: Optional[str] = None  # Model name
    gpu_memory_mb: Optional[float] = None  # GPU memory for local models

    @property
    def severity(self) -> float:
        """Calculate event severity score."""
        score = 0.0

        # Duration impact
        if self.duration > 10:
            score += 3.0
        elif self.duration > 5:
            score += 2.0
        elif self.duration > 2:
            score += 1.0

        # Memory impact
        if self.memory_delta > 500:
            score += 3.0
        elif self.memory_delta > 200:
            score += 2.0
        elif self.memory_delta > 100:
            score += 1.0

        # Memory pressure
        if self.memory_percent > 80:
            score += 2.0
        elif self.memory_percent > 70:
            score += 1.0

        # Error presence
        if self.error:
            score += 2.0

        return score


@dataclass
class CascadePattern:
    """Detected cascade pattern with events and analysis."""

    pattern_id: str
    cascade_type: CascadeType
    start_time: datetime
    end_time: Optional[datetime]
    events: List[CascadeEvent] = field(default_factory=list)
    total_memory_impact: float = 0.0
    max_latency: float = 0.0
    affected_operations: set = field(default_factory=set)
    mitigation_triggered: bool = False

    @property
    def duration(self) -> timedelta:
        """Calculate cascade duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return datetime.utcnow() - self.start_time

    @property
    def severity_score(self) -> float:
        """Calculate overall cascade severity."""
        if not self.events:
            return 0.0
        return sum(e.severity for e in self.events) / len(self.events)

    @property
    def is_critical(self) -> bool:
        """Check if cascade is critical."""
        return (
            self.severity_score > 5.0
            or self.total_memory_impact > 1000
            or self.max_latency > 30
            or len(self.events) > 10
        )


class CascadeDetector:
    """
    Detects and analyzes memory cascade patterns in real-time.

    A cascade occurs when one slow or memory-intensive operation
    triggers a chain reaction of performance degradation.
    """

    def __init__(
        self,
        window_seconds: int = 60,
        min_events_for_cascade: int = 3,
        correlation_threshold: float = 0.7,
    ):
        """
        Initialize cascade detector.

        Args:
            window_seconds: Time window for cascade detection
            min_events_for_cascade: Minimum events to declare cascade
            correlation_threshold: Threshold for event correlation
        """
        self.window_seconds = window_seconds
        self.min_events_for_cascade = min_events_for_cascade
        self.correlation_threshold = correlation_threshold

        # Event tracking
        self.recent_events: deque = deque(maxlen=1000)
        self.active_cascades: Dict[str, CascadePattern] = {}
        self.completed_cascades: List[CascadePattern] = []

        # Pattern learning
        self.cascade_signatures: List[Dict] = []
        self.mitigation_strategies: Dict[CascadeType, List[str]] = {
            CascadeType.MEMORY_EXHAUSTION: [
                "Reduce batch size",
                "Increase memory limits",
                "Trigger garbage collection",
                "Defer non-critical operations",
            ],
            CascadeType.LATENCY_PROPAGATION: [
                "Increase timeout thresholds",
                "Enable request circuit breaker",
                "Reduce concurrent operations",
                "Cache frequent queries",
            ],
            CascadeType.SEMAPHORE_STARVATION: [
                "Increase semaphore capacity",
                "Implement fairness queuing",
                "Add backpressure mechanism",
            ],
            CascadeType.BATCH_OVERFLOW: [
                "Reduce batch size dynamically",
                "Implement adaptive batching",
                "Add overflow queue",
            ],
            CascadeType.LLM_TIMEOUT: [
                "Increase LLM timeout",
                "Implement retry with backoff",
                "Use simpler prompts",
                "Switch to faster model",
            ],
            # Gen AI specific mitigations
            CascadeType.TOKEN_OVERFLOW: [
                "Reduce prompt length",
                "Implement context window management",
                "Use summarization for long contexts",
                "Switch to model with larger context",
            ],
            CascadeType.MODEL_STRUGGLING: [
                "Lower temperature setting",
                "Use more deterministic prompts",
                "Switch to more capable model",
                "Add few-shot examples",
            ],
            CascadeType.CONVERSATION_LOOP: [
                "Break conversation context",
                "Reset tool call history",
                "Implement loop detection",
                "Add conversation timeout",
            ],
            CascadeType.GPU_SATURATION: [
                "Reduce model precision (fp16)",
                "Implement model quantization",
                "Add GPU memory monitoring",
                "Switch to CPU inference",
                "Use smaller model variant",
            ],
        }

        # Gen AI specific tracking
        self.temperature_adjustments: deque = deque(maxlen=100)
        self.finish_reason_history: deque = deque(maxlen=100)
        self.tool_call_patterns: deque = deque(maxlen=100)

        logger.info(
            f"CascadeDetector initialized: window={window_seconds}s, "
            f"min_events={min_events_for_cascade}"
        )

    def record_event(
        self,
        operation: str,
        duration: float,
        memory_delta: float,
        memory_percent: float,
        error: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[CascadePattern]:
        """
        Record an operation event and check for cascades.

        Args:
            operation: Name of the operation
            duration: Operation duration in seconds
            memory_delta: Memory change in MB
            memory_percent: Current memory usage percentage
            error: Optional error message
            trace_id: Optional trace ID for correlation

        Returns:
            Detected cascade pattern if any
        """
        # Create event
        event = CascadeEvent(
            timestamp=datetime.utcnow(),
            operation=operation,
            duration=duration,
            memory_delta=memory_delta,
            memory_percent=memory_percent,
            error=error,
            trace_id=trace_id,
        )

        # Add to recent events
        self.recent_events.append(event)

        # Check for cascade patterns
        cascade = self._detect_cascade(event)

        if cascade:
            logger.warning(
                f"Cascade detected: {cascade.cascade_type.value} "
                f"with {len(cascade.events)} events, "
                f"severity={cascade.severity_score:.2f}"
            )

            # Suggest mitigation
            self._suggest_mitigation(cascade)

        return cascade

    def _detect_cascade(self, trigger_event: CascadeEvent) -> Optional[CascadePattern]:
        """
        Detect if recent events form a cascade pattern.

        Args:
            trigger_event: The latest event that might trigger detection

        Returns:
            Detected cascade pattern or None
        """
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=self.window_seconds)

        # Get events within window
        window_events = [e for e in self.recent_events if e.timestamp >= window_start]

        if len(window_events) < self.min_events_for_cascade:
            return None

        # Check for cascade patterns
        cascade_type = self._identify_cascade_type(window_events)
        if not cascade_type:
            return None

        # Create cascade pattern
        pattern_id = f"cascade_{current_time.timestamp():.0f}"
        cascade = CascadePattern(
            pattern_id=pattern_id,
            cascade_type=cascade_type,
            start_time=window_events[0].timestamp,
            end_time=None,
            events=window_events.copy(),
        )

        # Calculate metrics
        cascade.total_memory_impact = sum(e.memory_delta for e in window_events)
        cascade.max_latency = max(e.duration for e in window_events)
        cascade.affected_operations = {e.operation for e in window_events}

        # Check if cascade is still active
        if trigger_event.severity > 3.0:
            self.active_cascades[pattern_id] = cascade
        else:
            cascade.end_time = current_time
            self.completed_cascades.append(cascade)

        return cascade

    def _identify_cascade_type(
        self, events: List[CascadeEvent]
    ) -> Optional[CascadeType]:
        """
        Identify the type of cascade from event patterns including Gen AI patterns.

        Args:
            events: List of events to analyze

        Returns:
            Identified cascade type or None
        """
        if not events:
            return None

        # Calculate pattern indicators
        avg_memory_delta = sum(e.memory_delta for e in events) / len(events)
        max_memory_percent = max(e.memory_percent for e in events)
        avg_duration = sum(e.duration for e in events) / len(events)
        error_rate = sum(1 for e in events if e.error) / len(events)

        # Gen AI specific indicators
        finish_reasons = [e.finish_reason for e in events if e.finish_reason]
        length_finish_count = sum(1 for r in finish_reasons if r == "length")
        temperature_changes = sum(
            1
            for i in range(1, len(events))
            if events[i].temperature
            and events[i - 1].temperature
            and events[i].temperature != events[i - 1].temperature
        )

        # Check for token overflow (Ollama "length" finish reason)
        if length_finish_count >= 2 or (
            length_finish_count > 0 and avg_memory_delta > 100
        ):
            return CascadeType.TOKEN_OVERFLOW

        # Check for model struggling (temperature adjustments, retries)
        if temperature_changes >= 2 or (
            error_rate > 0.2 and any(e.temperature for e in events)
        ):
            return CascadeType.MODEL_STRUGGLING

        # Check for conversation loops (repetitive tool calls)
        operations = [e.operation for e in events[-10:]]
        if len(operations) >= 5:
            # Check for repeating pattern
            for pattern_len in [2, 3, 4]:
                if len(operations) >= pattern_len * 2:
                    pattern = operations[:pattern_len]
                    if operations[pattern_len : pattern_len * 2] == pattern:
                        return CascadeType.CONVERSATION_LOOP

        # Check for GPU saturation (local models)
        gpu_events = [e for e in events if e.gpu_memory_mb is not None]
        if gpu_events:
            avg_gpu_memory = sum(e.gpu_memory_mb for e in gpu_events) / len(gpu_events)
            max_gpu_memory = max(e.gpu_memory_mb for e in gpu_events)
            if max_gpu_memory > 4000 or (avg_gpu_memory > 3000 and avg_duration > 5):
                return CascadeType.GPU_SATURATION

        # Original cascade patterns
        # Memory exhaustion pattern
        if max_memory_percent > 75 and avg_memory_delta > 50:
            return CascadeType.MEMORY_EXHAUSTION

        # Latency propagation pattern
        if avg_duration > 5 and len(events) > 5:
            return CascadeType.LATENCY_PROPAGATION

        # LLM timeout pattern
        if error_rate > 0.3 and "timeout" in str(events[-1].error).lower():
            return CascadeType.LLM_TIMEOUT

        # Batch overflow pattern
        if "batch" in str(events[-1].operation).lower() and avg_memory_delta > 100:
            return CascadeType.BATCH_OVERFLOW

        # Semaphore starvation pattern
        if all(
            "semaphore" in e.operation.lower() or e.duration > 10 for e in events[-3:]
        ):
            return CascadeType.SEMAPHORE_STARVATION

        # Generic cascade if multiple indicators
        indicators = sum(
            [
                max_memory_percent > 70,
                avg_duration > 3,
                error_rate > 0.2,
                len(events) > 7,
                length_finish_count > 0,  # Gen AI indicator
                temperature_changes > 0,  # Gen AI indicator
            ]
        )

        if indicators >= 2:
            return CascadeType.LATENCY_PROPAGATION

        return None

    def _suggest_mitigation(self, cascade: CascadePattern) -> List[str]:
        """
        Suggest mitigation strategies for cascade.

        Args:
            cascade: Cascade pattern to mitigate

        Returns:
            List of mitigation suggestions
        """
        suggestions = self.mitigation_strategies.get(cascade.cascade_type, [])

        # Add specific suggestions based on cascade characteristics
        if cascade.total_memory_impact > 500:
            suggestions.append("Consider memory profiling to identify leaks")

        if cascade.max_latency > 20:
            suggestions.append("Review timeout configurations")

        if len(cascade.affected_operations) > 5:
            suggestions.append("Consider operation isolation or queuing")

        logger.info(
            f"Mitigation suggestions for {cascade.cascade_type.value}: "
            f"{', '.join(suggestions[:3])}"
        )

        return suggestions

    def get_active_cascades(self) -> List[CascadePattern]:
        """Get currently active cascade patterns."""
        # Check for expired cascades
        current_time = datetime.utcnow()
        expired = []

        for pattern_id, cascade in self.active_cascades.items():
            if cascade.duration > timedelta(seconds=self.window_seconds * 2):
                cascade.end_time = current_time
                self.completed_cascades.append(cascade)
                expired.append(pattern_id)

        for pattern_id in expired:
            del self.active_cascades[pattern_id]

        return list(self.active_cascades.values())

    def get_cascade_history(
        self, hours: int = 24, cascade_type: Optional[CascadeType] = None
    ) -> List[CascadePattern]:
        """
        Get historical cascade patterns.

        Args:
            hours: Hours of history to retrieve
            cascade_type: Optional filter by cascade type

        Returns:
            List of historical cascade patterns
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        history = [c for c in self.completed_cascades if c.start_time >= cutoff]

        if cascade_type:
            history = [c for c in history if c.cascade_type == cascade_type]

        return history

    def predict_cascade_risk(
        self, current_metrics: Dict[str, float]
    ) -> Tuple[float, Optional[CascadeType]]:
        """
        Predict cascade risk based on current metrics.

        Args:
            current_metrics: Current system metrics

        Returns:
            Tuple of (risk_score, predicted_cascade_type)
        """
        risk_score = 0.0
        predicted_type = None

        # Memory pressure risk
        memory_percent = current_metrics.get("memory_percent", 0)
        if memory_percent > 70:
            risk_score += (memory_percent - 70) / 30 * 0.4
            predicted_type = CascadeType.MEMORY_EXHAUSTION

        # Latency risk
        avg_latency = current_metrics.get("avg_latency", 0)
        if avg_latency > 3:
            risk_score += min(avg_latency / 10, 0.3)
            if not predicted_type:
                predicted_type = CascadeType.LATENCY_PROPAGATION

        # Error rate risk
        error_rate = current_metrics.get("error_rate", 0)
        if error_rate > 0.1:
            risk_score += min(error_rate, 0.3)

        # Recent cascade risk
        recent_cascades = self.get_cascade_history(hours=1)
        if recent_cascades:
            risk_score += 0.2
            if not predicted_type:
                predicted_type = recent_cascades[-1].cascade_type

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        return risk_score, predicted_type

    def get_cascade_statistics(self) -> Dict[str, Any]:
        """Get statistics about cascade patterns."""
        stats = {
            "active_cascades": len(self.active_cascades),
            "completed_cascades_24h": len(self.get_cascade_history(hours=24)),
            "cascade_types": {},
            "avg_cascade_duration": 0,
            "avg_cascade_severity": 0,
            "total_memory_impact_24h": 0,
        }

        # Calculate type distribution
        for cascade in self.get_cascade_history(hours=24):
            cascade_type = cascade.cascade_type.value
            stats["cascade_types"][cascade_type] = (
                stats["cascade_types"].get(cascade_type, 0) + 1
            )
            stats["total_memory_impact_24h"] += cascade.total_memory_impact

        # Calculate averages
        if stats["completed_cascades_24h"] > 0:
            cascades = self.get_cascade_history(hours=24)
            stats["avg_cascade_duration"] = sum(
                c.duration.total_seconds() for c in cascades
            ) / len(cascades)
            stats["avg_cascade_severity"] = sum(
                c.severity_score for c in cascades
            ) / len(cascades)

        return stats
