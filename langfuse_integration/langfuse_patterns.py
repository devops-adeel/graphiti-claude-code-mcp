#!/usr/bin/env python3
"""
Pattern Detection and Signature Generation for Langfuse Traces
Generates unique signatures for detected patterns to enable cross-project learning
"""

import re
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of patterns that can be detected in Langfuse traces"""

    STATE_LOSS = "state_loss"
    INTERRUPT = "interrupt"
    HIGH_LATENCY = "high_latency"
    TOKEN_OVERFLOW = "token_overflow"
    LOW_MEMORY_RELEVANCE = "low_memory_relevance"
    PROMPT_MISSING_VARS = "prompt_missing_vars"
    PHASE_TRANSITION = "phase_transition"
    TEST_ERROR = "test_error"
    STATE_CONTINUITY_LOSS = "state_continuity_loss"
    CONVERSATION_FLOW = "conversation_flow"
    SCORE_DEGRADATION = "score_degradation"


class PatternDetector:
    """
    Detects and generates signatures for patterns in Langfuse traces
    """

    def __init__(self):
        """Initialize pattern detector with signature templates"""
        self.signature_templates = {
            PatternType.STATE_LOSS: "state_loss_{from_phase}_to_{to_phase}",
            PatternType.INTERRUPT: "interrupt_{tool}_{context}",
            PatternType.HIGH_LATENCY: "high_latency_{model}_{seconds}s",
            PatternType.TOKEN_OVERFLOW: "token_overflow_{model}_{tokens}",
            PatternType.LOW_MEMORY_RELEVANCE: "low_relevance_memory_{score}",
            PatternType.PROMPT_MISSING_VARS: "prompt_missing_{variables}",
            PatternType.PHASE_TRANSITION: "transition_{from_phase}_{to_phase}",
            PatternType.TEST_ERROR: "test_error_{trace}_{observation}",
            PatternType.STATE_CONTINUITY_LOSS: "continuity_loss_{lost_item}_{observation}",
            PatternType.CONVERSATION_FLOW: "conversation_{pattern}_{tool}",
            PatternType.SCORE_DEGRADATION: "score_degraded_{name}_{value}",
        }

        self.pattern_cache = {}
        self.confidence_thresholds = {
            PatternType.STATE_LOSS: 0.85,
            PatternType.INTERRUPT: 0.95,
            PatternType.HIGH_LATENCY: 0.90,
            PatternType.TOKEN_OVERFLOW: 0.95,
            PatternType.LOW_MEMORY_RELEVANCE: 0.70,
            PatternType.PROMPT_MISSING_VARS: 0.80,
            PatternType.PHASE_TRANSITION: 0.75,
            PatternType.TEST_ERROR: 0.85,
            PatternType.STATE_CONTINUITY_LOSS: 0.90,
            PatternType.CONVERSATION_FLOW: 0.70,
            PatternType.SCORE_DEGRADATION: 0.80,
        }

    def generate_signature(self, pattern_type: str, **kwargs) -> str:
        """
        Generate a unique signature for a detected pattern

        Args:
            pattern_type: Type of pattern (from PatternType enum or string)
            **kwargs: Pattern-specific parameters

        Returns:
            Unique pattern signature
        """
        # Convert string to PatternType if needed
        if isinstance(pattern_type, str):
            try:
                pattern_enum = PatternType(pattern_type)
            except ValueError:
                # Handle custom pattern types
                pattern_enum = None
                template = "{pattern_type}_{hash}"
        else:
            pattern_enum = pattern_type

        # Get template for this pattern type
        if pattern_enum and pattern_enum in self.signature_templates:
            template = self.signature_templates[pattern_enum]
        else:
            template = "{pattern_type}_{hash}"

        # Clean and normalize parameters
        cleaned_params = self._clean_parameters(kwargs)

        # Generate signature
        try:
            if "{hash}" in template:
                # Use hash for complex patterns
                param_str = "_".join(
                    f"{k}={v}" for k, v in sorted(cleaned_params.items())
                )
                hash_val = hashlib.md5(param_str.encode()).hexdigest()[:8]
                signature = template.format(pattern_type=pattern_type, hash=hash_val)
            else:
                # Use template substitution
                signature = template.format(**cleaned_params)
        except KeyError as e:
            # Fallback to hash-based signature
            logger.warning(f"Missing parameter for signature template: {e}")
            param_str = "_".join(f"{k}={v}" for k, v in sorted(cleaned_params.items()))
            hash_val = hashlib.md5(param_str.encode()).hexdigest()[:8]
            signature = f"{pattern_type}_{hash_val}"

        # Normalize signature
        signature = self._normalize_signature(signature)

        return signature

    def detect_patterns_in_trace(
        self, trace: Dict[str, Any], observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect all patterns in a trace

        Args:
            trace: Trace data
            observations: List of observations in the trace

        Returns:
            List of detected patterns with signatures and confidence
        """
        patterns = []

        # Check for state loss patterns
        state_losses = self._detect_state_loss(observations)
        patterns.extend(state_losses)

        # Check for interrupt patterns
        interrupts = self._detect_interrupts(observations)
        patterns.extend(interrupts)

        # Check for latency issues
        latency_issues = self._detect_high_latency(observations)
        patterns.extend(latency_issues)

        # Check for token overflow
        token_issues = self._detect_token_overflow(observations)
        patterns.extend(token_issues)

        # Check for memory relevance issues
        memory_issues = self._detect_memory_relevance(observations)
        patterns.extend(memory_issues)

        # Check for score degradation
        score_issues = self._detect_score_degradation(trace, observations)
        patterns.extend(score_issues)

        return patterns

    def calculate_confidence(
        self, pattern_type: PatternType, evidence: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for a detected pattern

        Args:
            pattern_type: Type of pattern
            evidence: Evidence supporting the pattern

        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = self.confidence_thresholds.get(pattern_type, 0.5)

        # Adjust based on evidence strength
        adjustments = 0.0

        # Multiple occurrences increase confidence
        if evidence.get("occurrences", 1) > 1:
            adjustments += min(0.1 * evidence["occurrences"], 0.2)

        # Consistent across observations
        if evidence.get("consistent", False):
            adjustments += 0.1

        # Has clear indicators
        if evidence.get("clear_indicators", False):
            adjustments += 0.15

        # Cross-project validation
        if evidence.get("cross_project", False):
            adjustments += 0.1

        # Historical precedent
        if evidence.get("historical_match", False):
            adjustments += 0.1

        return min(base_confidence + adjustments, 1.0)

    def get_resolution_suggestion(
        self, pattern_type: PatternType, pattern_details: Dict[str, Any]
    ) -> Optional[str]:
        """
        Get resolution suggestion for a detected pattern

        Args:
            pattern_type: Type of pattern
            pattern_details: Details about the pattern

        Returns:
            Suggested resolution or None
        """
        resolutions = {
            PatternType.STATE_LOSS: "Ensure state variables are passed between phases: {tasks}, {projects}, {priorities}",
            PatternType.INTERRUPT: "Review interrupt logic in {tool} - consider adjusting trigger conditions",
            PatternType.HIGH_LATENCY: "Optimize {model} generation - consider streaming or smaller context",
            PatternType.TOKEN_OVERFLOW: "Reduce context size or use a model with larger context window",
            PatternType.LOW_MEMORY_RELEVANCE: "Adjust memory retrieval threshold or improve embedding quality",
            PatternType.PROMPT_MISSING_VARS: "Add missing variables to prompt template: {variables}",
            PatternType.PHASE_TRANSITION: "Review phase transition logic between {from_phase} and {to_phase}",
            PatternType.TEST_ERROR: "Debug test failure in {trace} at {observation}",
            PatternType.STATE_CONTINUITY_LOSS: "Implement state persistence for {lost_item}",
            PatternType.CONVERSATION_FLOW: "Review conversation flow pattern in {tool}",
            PatternType.SCORE_DEGRADATION: "Investigate score degradation for {name} metric",
        }

        resolution_template = resolutions.get(pattern_type)
        if resolution_template:
            try:
                return resolution_template.format(**pattern_details)
            except KeyError:
                return resolution_template

        return None

    # Pattern detection methods

    def _detect_state_loss(
        self, observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect state loss patterns in observations"""
        patterns = []
        state_keys = {"tasks", "projects", "priorities", "state", "context"}

        for i in range(1, len(observations)):
            prev_obs = observations[i - 1]
            curr_obs = observations[i]

            # Check for state loss
            if self._has_output(prev_obs) and self._has_output(curr_obs):
                prev_state = set(prev_obs.get("output", {}).keys()) & state_keys
                curr_state = set(curr_obs.get("output", {}).keys()) & state_keys

                if prev_state and not curr_state:
                    # State was lost
                    from_phase = self._extract_phase(prev_obs)
                    to_phase = self._extract_phase(curr_obs)

                    signature = self.generate_signature(
                        PatternType.STATE_LOSS.value,
                        from_phase=from_phase,
                        to_phase=to_phase,
                    )

                    patterns.append(
                        {
                            "type": PatternType.STATE_LOSS.value,
                            "signature": signature,
                            "confidence": self.calculate_confidence(
                                PatternType.STATE_LOSS, {"clear_indicators": True}
                            ),
                            "details": {
                                "from_phase": from_phase,
                                "to_phase": to_phase,
                                "lost_keys": list(prev_state - curr_state),
                            },
                            "resolution": self.get_resolution_suggestion(
                                PatternType.STATE_LOSS,
                                {"from_phase": from_phase, "to_phase": to_phase},
                            ),
                        }
                    )

        return patterns

    def _detect_interrupts(
        self, observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect interrupt patterns"""
        patterns = []
        interrupt_indicators = [
            "check_in",
            "wait_for",
            "confirm",
            "interrupt",
            "__interrupt__",
        ]

        for obs in observations:
            obs_name = obs.get("name", "").lower()

            # Check for interrupt patterns
            for indicator in interrupt_indicators:
                if indicator in obs_name or (
                    obs.get("output") and indicator in str(obs.get("output"))
                ):
                    tool = obs.get("name", "unknown")
                    context = self._extract_context(obs)

                    signature = self.generate_signature(
                        PatternType.INTERRUPT.value,
                        tool=self._clean_tool_name(tool),
                        context=context,
                    )

                    patterns.append(
                        {
                            "type": PatternType.INTERRUPT.value,
                            "signature": signature,
                            "confidence": self.calculate_confidence(
                                PatternType.INTERRUPT, {"clear_indicators": True}
                            ),
                            "details": {
                                "tool": tool,
                                "context": context,
                                "observation_id": obs.get("id"),
                            },
                            "resolution": self.get_resolution_suggestion(
                                PatternType.INTERRUPT, {"tool": tool}
                            ),
                        }
                    )
                    break

        return patterns

    def _detect_high_latency(
        self, observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect high latency patterns"""
        patterns = []
        latency_threshold = 5.0  # seconds

        for obs in observations:
            start_time = obs.get("start_time")
            end_time = obs.get("end_time")

            if start_time and end_time:
                # Calculate latency
                if isinstance(start_time, str):
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                else:
                    start_dt = start_time

                if isinstance(end_time, str):
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                else:
                    end_dt = end_time

                latency = (end_dt - start_dt).total_seconds()

                if latency > latency_threshold:
                    model = self._extract_model(obs)

                    signature = self.generate_signature(
                        PatternType.HIGH_LATENCY.value,
                        model=model,
                        seconds=int(latency),
                    )

                    patterns.append(
                        {
                            "type": PatternType.HIGH_LATENCY.value,
                            "signature": signature,
                            "confidence": self.calculate_confidence(
                                PatternType.HIGH_LATENCY, {"clear_indicators": True}
                            ),
                            "details": {
                                "model": model,
                                "latency": latency,
                                "observation_id": obs.get("id"),
                            },
                            "resolution": self.get_resolution_suggestion(
                                PatternType.HIGH_LATENCY, {"model": model}
                            ),
                        }
                    )

        return patterns

    def _detect_token_overflow(
        self, observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect token overflow patterns"""
        patterns = []
        token_limits = {
            "gpt-3.5": 4096,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "claude": 100000,
        }

        for obs in observations:
            # Check for token-related errors
            output = obs.get("output", {})
            error_msg = str(output) if output else ""

            if "token" in error_msg.lower() and any(
                word in error_msg.lower()
                for word in ["limit", "exceeded", "overflow", "maximum"]
            ):
                model = self._extract_model(obs)
                tokens = self._extract_token_count(obs)

                signature = self.generate_signature(
                    PatternType.TOKEN_OVERFLOW.value, model=model, tokens=tokens
                )

                patterns.append(
                    {
                        "type": PatternType.TOKEN_OVERFLOW.value,
                        "signature": signature,
                        "confidence": self.calculate_confidence(
                            PatternType.TOKEN_OVERFLOW, {"clear_indicators": True}
                        ),
                        "details": {
                            "model": model,
                            "tokens": tokens,
                            "limit": token_limits.get(model, "unknown"),
                        },
                        "resolution": self.get_resolution_suggestion(
                            PatternType.TOKEN_OVERFLOW, {}
                        ),
                    }
                )

        return patterns

    def _detect_memory_relevance(
        self, observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect low memory relevance patterns"""
        patterns = []
        relevance_threshold = 0.5

        for obs in observations:
            # Check for memory-related observations
            if "memory" in obs.get("name", "").lower():
                metadata = obs.get("metadata", {})
                relevance = metadata.get("relevance_score", 1.0)

                if relevance < relevance_threshold:
                    score_str = f"{relevance:.1f}".replace(".", "_")

                    signature = self.generate_signature(
                        PatternType.LOW_MEMORY_RELEVANCE.value, score=score_str
                    )

                    patterns.append(
                        {
                            "type": PatternType.LOW_MEMORY_RELEVANCE.value,
                            "signature": signature,
                            "confidence": self.calculate_confidence(
                                PatternType.LOW_MEMORY_RELEVANCE,
                                {"clear_indicators": True},
                            ),
                            "details": {
                                "relevance_score": relevance,
                                "observation_id": obs.get("id"),
                            },
                            "resolution": self.get_resolution_suggestion(
                                PatternType.LOW_MEMORY_RELEVANCE, {}
                            ),
                        }
                    )

        return patterns

    def _detect_score_degradation(
        self, trace: Dict[str, Any], observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect score degradation patterns"""
        patterns = []
        degradation_threshold = 0.5

        # Check trace scores
        scores = trace.get("scores", [])
        for score in scores:
            if score.get("value", 1.0) < degradation_threshold:
                name = score.get("name", "unknown")
                value = f"{score.get('value', 0):.1f}".replace(".", "_")

                signature = self.generate_signature(
                    PatternType.SCORE_DEGRADATION.value,
                    name=self._clean_name(name),
                    value=value,
                )

                patterns.append(
                    {
                        "type": PatternType.SCORE_DEGRADATION.value,
                        "signature": signature,
                        "confidence": self.calculate_confidence(
                            PatternType.SCORE_DEGRADATION, {"clear_indicators": True}
                        ),
                        "details": {
                            "score_name": name,
                            "score_value": score.get("value"),
                            "trace_id": trace.get("id"),
                        },
                        "resolution": self.get_resolution_suggestion(
                            PatternType.SCORE_DEGRADATION, {"name": name}
                        ),
                    }
                )

        return patterns

    # Helper methods

    def _clean_parameters(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Clean and normalize parameters for signature generation"""
        cleaned = {}

        for key, value in params.items():
            if value is None:
                cleaned[key] = "none"
            elif isinstance(value, bool):
                cleaned[key] = str(value).lower()
            elif isinstance(value, (int, float)):
                cleaned[key] = str(value)
            else:
                # Clean string values
                cleaned_val = str(value).lower()
                cleaned_val = re.sub(r"[^a-z0-9_]", "_", cleaned_val)
                cleaned_val = re.sub(r"_+", "_", cleaned_val).strip("_")
                cleaned[key] = cleaned_val[:30]  # Limit length

        return cleaned

    def _normalize_signature(self, signature: str) -> str:
        """Normalize signature for consistency"""
        # Convert to lowercase
        signature = signature.lower()

        # Replace multiple underscores with single
        signature = re.sub(r"_+", "_", signature)

        # Remove leading/trailing underscores
        signature = signature.strip("_")

        # Limit length
        if len(signature) > 100:
            # Hash if too long
            hash_val = hashlib.md5(signature.encode()).hexdigest()[:8]
            signature = f"{signature[:60]}_{hash_val}"

        return signature

    def _has_output(self, obs: Dict[str, Any]) -> bool:
        """Check if observation has output"""
        return bool(obs.get("output"))

    def _extract_phase(self, obs: Dict[str, Any]) -> str:
        """Extract phase from observation"""
        metadata = obs.get("metadata", {})
        phase = metadata.get("phase") or metadata.get("current_phase")

        if not phase and obs.get("name"):
            # Try to infer from name
            name = obs["name"].lower()
            if "planning" in name:
                phase = "planning"
            elif "review" in name:
                phase = "review"
            elif "capture" in name:
                phase = "capture"
            else:
                phase = "unknown"

        return phase or "unknown"

    def _extract_context(self, obs: Dict[str, Any]) -> str:
        """Extract context from observation"""
        # Try to determine context from observation
        name = obs.get("name", "").lower()

        if "test" in name:
            return "test"
        elif "debug" in name:
            return "debug"
        elif "review" in name:
            return "review"
        elif "capture" in name:
            return "capture"
        else:
            return "general"

    def _extract_model(self, obs: Dict[str, Any]) -> str:
        """Extract model name from observation"""
        metadata = obs.get("metadata", {})
        model = metadata.get("model")

        if not model and obs.get("input"):
            # Try to extract from input
            input_data = obs["input"]
            if isinstance(input_data, dict):
                model = input_data.get("model")

        if not model:
            # Try to infer from observation name
            name = obs.get("name", "").lower()
            if "gpt" in name:
                model = "gpt"
            elif "claude" in name:
                model = "claude"
            else:
                model = "unknown"

        return self._clean_model_name(model)

    def _extract_token_count(self, obs: Dict[str, Any]) -> int:
        """Extract token count from observation"""
        # Try various locations for token count
        metadata = obs.get("metadata", {})
        tokens = metadata.get("tokens") or metadata.get("token_count")

        if not tokens and obs.get("output"):
            output = obs["output"]
            if isinstance(output, dict):
                tokens = output.get("usage", {}).get("total_tokens")

        return tokens or 0

    def _clean_tool_name(self, tool: str) -> str:
        """Clean tool name for signature"""
        tool = tool.lower()
        tool = re.sub(r"[^a-z0-9_]", "_", tool)
        tool = re.sub(r"_+", "_", tool).strip("_")
        return tool[:20]  # Limit length

    def _clean_name(self, name: str) -> str:
        """Clean generic name for signature"""
        name = name.lower()
        name = re.sub(r"[^a-z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name).strip("_")
        return name[:30]  # Limit length

    def _clean_model_name(self, model: str) -> str:
        """Clean and standardize model name"""
        if not model:
            return "unknown"

        model = model.lower()

        # Standardize common model names
        if "gpt-4" in model:
            if "turbo" in model:
                return "gpt4_turbo"
            return "gpt4"
        elif "gpt-3" in model:
            return "gpt3"
        elif "claude" in model:
            return "claude"
        elif "llama" in model:
            return "llama"
        else:
            # Clean for signature
            model = re.sub(r"[^a-z0-9_]", "_", model)
            model = re.sub(r"_+", "_", model).strip("_")
            return model[:15]
