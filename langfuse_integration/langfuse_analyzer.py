#!/usr/bin/env python3
"""
Langfuse Analyzer - Wrapper for analyze_langfuse_traces.py
Provides async integration with Langfuse trace analysis for the MCP server
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json

# Add GTD Coach scripts to path to import analyze_langfuse_traces
gtd_scripts_path = Path.home() / "gtd-coach" / "scripts"
if gtd_scripts_path.exists():
    sys.path.insert(0, str(gtd_scripts_path))

try:
    from .analyze_langfuse_traces import (
        analyze_recent_traces,
        get_trace_details,
        analyze_phase_transition,
        extract_prompt_metadata,
        format_conversation_flow,
        validate_state_continuity,
        analyze_test_failure,
        debug_session,
    )

    ANALYZER_AVAILABLE = True
except ImportError:
    logging.warning("analyze_langfuse_traces not found. Some features will be limited.")
    ANALYZER_AVAILABLE = False

from langfuse import Langfuse
from .langfuse_patterns import PatternDetector
from graphiti_memory import get_shared_memory

logger = logging.getLogger(__name__)


class LangfuseAnalyzer:
    """
    Async wrapper for Langfuse trace analysis functions
    Integrates with Graphiti memory for pattern storage
    """

    def __init__(self):
        """Initialize Langfuse analyzer with API credentials"""
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        self.host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not self.public_key or not self.secret_key:
            logger.warning("Langfuse API keys not configured")
            self.client = None
        else:
            self.client = Langfuse(
                public_key=self.public_key, secret_key=self.secret_key, host=self.host
            )
            # Tag all traces from this client as MCP-internal to prevent analysis loops
            # This ensures we can monitor the MCP server while preventing it from analyzing itself
            self.mcp_tags = [
                os.getenv("MCP_TRACE_TAG", "mcp-internal"),
                os.getenv("MCP_ANALYZER_TAG", "mcp-analyzer"),
            ]
            self.mcp_metadata = {
                "source": os.getenv("MCP_SOURCE_IDENTIFIER", "mcp-server"),
                "component": "langfuse-analyzer",
                "version": os.getenv("MCP_COMPONENT_VERSION", "1.0.0"),
            }

        self.pattern_detector = PatternDetector()
        self.memory = None
        self._initialized = False

    async def initialize(self):
        """Initialize connection to shared memory"""
        if not self._initialized:
            self.memory = await get_shared_memory()
            self._initialized = True
            logger.info("LangfuseAnalyzer initialized with shared memory")

    def _should_skip_trace(self, trace) -> bool:
        """
        Check if a trace should be skipped to prevent analysis loops.
        Returns True if the trace is from the MCP server itself.
        """
        # Skip if tagged as MCP-internal
        if hasattr(trace, "tags") and trace.tags:
            if any(tag in self.mcp_tags for tag in trace.tags):
                return True

        # Also check metadata for extra safety
        if hasattr(trace, "metadata") and trace.metadata:
            if (
                isinstance(trace.metadata, dict)
                and trace.metadata.get("source") == self.mcp_metadata["source"]
            ):
                return True

        return False

    async def analyze_recent_traces(
        self,
        hours_back: int = 1,
        session_id: Optional[str] = None,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze recent Langfuse traces and detect patterns

        Args:
            hours_back: How many hours back to look
            session_id: Optional specific session to analyze
            project: Optional project name for filtering

        Returns:
            Analysis results with detected patterns
        """
        if not self.client:
            return {"error": "Langfuse client not configured"}

        # Get recent traces
        from_timestamp = datetime.now() - timedelta(hours=hours_back)

        traces = self.client.api.trace.list(
            from_timestamp=from_timestamp, session_id=session_id, limit=50
        ).data

        if not traces:
            return {
                "status": "success",
                "message": "No traces found",
                "traces": [],
                "patterns": [],
            }

        # Filter out MCP-internal traces to prevent analysis loops
        filtered_traces = []
        skipped_count = 0

        for trace in traces:
            if self._should_skip_trace(trace):
                logger.debug(f"Skipping MCP-internal trace: {trace.id}")
                skipped_count += 1
                continue

            filtered_traces.append(trace)

        if skipped_count > 0:
            logger.info(
                f"Filtered out {skipped_count} MCP-internal traces to prevent loops"
            )

        # Analyze filtered traces
        analysis_results = []
        detected_patterns = []

        for trace in filtered_traces:
            # Get observations for trace
            observations_response = self.client.api.observations.get_many(
                trace_id=trace.id
            )
            # Extract data from response
            observations = (
                observations_response.data
                if hasattr(observations_response, "data")
                else observations_response
            )

            # Analyze this trace
            trace_analysis = {
                "trace_id": trace.id,
                "name": trace.name,
                "session_id": trace.session_id,
                "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
                "observations": len(observations) if observations else 0,
            }

            # Detect patterns
            patterns = await self._detect_trace_patterns(trace, observations)
            if patterns:
                detected_patterns.extend(patterns)
                trace_analysis["patterns"] = patterns

            # Check for interrupts
            interrupt_found = self._check_for_interrupts(observations)
            trace_analysis["has_interrupts"] = interrupt_found

            # Get scores
            scores_response = self.client.api.score_v_2.get(trace_id=trace.id)
            scores = (
                scores_response.data
                if hasattr(scores_response, "data")
                else scores_response
            )
            if scores:
                trace_analysis["scores"] = [
                    {
                        "name": s.get("name") if isinstance(s, dict) else s.name,
                        "value": s.get("value") if isinstance(s, dict) else s.value,
                    }
                    for s in scores
                ]

            analysis_results.append(trace_analysis)

        # Store detected patterns in Graphiti
        if detected_patterns and self.memory:
            for pattern in detected_patterns:
                await self._store_pattern_in_memory(pattern, project)

        return {
            "status": "success",
            "hours_analyzed": hours_back,
            "total_traces": len(traces),
            "traces": analysis_results,
            "patterns_detected": len(detected_patterns),
            "unique_patterns": len(set(p["signature"] for p in detected_patterns)),
        }

    async def analyze_phase_transitions(
        self, trace_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze phase transitions for state loss detection

        Args:
            trace_id: Specific trace to analyze
            session_id: Session to analyze all traces

        Returns:
            Phase transition analysis with state loss detection
        """
        if not self.client:
            return {"error": "Langfuse client not configured"}

        results = []

        if trace_id:
            # Analyze single trace
            observations_response = self.client.api.observations.get_many(
                trace_id=trace_id
            )
            observations = (
                observations_response.data
                if hasattr(observations_response, "data")
                else observations_response
            )
            if ANALYZER_AVAILABLE:
                transitions = analyze_phase_transition(trace_id, observations)
            else:
                transitions = self._basic_phase_analysis(observations)

            if transitions:
                # Generate pattern signatures for state losses
                for trans in transitions:
                    if trans.get("state_lost"):
                        signature = self.pattern_detector.generate_signature(
                            "state_loss",
                            from_phase=trans["from_phase"],
                            to_phase=trans["to_phase"],
                        )
                        trans["pattern_signature"] = signature

                        # Store pattern
                        if self.memory:
                            await self._store_pattern_in_memory(
                                {
                                    "signature": signature,
                                    "type": "state_loss",
                                    "confidence": 0.9,
                                    "trace_id": trace_id,
                                    "details": trans,
                                }
                            )

            results.append({"trace_id": trace_id, "transitions": transitions})

        elif session_id:
            # Analyze all traces in session
            traces = self.client.api.trace.list(session_id=session_id).data
            for trace in traces:
                # Skip MCP-internal traces
                if self._should_skip_trace(trace):
                    logger.debug(f"Skipping MCP-internal trace in session: {trace.id}")
                    continue

                observations_response = self.client.api.observations.get_many(
                    trace_id=trace.id
                )
                observations = (
                    observations_response.data
                    if hasattr(observations_response, "data")
                    else observations_response
                )
                if ANALYZER_AVAILABLE:
                    transitions = analyze_phase_transition(trace.id, observations)
                else:
                    transitions = self._basic_phase_analysis(observations)

                if transitions:
                    results.append({"trace_id": trace.id, "transitions": transitions})

        # Analyze patterns across results
        state_loss_count = sum(
            len([t for t in r.get("transitions", []) if t.get("state_lost")])
            for r in results
        )

        return {
            "status": "success",
            "traces_analyzed": len(results),
            "total_transitions": sum(len(r.get("transitions", [])) for r in results),
            "state_losses_detected": state_loss_count,
            "results": results,
        }

    async def validate_state_continuity(
        self, trace_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate state continuity across observations

        Args:
            trace_id: Specific trace to validate
            session_id: Session to validate all traces

        Returns:
            State validation results with issues detected
        """
        if not self.client:
            return {"error": "Langfuse client not configured"}

        validation_results = []

        traces_to_validate = []
        if trace_id:
            traces_to_validate = [{"id": trace_id}]
        elif session_id:
            traces_to_validate = self.client.api.trace.list(session_id=session_id).data

        for trace in traces_to_validate:
            trace_id = trace.get("id") if isinstance(trace, dict) else trace.id
            observations_response = self.client.api.observations.get_many(
                trace_id=trace_id
            )
            observations = (
                observations_response.data
                if hasattr(observations_response, "data")
                else observations_response
            )

            if ANALYZER_AVAILABLE:
                validation = validate_state_continuity(observations)
            else:
                validation = self._basic_state_validation(observations)

            # Generate patterns for state losses
            if validation.get("state_losses"):
                for loss in validation["state_losses"]:
                    signature = self.pattern_detector.generate_signature(
                        "state_continuity_loss",
                        lost_item=loss.get("lost_item"),
                        observation=loss.get("observation_name"),
                    )
                    loss["pattern_signature"] = signature

            validation_results.append({"trace_id": trace_id, "validation": validation})

        total_issues = sum(
            len(r["validation"].get("state_losses", []))
            + len(r["validation"].get("inconsistencies", []))
            + len(r["validation"].get("warnings", []))
            for r in validation_results
        )

        return {
            "status": "success",
            "traces_validated": len(validation_results),
            "total_issues": total_issues,
            "results": validation_results,
        }

    async def analyze_test_failure(
        self, session_id: str, return_patterns: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze test failure session with AI-optimized output

        Args:
            session_id: Test session ID to analyze
            return_patterns: Whether to detect and return patterns

        Returns:
            Comprehensive test failure analysis
        """
        if not ANALYZER_AVAILABLE:
            return {"error": "analyze_langfuse_traces module not available"}

        # Use the original function for comprehensive analysis
        analysis = analyze_test_failure(session_id, return_data=True)

        if analysis.get("error"):
            return analysis

        # Detect patterns in errors and interrupts
        if return_patterns:
            patterns = []

            # Pattern detection for errors
            for error in analysis.get("errors", []):
                signature = self.pattern_detector.generate_signature(
                    "test_error",
                    trace=error.get("trace"),
                    observation=error.get("observation"),
                )
                patterns.append(
                    {
                        "signature": signature,
                        "type": "test_error",
                        "confidence": 0.8,
                        "details": error,
                    }
                )

            # Pattern detection for interrupts
            for interrupt in analysis.get("interrupts", []):
                signature = self.pattern_detector.generate_signature(
                    "interrupt_pattern",
                    trace=interrupt.get("trace"),
                    observation=interrupt.get("observation"),
                )
                patterns.append(
                    {
                        "signature": signature,
                        "type": "interrupt",
                        "confidence": 0.9,
                        "details": interrupt,
                    }
                )

            analysis["patterns"] = patterns

            # Store patterns in memory
            if patterns and self.memory:
                for pattern in patterns:
                    await self._store_pattern_in_memory(pattern, "test_failures")

        return analysis

    async def detect_interrupt_patterns(
        self, hours_back: int = 1, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect interrupt patterns in traces

        Args:
            hours_back: Hours to look back
            session_id: Optional specific session

        Returns:
            Interrupt pattern analysis
        """
        if not self.client:
            return {"error": "Langfuse client not configured"}

        from_timestamp = datetime.now() - timedelta(hours=hours_back)

        traces = self.client.api.trace.list(
            from_timestamp=from_timestamp, session_id=session_id, limit=50
        ).data

        interrupt_patterns = []

        for trace in traces:
            observations_response = self.client.api.observations.get_many(
                trace_id=trace.id
            )
            observations = (
                observations_response.data
                if hasattr(observations_response, "data")
                else observations_response
            )

            for obs in observations if observations else []:
                # Check for interrupt patterns
                if self._is_interrupt_observation(obs):
                    signature = self.pattern_detector.generate_signature(
                        "interrupt", tool=obs.name, trace=trace.name
                    )

                    pattern = {
                        "signature": signature,
                        "trace_id": trace.id,
                        "observation_id": obs.id,
                        "tool": obs.name,
                        "timestamp": (
                            obs.start_time.isoformat() if obs.start_time else None
                        ),
                        "confidence": 0.95,
                    }

                    interrupt_patterns.append(pattern)

        # Store patterns
        if interrupt_patterns and self.memory:
            for pattern in interrupt_patterns:
                await self._store_pattern_in_memory(pattern, "interrupts")

        return {
            "status": "success",
            "hours_analyzed": hours_back,
            "traces_analyzed": len(traces),
            "interrupts_found": len(interrupt_patterns),
            "patterns": interrupt_patterns,
        }

    async def predict_trace_issues(
        self, trace_id: str, threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Predict potential issues based on historical patterns

        Args:
            trace_id: Trace to analyze
            threshold: Confidence threshold for predictions

        Returns:
            Predicted issues with confidence scores
        """
        if not self.client or not self.memory:
            return {"error": "Langfuse client or memory not configured"}

        # Get trace details
        trace_response = self.client.api.trace.get(trace_id)
        trace = (
            trace_response.data if hasattr(trace_response, "data") else trace_response
        )
        observations_response = self.client.api.observations.get_many(trace_id=trace_id)
        observations = (
            observations_response.data
            if hasattr(observations_response, "data")
            else observations_response
        )

        # Extract features from trace
        features = await self._extract_trace_features(trace, observations)

        # Search for similar patterns in memory
        predictions = []

        for feature_type, feature_value in features.items():
            # Search for patterns matching this feature
            similar_patterns = await self.memory.search_with_temporal_weight(
                f"langfuse_pattern {feature_type} {feature_value}",
                filter_source="langfuse_analyzer",
            )

            for pattern in similar_patterns:
                if pattern.score >= threshold:
                    predictions.append(
                        {
                            "issue_type": feature_type,
                            "pattern": pattern.metadata.get("signature"),
                            "confidence": pattern.score,
                            "resolution": pattern.metadata.get("resolution"),
                            "previous_occurrences": pattern.metadata.get(
                                "occurrences", 1
                            ),
                        }
                    )

        # Sort by confidence
        predictions.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "status": "success",
            "trace_id": trace_id,
            "predictions": predictions[:10],  # Top 10 predictions
            "high_confidence": len([p for p in predictions if p["confidence"] > 0.8]),
            "recommendation": predictions[0]["resolution"] if predictions else None,
        }

    # Helper methods

    async def _detect_trace_patterns(
        self, trace: Any, observations: List[Any]
    ) -> List[Dict[str, Any]]:
        """Detect patterns in a single trace"""
        patterns = []

        # Check for state loss patterns
        for i in range(1, len(observations)):
            curr_obs = observations[i]
            prev_obs = observations[i - 1]

            # Simple state loss detection
            if self._has_state_loss(prev_obs, curr_obs):
                signature = self.pattern_detector.generate_signature(
                    "state_loss", trace=trace.name
                )
                patterns.append(
                    {
                        "signature": signature,
                        "type": "state_loss",
                        "confidence": 0.85,
                        "trace_id": trace.id,
                    }
                )

        # Check for high latency
        if observations:
            for obs in observations:
                if obs.end_time and obs.start_time:
                    latency = (obs.end_time - obs.start_time).total_seconds()
                    if latency > 5:
                        signature = self.pattern_detector.generate_signature(
                            "high_latency", seconds=int(latency)
                        )
                        patterns.append(
                            {
                                "signature": signature,
                                "type": "high_latency",
                                "confidence": 0.9,
                                "trace_id": trace.id,
                                "latency": latency,
                            }
                        )

        return patterns

    def _check_for_interrupts(self, observations: List[Any]) -> bool:
        """Check if observations contain interrupt patterns"""
        for obs in observations:
            if self._is_interrupt_observation(obs):
                return True
        return False

    def _is_interrupt_observation(self, obs: Any) -> bool:
        """Check if an observation is an interrupt"""
        if obs.name and any(
            pattern in obs.name.lower()
            for pattern in ["check_in", "wait_for", "confirm_with", "interrupt"]
        ):
            return True

        if obs.output:
            output_str = str(obs.output)
            if "__interrupt__" in output_str:
                return True

        return False

    def _has_state_loss(self, prev_obs: Any, curr_obs: Any) -> bool:
        """Simple state loss detection between observations"""
        # This is a simplified version - the real implementation would be more sophisticated
        if not prev_obs.output or not curr_obs.output:
            return False

        # Check if state keys are missing
        if isinstance(prev_obs.output, dict) and isinstance(curr_obs.output, dict):
            prev_keys = set(prev_obs.output.keys())
            curr_keys = set(curr_obs.output.keys())

            # State loss if we had keys before but not now
            state_keys = {"tasks", "projects", "priorities", "state"}
            prev_state = prev_keys & state_keys
            curr_state = curr_keys & state_keys

            return len(prev_state) > len(curr_state)

        return False

    def _basic_phase_analysis(self, observations: List[Any]) -> List[Dict]:
        """Basic phase transition analysis when full analyzer not available"""
        transitions = []
        current_phase = None

        for obs in observations:
            # Try to extract phase from observation
            phase = None
            if obs.metadata and isinstance(obs.metadata, dict):
                phase = obs.metadata.get("phase") or obs.metadata.get("current_phase")

            if phase and phase != current_phase and current_phase:
                transitions.append(
                    {
                        "from_phase": current_phase,
                        "to_phase": phase,
                        "timestamp": (
                            obs.start_time.isoformat() if obs.start_time else None
                        ),
                    }
                )

            current_phase = phase

        return transitions

    def _basic_state_validation(self, observations: List[Any]) -> Dict:
        """Basic state validation when full analyzer not available"""
        validation = {"state_losses": [], "warnings": []}

        tracked_state = {}

        for obs in observations:
            if obs.output and isinstance(obs.output, dict):
                current_state = obs.output

                # Check for lost state
                for key in ["tasks", "projects", "priorities"]:
                    if key in tracked_state and key not in current_state:
                        validation["state_losses"].append(
                            {
                                "observation_id": obs.id,
                                "lost_item": key,
                                "observation_name": obs.name,
                            }
                        )

                tracked_state.update(current_state)

        return validation

    async def _extract_trace_features(
        self, trace: Any, observations: List[Any]
    ) -> Dict[str, str]:
        """Extract features from trace for pattern matching"""
        features = {}

        # Trace name pattern
        if trace.name:
            features["trace_type"] = (
                trace.name.split("-")[0] if "-" in trace.name else trace.name
            )

        # Check for interrupts
        has_interrupts = self._check_for_interrupts(observations)
        if has_interrupts:
            features["has_interrupts"] = "true"

        # Phase transitions
        transitions = self._basic_phase_analysis(observations)
        if transitions:
            features["has_transitions"] = "true"
            for trans in transitions:
                features[f"transition_{trans['from_phase']}_{trans['to_phase']}"] = (
                    "true"
                )

        # Latency patterns
        for obs in observations:
            if obs.end_time and obs.start_time:
                latency = (obs.end_time - obs.start_time).total_seconds()
                if latency > 5:
                    features["high_latency"] = "true"
                    break

        return features

    async def _store_pattern_in_memory(
        self, pattern: Dict[str, Any], project: Optional[str] = None
    ):
        """Store detected pattern in Graphiti memory"""
        if not self.memory:
            return

        memory_data = {
            "type": "langfuse_pattern",
            "title": f"Pattern: {pattern['signature']}",
            "signature": pattern["signature"],
            "pattern_type": pattern.get("type", "unknown"),
            "confidence": pattern.get("confidence", 0.5),
            "source": "langfuse_analyzer",
            "project": project or "unknown",
            "trace_ids": [pattern.get("trace_id")] if pattern.get("trace_id") else [],
            "timestamp": datetime.now().isoformat(),
            "details": pattern.get("details", {}),
            "resolution": pattern.get("resolution"),
        }

        # Check if pattern exists and update occurrence count
        existing = await self.memory.search_with_temporal_weight(
            f"langfuse_pattern signature:{pattern['signature']}",
            filter_source="langfuse_analyzer",
        )

        if existing:
            # Update occurrence count
            memory_data["occurrences"] = existing[0].metadata.get("occurrences", 1) + 1
            # Supersede old pattern
            await self.memory.supersede_memory(
                old_id=existing[0].uuid,
                new_content=memory_data,
                reason="Updated occurrence count",
            )
        else:
            memory_data["occurrences"] = 1
            await self.memory.add_memory(memory_data, source="langfuse_analyzer")


# Singleton instance
_analyzer_instance = None


async def get_langfuse_analyzer() -> LangfuseAnalyzer:
    """Get or create singleton LangfuseAnalyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = LangfuseAnalyzer()
        await _analyzer_instance.initialize()
    return _analyzer_instance
