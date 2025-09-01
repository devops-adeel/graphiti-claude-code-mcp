"""
Trace Correlation Bridge for dual observability.

Correlates Langfuse LLM traces with OpenTelemetry infrastructure traces,
enabling unified observability across both systems.
"""

import logging
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any
from datetime import datetime

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


class TraceCorrelationBridge:
    """
    Bridges Langfuse and OpenTelemetry tracing systems.

    This enables correlation between:
    - Langfuse: LLM operations (prompts, completions, costs)
    - OpenTelemetry: Infrastructure operations (memory, latency, queries)
    """

    def __init__(self, service_name: str = "graphiti.mcp"):
        """
        Initialize the trace correlation bridge.

        Args:
            service_name: The service name for OpenTelemetry traces
        """
        self.tracer = trace.get_tracer(service_name, "1.0.0")
        self.propagator = TraceContextTextMapPropagator()
        self.service_name = service_name

    def correlate_with_langfuse(
        self,
        langfuse_trace_id: Optional[str] = None,
        langfuse_span_id: Optional[str] = None,
        langfuse_session_id: Optional[str] = None,
    ) -> None:
        """
        Add Langfuse identifiers to current OpenTelemetry span.

        Args:
            langfuse_trace_id: The Langfuse trace ID
            langfuse_span_id: The Langfuse span ID
            langfuse_session_id: The Langfuse session ID
        """
        span = trace.get_current_span()
        if not span or not span.is_recording():
            return

        # Add Langfuse correlation attributes
        if langfuse_trace_id:
            span.set_attribute("langfuse.trace_id", langfuse_trace_id)
            span.set_attribute("correlation.type", "langfuse-otel")

        if langfuse_span_id:
            span.set_attribute("langfuse.span_id", langfuse_span_id)

        if langfuse_session_id:
            span.set_attribute("langfuse.session_id", langfuse_session_id)

        # Add correlation metadata
        span.set_attribute("correlation.timestamp", datetime.utcnow().isoformat())
        span.set_attribute("correlation.service", self.service_name)

    def extract_langfuse_context(self) -> Dict[str, Optional[str]]:
        """
        Extract Langfuse context from environment or current context.

        Returns:
            Dictionary with Langfuse trace information
        """
        # Try to get from environment (if Langfuse sets these)
        context = {
            "trace_id": os.getenv("LANGFUSE_TRACE_ID"),
            "span_id": os.getenv("LANGFUSE_SPAN_ID"),
            "session_id": os.getenv("LANGFUSE_SESSION_ID"),
        }

        # Try to extract from current span attributes
        span = trace.get_current_span()
        if span and span.is_recording():
            # Check if we already have Langfuse context in span
            for key, value in span.attributes.items():
                if key.startswith("langfuse."):
                    context_key = key.replace("langfuse.", "")
                    context[context_key] = value

        return context

    @contextmanager
    def dual_trace(
        self,
        operation_name: str,
        langfuse_context: Optional[Dict[str, Any]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Create correlated spans in both Langfuse and OpenTelemetry.

        Args:
            operation_name: Name of the operation being traced
            langfuse_context: Optional Langfuse context to correlate
            attributes: Additional attributes to add to the span

        Yields:
            The OpenTelemetry span for additional instrumentation
        """
        # Start OpenTelemetry span
        with self.tracer.start_as_current_span(operation_name) as span:
            try:
                # Add dual-trace marker
                span.set_attribute("trace.dual", True)
                span.set_attribute("trace.operation", operation_name)

                # Correlate with Langfuse if context provided
                if langfuse_context:
                    self.correlate_with_langfuse(
                        langfuse_trace_id=langfuse_context.get("trace_id"),
                        langfuse_span_id=langfuse_context.get("span_id"),
                        langfuse_session_id=langfuse_context.get("session_id"),
                    )

                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        # OpenTelemetry has restrictions on attribute types
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(key, value)
                        else:
                            span.set_attribute(key, str(value))

                yield span

                # Mark successful completion
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                # Mark span as error
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def create_trace_link(
        self, otel_trace_id: str, langfuse_trace_id: str
    ) -> Dict[str, str]:
        """
        Create a bidirectional link between traces.

        Args:
            otel_trace_id: OpenTelemetry trace ID
            langfuse_trace_id: Langfuse trace ID

        Returns:
            Link metadata dictionary
        """
        link = {
            "otel_trace_id": otel_trace_id,
            "langfuse_trace_id": langfuse_trace_id,
            "correlation_id": f"{otel_trace_id[:8]}-{langfuse_trace_id[:8]}",
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
        }

        # Log the correlation for debugging
        logger.debug(f"Created trace correlation: {link['correlation_id']}")

        return link

    def propagate_context(self, carrier: Dict[str, str]) -> None:
        """
        Inject current trace context into carrier for propagation.

        Args:
            carrier: Dictionary to inject trace context into
        """
        self.propagator.inject(carrier)

        # Also add Langfuse context if available
        langfuse_context = self.extract_langfuse_context()
        if langfuse_context.get("trace_id"):
            carrier["langfuse-trace-id"] = langfuse_context["trace_id"]
        if langfuse_context.get("session_id"):
            carrier["langfuse-session-id"] = langfuse_context["session_id"]

    def extract_context(self, carrier: Dict[str, str]) -> None:
        """
        Extract trace context from carrier and set as current.

        Args:
            carrier: Dictionary containing trace context
        """
        # Extract OpenTelemetry context
        ctx = self.propagator.extract(carrier)

        # Set as current context
        token = trace.use_context(ctx)

        # Extract and correlate Langfuse context if present
        if "langfuse-trace-id" in carrier:
            self.correlate_with_langfuse(
                langfuse_trace_id=carrier["langfuse-trace-id"],
                langfuse_session_id=carrier.get("langfuse-session-id"),
            )

        return token
