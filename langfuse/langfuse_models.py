#!/usr/bin/env python3
"""
Pydantic models for Langfuse trace data validation
Ensures consistent structure for Langfuse analysis results
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TraceStatus(str, Enum):
    """Status of a trace"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    INTERRUPTED = "interrupted"


class ObservationType(str, Enum):
    """Types of observations in Langfuse"""
    GENERATION = "generation"
    SPAN = "span"
    EVENT = "event"


class ScoreDataType(str, Enum):
    """Data types for scores"""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


class PhaseType(str, Enum):
    """GTD Coach phase types"""
    PLANNING = "planning"
    CAPTURE = "capture"
    REVIEW = "review"
    ORGANIZE = "organize"
    UNKNOWN = "unknown"


class PatternConfidence(str, Enum):
    """Confidence levels for pattern detection"""
    HIGH = "high"       # > 0.8
    MEDIUM = "medium"   # 0.5 - 0.8
    LOW = "low"         # < 0.5


class LangfuseScore(BaseModel):
    """Model for Langfuse score data"""
    model_config = ConfigDict(use_enum_values=True)
    
    id: Optional[str] = None
    name: str
    value: float = Field(..., ge=0.0, le=1.0)
    comment: Optional[str] = None
    data_type: ScoreDataType = Field(default=ScoreDataType.NUMERIC)
    trace_id: Optional[str] = None
    observation_id: Optional[str] = None
    timestamp: Optional[datetime] = None


class LangfuseObservation(BaseModel):
    """Model for Langfuse observation data"""
    model_config = ConfigDict(use_enum_values=True)
    
    id: str
    name: Optional[str] = None
    type: ObservationType
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    level: Optional[str] = None
    status_message: Optional[str] = None
    parent_observation_id: Optional[str] = None
    trace_id: str
    
    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v):
        """Ensure metadata is JSON serializable"""
        if v is not None:
            import json
            try:
                json.dumps(v)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Metadata must be JSON serializable: {e}")
        return v
    
    @property
    def latency(self) -> Optional[float]:
        """Calculate latency in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def has_interrupt(self) -> bool:
        """Check if observation contains interrupt pattern"""
        interrupt_indicators = ["check_in", "wait_for", "confirm", "__interrupt__"]
        
        if self.name:
            name_lower = self.name.lower()
            if any(indicator in name_lower for indicator in interrupt_indicators):
                return True
        
        if self.output:
            output_str = str(self.output)
            if "__interrupt__" in output_str:
                return True
        
        return False


class LangfuseTrace(BaseModel):
    """Model for Langfuse trace data"""
    model_config = ConfigDict(use_enum_values=True)
    
    id: str
    name: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    release: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    public: bool = Field(default=False)
    observations: List[LangfuseObservation] = Field(default_factory=list)
    scores: List[LangfuseScore] = Field(default_factory=list)
    
    @property
    def observation_count(self) -> int:
        """Get count of observations"""
        return len(self.observations)
    
    @property
    def has_errors(self) -> bool:
        """Check if trace contains errors"""
        for obs in self.observations:
            if obs.status_message and "error" in obs.status_message.lower():
                return True
            if obs.output and "error" in str(obs.output).lower():
                return True
        return False
    
    @property
    def has_interrupts(self) -> bool:
        """Check if trace contains interrupts"""
        return any(obs.has_interrupt for obs in self.observations)
    
    @property
    def average_score(self) -> Optional[float]:
        """Calculate average score"""
        if not self.scores:
            return None
        numeric_scores = [s.value for s in self.scores if s.data_type == ScoreDataType.NUMERIC]
        return sum(numeric_scores) / len(numeric_scores) if numeric_scores else None


class PhaseTransition(BaseModel):
    """Model for phase transition analysis"""
    model_config = ConfigDict(use_enum_values=True)
    
    from_phase: PhaseType
    to_phase: PhaseType
    timestamp: Optional[datetime] = None
    observation_id: Optional[str] = None
    state_before: Dict[str, Any] = Field(default_factory=dict)
    state_after: Dict[str, Any] = Field(default_factory=dict)
    state_lost: List[str] = Field(default_factory=list)
    pattern_signature: Optional[str] = None
    
    @property
    def has_state_loss(self) -> bool:
        """Check if transition resulted in state loss"""
        return len(self.state_lost) > 0


class StateValidation(BaseModel):
    """Model for state validation results"""
    model_config = ConfigDict(use_enum_values=True)
    
    trace_id: str
    state_losses: List[Dict[str, Any]] = Field(default_factory=list)
    inconsistencies: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if state is valid (no issues)"""
        return not (self.state_losses or self.inconsistencies)
    
    @property
    def total_issues(self) -> int:
        """Get total count of issues"""
        return len(self.state_losses) + len(self.inconsistencies) + len(self.warnings)


class DetectedPattern(BaseModel):
    """Model for detected pattern"""
    model_config = ConfigDict(use_enum_values=True)
    
    signature: str = Field(..., description="Unique pattern signature")
    type: str = Field(..., description="Pattern type")
    confidence: float = Field(..., ge=0.0, le=1.0)
    trace_id: Optional[str] = None
    observation_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    resolution: Optional[str] = None
    occurrences: int = Field(default=1)
    projects: List[str] = Field(default_factory=list)
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    
    @property
    def confidence_level(self) -> PatternConfidence:
        """Get confidence level category"""
        if self.confidence > 0.8:
            return PatternConfidence.HIGH
        elif self.confidence >= 0.5:
            return PatternConfidence.MEDIUM
        else:
            return PatternConfidence.LOW
    
    def update_occurrence(self, project: Optional[str] = None):
        """Update pattern occurrence statistics"""
        self.occurrences += 1
        self.last_seen = datetime.now()
        if project and project not in self.projects:
            self.projects.append(project)


