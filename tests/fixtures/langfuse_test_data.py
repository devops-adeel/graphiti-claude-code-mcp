#!/usr/bin/env python3
"""
Test fixtures and mock data for Langfuse integration tests.
Uses langfuse_models.py Pydantic models to ensure data validity.
"""

import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langfuse_integration.langfuse_models import (
    LangfuseObservation,
    LangfuseTrace,
    DetectedPattern,
    TraceStatus,
    ObservationType,
    PhaseType,
    PatternConfidence,
    LangfuseScore,
)


class LangfuseTestData:
    """Generate test data for various Langfuse testing scenarios"""

    @staticmethod
    def create_test_observation(
        name: str = "test_observation",
        obs_type: ObservationType = ObservationType.SPAN,
        start_offset_seconds: int = 0,
        duration_seconds: int = 1,
        metadata: Dict[str, Any] = None,
        output: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create a test observation"""
        start_time = datetime.now() - timedelta(seconds=start_offset_seconds)
        end_time = start_time + timedelta(seconds=duration_seconds)

        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": obs_type.value,
            "trace_id": str(uuid.uuid4()),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "metadata": metadata or {},
            "output": output or {},
            "input": {},
            "level": "INFO",
            "status_message": None,
            "parent_observation_id": None,
        }

    @staticmethod
    def create_test_trace(
        name: str = "test_trace",
        status: TraceStatus = TraceStatus.SUCCESS,
        num_observations: int = 3,
    ) -> Dict[str, Any]:
        """Create a test trace with observations"""
        trace_id = str(uuid.uuid4())
        observations = []

        for i in range(num_observations):
            obs = LangfuseTestData.create_test_observation(
                name=f"observation_{i}",
                start_offset_seconds=num_observations - i,
                duration_seconds=1,
            )
            obs["trace_id"] = trace_id
            observations.append(obs)

        return {
            "id": trace_id,
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "status": status.value,
            "session_id": f"session_{uuid.uuid4()}",
            "observations": observations,
            "tags": ["test", "integration"],
            "scores": [],
        }

    @staticmethod
    def create_state_loss_scenario() -> Dict[str, Any]:
        """Create a trace demonstrating state loss pattern"""
        trace_id = str(uuid.uuid4())

        # First observation has state
        obs1 = LangfuseTestData.create_test_observation(
            name="planning_phase",
            metadata={"phase": "planning"},
            output={
                "tasks": ["task1", "task2"],
                "projects": ["project1"],
                "priorities": ["high", "medium"],
            },
        )

        # Second observation loses state
        obs2 = LangfuseTestData.create_test_observation(
            name="review_phase",
            metadata={"phase": "review"},
            output={
                "summary": "Review complete"
                # Missing tasks, projects, priorities - state loss!
            },
        )

        obs1["trace_id"] = trace_id
        obs2["trace_id"] = trace_id

        return {
            "id": trace_id,
            "name": "state_loss_trace",
            "timestamp": datetime.now().isoformat(),
            "status": TraceStatus.ERROR.value,
            "session_id": f"session_{uuid.uuid4()}",
            "observations": [obs1, obs2],
            "tags": ["state_loss", "test"],
            "scores": [],
        }

    @staticmethod
    def create_interrupt_scenario() -> Dict[str, Any]:
        """Create a trace with interrupt patterns"""
        trace_id = str(uuid.uuid4())

        observations = [
            LangfuseTestData.create_test_observation(
                name="normal_operation", output={"status": "processing"}
            ),
            LangfuseTestData.create_test_observation(
                name="check_in_with_user",  # Interrupt indicator
                output={"__interrupt__": True, "message": "Need user confirmation"},
            ),
            LangfuseTestData.create_test_observation(
                name="wait_for_response",  # Another interrupt indicator
                output={"waiting": True},
            ),
        ]

        for obs in observations:
            obs["trace_id"] = trace_id

        return {
            "id": trace_id,
            "name": "interrupt_trace",
            "timestamp": datetime.now().isoformat(),
            "status": TraceStatus.INTERRUPTED.value,
            "session_id": f"session_{uuid.uuid4()}",
            "observations": observations,
            "tags": ["interrupt", "test"],
            "scores": [],
        }

    @staticmethod
    def create_high_latency_scenario() -> Dict[str, Any]:
        """Create a trace with high latency issues"""
        trace_id = str(uuid.uuid4())

        # Create observation with 10 second latency
        slow_obs = LangfuseTestData.create_test_observation(
            name="slow_model_generation",
            duration_seconds=10,  # High latency!
            metadata={"model": "gpt-4"},
        )
        slow_obs["trace_id"] = trace_id

        return {
            "id": trace_id,
            "name": "high_latency_trace",
            "timestamp": datetime.now().isoformat(),
            "status": TraceStatus.SUCCESS.value,
            "session_id": f"session_{uuid.uuid4()}",
            "observations": [slow_obs],
            "tags": ["latency", "performance", "test"],
            "scores": [
                {"name": "latency", "value": 0.3}  # Low score due to high latency
            ],
        }

    @staticmethod
    def create_phase_transition_scenario() -> Dict[str, Any]:
        """Create a trace with phase transitions"""
        trace_id = str(uuid.uuid4())

        observations = [
            LangfuseTestData.create_test_observation(
                name="capture_phase",
                metadata={"phase": "capture", "current_phase": "capture"},
            ),
            LangfuseTestData.create_test_observation(
                name="planning_phase",
                metadata={"phase": "planning", "current_phase": "planning"},
            ),
            LangfuseTestData.create_test_observation(
                name="review_phase",
                metadata={"phase": "review", "current_phase": "review"},
            ),
        ]

        for obs in observations:
            obs["trace_id"] = trace_id

        return {
            "id": trace_id,
            "name": "phase_transition_trace",
            "timestamp": datetime.now().isoformat(),
            "status": TraceStatus.SUCCESS.value,
            "session_id": f"session_{uuid.uuid4()}",
            "observations": observations,
            "tags": ["phase_transition", "gtd", "test"],
            "scores": [],
        }

    @staticmethod
    def create_test_failure_scenario() -> Dict[str, Any]:
        """Create a trace representing a test failure"""
        trace_id = str(uuid.uuid4())

        observations = [
            LangfuseTestData.create_test_observation(
                name="test_setup", output={"status": "initialized"}
            ),
            LangfuseTestData.create_test_observation(
                name="test_execution",
                output={
                    "error": "AssertionError: Expected 5, got 4",
                    "test_name": "test_addition",
                    "line": 42,
                },
            ),
        ]

        for obs in observations:
            obs["trace_id"] = trace_id

        return {
            "id": trace_id,
            "name": "test_failure_trace",
            "timestamp": datetime.now().isoformat(),
            "status": TraceStatus.ERROR.value,
            "session_id": f"test_session_{uuid.uuid4()}",
            "observations": observations,
            "tags": ["test", "failure", "ci"],
            "scores": [{"name": "test_success", "value": 0.0}],
        }

    @staticmethod
    def create_score_degradation_scenario() -> Dict[str, Any]:
        """Create a trace with degraded scores"""
        trace_id = str(uuid.uuid4())

        obs = LangfuseTestData.create_test_observation(name="low_quality_generation")
        obs["trace_id"] = trace_id

        return {
            "id": trace_id,
            "name": "degraded_score_trace",
            "timestamp": datetime.now().isoformat(),
            "status": TraceStatus.SUCCESS.value,
            "session_id": f"session_{uuid.uuid4()}",
            "observations": [obs],
            "tags": ["quality", "degradation", "test"],
            "scores": [
                {"name": "quality", "value": 0.3},
                {"name": "relevance", "value": 0.4},
                {"name": "coherence", "value": 0.2},
            ],
        }

    @staticmethod
    def create_mock_api_response(traces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a mock Langfuse API response"""
        return {"data": traces, "meta": {"page": 1, "limit": 50, "total": len(traces)}}

    @staticmethod
    def create_detected_pattern(
        pattern_type: str, confidence: float = 0.85, trace_id: str = None
    ) -> Dict[str, Any]:
        """Create a detected pattern"""
        return {
            "signature": f"{pattern_type}_{uuid.uuid4().hex[:8]}",
            "type": pattern_type,
            "confidence": confidence,
            "confidence_level": (
                PatternConfidence.HIGH.value
                if confidence > 0.8
                else (
                    PatternConfidence.MEDIUM.value
                    if confidence > 0.5
                    else PatternConfidence.LOW.value
                )
            ),
            "trace_id": trace_id or str(uuid.uuid4()),
            "details": {
                "detected_at": datetime.now().isoformat(),
                "pattern_type": pattern_type,
            },
            "resolution": f"Suggested fix for {pattern_type}",
        }

    @staticmethod
    def get_all_test_scenarios() -> Dict[str, Dict[str, Any]]:
        """Get all test scenarios as a dictionary"""
        return {
            "normal": LangfuseTestData.create_test_trace(),
            "state_loss": LangfuseTestData.create_state_loss_scenario(),
            "interrupt": LangfuseTestData.create_interrupt_scenario(),
            "high_latency": LangfuseTestData.create_high_latency_scenario(),
            "phase_transition": LangfuseTestData.create_phase_transition_scenario(),
            "test_failure": LangfuseTestData.create_test_failure_scenario(),
            "score_degradation": LangfuseTestData.create_score_degradation_scenario(),
        }


# Mock Langfuse client for testing
class MockLangfuseClient:
    """Mock Langfuse client for testing without real API"""

    def __init__(self, scenarios: List[str] = None):
        """Initialize with specific test scenarios"""
        self.test_data = LangfuseTestData()
        self.scenarios = scenarios or ["normal"]
        self.all_scenarios = self.test_data.get_all_test_scenarios()

    class API:
        """Mock API namespace"""

        def __init__(self, client):
            self.client = client
            self.trace = self.Trace(self)
            self.observations = self.Observations(self)
            self.score_v_2 = self.ScoreV2(self)

        class Trace:
            def __init__(self, api):
                self.api = api
                self.parent = api  # For compatibility

            def list(self, **kwargs):
                """Return mock trace list as Pydantic models"""
                trace_dicts = [
                    self.api.client.all_scenarios.get(
                        s, self.api.client.all_scenarios["normal"]
                    )
                    for s in self.api.client.scenarios
                ]
                # Convert dicts to Trace models
                trace_models = []
                for t in trace_dicts:
                    # Convert observations to models
                    obs_models = []
                    for obs in t.get("observations", []):
                        obs_models.append(
                            LangfuseObservation(
                                id=obs["id"],
                                name=obs.get("name"),
                                type=obs.get("type", ObservationType.SPAN.value),
                                trace_id=obs["trace_id"],
                                start_time=obs.get("start_time"),
                                end_time=obs.get("end_time"),
                                metadata=obs.get("metadata", {}),
                                output=obs.get("output", {}),
                                input=obs.get("input", {}),
                                level=obs.get("level"),
                                status_message=obs.get("status_message"),
                                parent_observation_id=obs.get("parent_observation_id"),
                            )
                        )

                    # Convert scores to models
                    score_models = []
                    for score in t.get("scores", []):
                        score_models.append(
                            LangfuseScore(
                                name=score["name"],
                                value=score["value"],
                                trace_id=t["id"],
                            )
                        )

                    # Create trace model
                    trace_models.append(
                        LangfuseTrace(
                            id=t["id"],
                            name=t.get("name"),
                            timestamp=t["timestamp"],
                            session_id=t.get("session_id"),
                            tags=t.get("tags", []),
                            observations=obs_models,
                            scores=score_models,
                        )
                    )
                return type("Response", (), {"data": trace_models})()

            def get(self, trace_id):
                """Return a specific trace as Pydantic model"""
                t = self.api.client.all_scenarios.get("normal")
                obs_models = []
                for obs in t.get("observations", []):
                    obs_models.append(
                        LangfuseObservation(
                            id=obs["id"],
                            name=obs.get("name"),
                            type=obs.get("type", ObservationType.SPAN.value),
                            trace_id=obs["trace_id"],
                            start_time=obs.get("start_time"),
                            end_time=obs.get("end_time"),
                            metadata=obs.get("metadata", {}),
                            output=obs.get("output", {}),
                            input=obs.get("input", {}),
                            level=obs.get("level"),
                            status_message=obs.get("status_message"),
                            parent_observation_id=obs.get("parent_observation_id"),
                        )
                    )

                score_models = []
                for score in t.get("scores", []):
                    score_models.append(
                        LangfuseScore(
                            name=score["name"], value=score["value"], trace_id=t["id"]
                        )
                    )

                return LangfuseTrace(
                    id=t["id"],
                    name=t.get("name"),
                    timestamp=t["timestamp"],
                    session_id=t.get("session_id"),
                    tags=t.get("tags", []),
                    observations=obs_models,
                    scores=score_models,
                )

        class Observations:
            def __init__(self, api):
                self.api = api
                self.parent = api  # For compatibility

            def get_many(self, trace_id=None, **kwargs):
                """Return mock observations as Pydantic models"""
                # Find trace by ID or return default
                for scenario in self.api.client.all_scenarios.values():
                    if scenario["id"] == trace_id:
                        obs_models = []
                        for obs in scenario["observations"]:
                            obs_models.append(
                                LangfuseObservation(
                                    id=obs["id"],
                                    name=obs.get("name"),
                                    type=obs.get("type", ObservationType.SPAN.value),
                                    trace_id=obs["trace_id"],
                                    start_time=obs.get("start_time"),
                                    end_time=obs.get("end_time"),
                                    metadata=obs.get("metadata", {}),
                                    output=obs.get("output", {}),
                                    input=obs.get("input", {}),
                                    level=obs.get("level"),
                                    status_message=obs.get("status_message"),
                                    parent_observation_id=obs.get(
                                        "parent_observation_id"
                                    ),
                                )
                            )
                        return type("Response", (), {"data": obs_models})()
                return type("Response", (), {"data": []})()

        class ScoreV2:
            def __init__(self, api):
                self.api = api
                self.parent = api  # For compatibility

            def get(self, **kwargs):
                """Return mock scores as Pydantic models"""
                score_dicts = []
                for scenario in self.api.client.all_scenarios.values():
                    score_dicts.extend(scenario.get("scores", []))
                # Convert to LangfuseScore models
                score_models = []
                for score in score_dicts:
                    score_models.append(
                        LangfuseScore(
                            name=score["name"],
                            value=score["value"],
                            trace_id=kwargs.get("trace_id"),
                        )
                    )
                return type("Response", (), {"data": score_models})()

    @property
    def api(self):
        return self.API(self)