class AnalysisResult(BaseModel):
    """Model for trace analysis results"""
    model_config = ConfigDict(use_enum_values=True)
    
    status: Literal["success", "error"] = Field(default="success")
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Analysis data
    traces_analyzed: int = Field(default=0)
    hours_analyzed: Optional[int] = None
    session_id: Optional[str] = None
    
    # Results
    traces: List[LangfuseTrace] = Field(default_factory=list)
    patterns_detected: List[DetectedPattern] = Field(default_factory=list)
    phase_transitions: List[PhaseTransition] = Field(default_factory=list)
    state_validations: List[StateValidation] = Field(default_factory=list)
    
    # Metrics
    total_observations: int = Field(default=0)
    total_errors: int = Field(default=0)
    total_interrupts: int = Field(default=0)
    unique_patterns: int = Field(default=0)
    state_losses: int = Field(default=0)
    
    @property
    def has_issues(self) -> bool:
        """Check if analysis found any issues"""
        return (self.total_errors > 0 or 
                self.state_losses > 0 or 
                len(self.patterns_detected) > 0)
    
    def add_pattern(self, pattern: DetectedPattern):
        """Add a detected pattern and update metrics"""
        self.patterns_detected.append(pattern)
        self.unique_patterns = len(set(p.signature for p in self.patterns_detected))
    
    def add_trace(self, trace: LangfuseTrace):
        """Add a trace and update metrics"""
        self.traces.append(trace)
        self.total_observations += trace.observation_count
        if trace.has_errors:
            self.total_errors += 1
        if trace.has_interrupts:
            self.total_interrupts += 1


class PredictionResult(BaseModel):
    """Model for pattern prediction results"""
    model_config = ConfigDict(use_enum_values=True)
    
    trace_id: str
    predictions: List[Dict[str, Any]] = Field(default_factory=list)
    high_confidence_count: int = Field(default=0)
    recommendation: Optional[str] = None
    confidence_threshold: float = Field(default=0.7)
    
    def add_prediction(
        self,
        issue_type: str,
        pattern: str,
        confidence: float,
        resolution: Optional[str] = None
    ):
        """Add a prediction"""
        self.predictions.append({
            "issue_type": issue_type,
            "pattern": pattern,
            "confidence": confidence,
            "resolution": resolution
        })
        
        if confidence > 0.8:
            self.high_confidence_count += 1
        
        # Update recommendation with highest confidence prediction
        if not self.recommendation or confidence > self.predictions[0]["confidence"]:
            self.recommendation = resolution
            # Re-sort predictions by confidence
            self.predictions.sort(key=lambda x: x["confidence"], reverse=True)


class TestFailureAnalysis(BaseModel):
    """Model for test failure analysis"""
    model_config = ConfigDict(use_enum_values=True)
    
    session_id: str
    traces: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    interrupts: List[Dict[str, Any]] = Field(default_factory=list)
    state_transitions: List[Dict[str, Any]] = Field(default_factory=list)
    patterns: List[DetectedPattern] = Field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        """Get total error count"""
        return len(self.errors)
    
    @property
    def has_critical_issues(self) -> bool:
        """Check for critical issues requiring immediate attention"""
        # Critical if multiple errors or state transitions with loss
        return self.error_count > 3 or any(
            "state_lost" in str(transition) 
            for transition in self.state_transitions
        )
    
    def get_error_summary(self) -> str:
        """Generate error summary"""
        if not self.errors:
            return "No errors detected"
        
        error_types = {}
        for error in self.errors:
            error_type = error.get("observation", "unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        summary = f"Found {self.error_count} errors: "
        summary += ", ".join(f"{count} in {type}" for type, count in error_types.items())
        return summary


class MonitoringStatus(BaseModel):
    """Model for real-time monitoring status"""
    model_config = ConfigDict(use_enum_values=True)
    
    active_sessions: List[str] = Field(default_factory=list)
    monitoring_start: datetime = Field(default_factory=datetime.now)
    traces_monitored: int = Field(default=0)
    anomalies_detected: int = Field(default=0)
    latest_trace_id: Optional[str] = None
    latest_anomaly: Optional[Dict[str, Any]] = None
    
    def update_status(
        self,
        trace_id: str,
        anomaly_detected: bool = False,
        anomaly_details: Optional[Dict[str, Any]] = None
    ):
        """Update monitoring status"""
        self.traces_monitored += 1
        self.latest_trace_id = trace_id
        
        if anomaly_detected:
            self.anomalies_detected += 1
            self.latest_anomaly = anomaly_details or {"trace_id": trace_id}
    
    @property
    def monitoring_duration(self) -> float:
        """Get monitoring duration in seconds"""
        return (datetime.now() - self.monitoring_start).total_seconds()
    
    @property
    def anomaly_rate(self) -> float:
        """Calculate anomaly detection rate"""
        if self.traces_monitored == 0:
            return 0.0
        return self.anomalies_detected / self.traces_monitored