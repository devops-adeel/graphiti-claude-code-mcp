#!/usr/bin/env python3
"""
Unified Observability Module
Implements W3C Trace Context correlation between Langfuse and OpenTelemetry
Based on Grafana-OrbStack patterns
"""

import os
import time
import logging
import functools
import asyncio
from typing import Optional, Dict, Any, Callable, TypeVar
from contextlib import contextmanager
from dataclasses import dataclass

from langfuse import Langfuse, observe

# OpenTelemetry imports (optional - graceful degradation if not available)
try:
    from opentelemetry import trace, baggage, context
    from opentelemetry.propagate import inject, extract
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(
        "OpenTelemetry not available. Only Langfuse tracking will be active."
    )

logger = logging.getLogger(__name__)

# Type hints
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class UnifiedTraceContext:
    """
    Unified trace context following W3C Trace Context standard
    Enables correlation between Langfuse and OpenTelemetry/Tempo
    """

    trace_id: str  # W3C format: 32 hex chars
    span_id: Optional[str] = None  # W3C format: 16 hex chars
    langfuse_trace_id: Optional[str] = None
    langfuse_observation_id: Optional[str] = None
    parent_context: Optional[Dict[str, str]] = None

    def to_w3c_headers(self) -> Dict[str, str]:
        """Convert to W3C Trace Context headers for propagation"""
        headers = {}

        if OTEL_AVAILABLE:
            inject(headers)  # Inject current OTel context

        # Add custom headers for Langfuse correlation
        if self.langfuse_trace_id:
            headers["X-Langfuse-Trace-Id"] = self.langfuse_trace_id
        if self.langfuse_observation_id:
            headers["X-Langfuse-Observation-Id"] = self.langfuse_observation_id

        # Add standard W3C headers if OTel not available
        if not OTEL_AVAILABLE and self.trace_id:
            headers["traceparent"] = f"00-{self.trace_id}-{self.span_id or '0'*16}-01"

        return headers

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "UnifiedTraceContext":
        """Extract trace context from W3C headers"""
        if OTEL_AVAILABLE:
            ctx = extract(headers)
            context.attach(ctx)

            span = trace.get_current_span()
            span_context = span.get_span_context()

            return cls(
                trace_id=format(span_context.trace_id, "032x"),
                span_id=format(span_context.span_id, "016x"),
                langfuse_trace_id=headers.get("X-Langfuse-Trace-Id"),
                langfuse_observation_id=headers.get("X-Langfuse-Observation-Id"),
                parent_context=headers,
            )
        else:
            # Parse W3C traceparent header manually
            traceparent = headers.get("traceparent", "")
            if traceparent:
                parts = traceparent.split("-")
                if len(parts) >= 4:
                    return cls(
                        trace_id=parts[1],
                        span_id=parts[2],
                        langfuse_trace_id=headers.get("X-Langfuse-Trace-Id"),
                        langfuse_observation_id=headers.get(
                            "X-Langfuse-Observation-Id"
                        ),
                        parent_context=headers,
                    )

            # Generate new trace ID if none provided
            import uuid

            return cls(
                trace_id=uuid.uuid4().hex,
                langfuse_trace_id=headers.get("X-Langfuse-Trace-Id"),
                parent_context=headers,
            )


class UnifiedObservability:
    """
    Unified observability system combining Langfuse and OpenTelemetry
    Implements patterns from Grafana-OrbStack for complete AI observability
    """

    def __init__(self):
        """Initialize unified observability"""
        # Initialize Langfuse (mandatory)
        self.langfuse = self._init_langfuse()

        # Initialize OpenTelemetry (optional)
        self.tracer = None
        if OTEL_AVAILABLE:
            self.tracer = self._init_opentelemetry()

        # Track active contexts for correlation
        self.active_contexts: Dict[str, UnifiedTraceContext] = {}

    def _init_langfuse(self) -> Langfuse:
        """Initialize Langfuse client with 1Password credentials"""
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not public_key or not secret_key:
            raise ValueError(
                "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are REQUIRED. "
                "Run with: op run --env-file=secrets/.env.1password"
            )

        return Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    def _init_opentelemetry(self):
        """Initialize OpenTelemetry tracer if available"""
        if not OTEL_AVAILABLE:
            return None

        # Create resource
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: "graphiti-mcp",
                ResourceAttributes.SERVICE_VERSION: "1.0.0",
                "deployment.environment": "orbstack",
                "mcp.server.type": "graphiti",
            }
        )

        # Set up tracing
        provider = TracerProvider(resource=resource)

        # Add OTLP exporter if configured
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        if otlp_endpoint:
            processor = BatchSpanProcessor(
                OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            )
            provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        return trace.get_tracer("graphiti-mcp")

    def get_current_context(self) -> UnifiedTraceContext:
        """Get current unified trace context"""
        if OTEL_AVAILABLE and self.tracer:
            span = trace.get_current_span()
            span_context = span.get_span_context()

            # Get Langfuse IDs from baggage
            langfuse_trace_id = baggage.get_baggage("langfuse_trace_id")
            langfuse_obs_id = baggage.get_baggage("langfuse_observation_id")

            return UnifiedTraceContext(
                trace_id=format(span_context.trace_id, "032x"),
                span_id=format(span_context.span_id, "016x"),
                langfuse_trace_id=langfuse_trace_id,
                langfuse_observation_id=langfuse_obs_id,
            )
        else:
            # Fallback to UUID-based trace ID
            import uuid

            return UnifiedTraceContext(
                trace_id=uuid.uuid4().hex,
                langfuse_trace_id=self.langfuse.get_current_trace_id(),
            )

    @contextmanager
    def unified_trace(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for unified tracing across both systems
        Creates correlated traces in both Langfuse and OpenTelemetry
        """
        # Start OpenTelemetry span if available
        otel_span = None
        if OTEL_AVAILABLE and self.tracer:
            otel_span = self.tracer.start_as_current_span(name)
            otel_span.__enter__()

            # Get OTel trace ID for correlation
            span_context = otel_span.span.get_span_context()
            otel_trace_id = format(span_context.trace_id, "032x")
        else:
            otel_trace_id = None

        # Create Langfuse trace with OTel correlation
        langfuse_metadata = metadata or {}
        if otel_trace_id:
            langfuse_metadata["tempo_trace_id"] = otel_trace_id
            langfuse_metadata["grafana_explore_url"] = (
                f"http://grafana.local/explore?traceID={otel_trace_id}"
            )

        # Store correlation in baggage for propagation
        if OTEL_AVAILABLE:
            # Note: Langfuse doesn't expose trace ID synchronously, would need async handling
            pass

        try:
            yield self.get_current_context()
        finally:
            # Clean up OTel span
            if otel_span:
                otel_span.__exit__(None, None, None)

    def create_unified_score(
        self,
        name: str,
        value: float,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Create a score in Langfuse with OpenTelemetry correlation
        """
        # Get current context if no trace_id provided
        if not trace_id:
            ctx = self.get_current_context()
            trace_id = ctx.langfuse_trace_id or ctx.trace_id

        # Add OTel correlation to metadata
        unified_metadata = metadata or {}
        if OTEL_AVAILABLE:
            span = trace.get_current_span()
            if span:
                span_context = span.get_span_context()
                unified_metadata["otel_trace_id"] = format(
                    span_context.trace_id, "032x"
                )
                unified_metadata["otel_span_id"] = format(span_context.span_id, "016x")

        # Create score in Langfuse
        self.langfuse.create_score(
            trace_id=trace_id,
            name=name,
            value=value,
            data_type="NUMERIC",
            metadata=unified_metadata,
        )

        # Also record in OTel span if available
        if OTEL_AVAILABLE:
            span = trace.get_current_span()
            if span:
                span.set_attribute(f"score.{name}", value)
                span.add_event(
                    f"Score recorded: {name}",
                    {"score_value": value, "langfuse_trace_id": trace_id},
                )


def unified_observe(name: Optional[str] = None):
    """
    Decorator for unified observability across Langfuse and OpenTelemetry
    Combines @observe from Langfuse with OpenTelemetry span creation
    """

    def decorator(func: F) -> F:
        # Apply Langfuse observe
        langfuse_wrapped = observe(name=name or func.__name__)(func)

        if not OTEL_AVAILABLE:
            return langfuse_wrapped

        # Add OpenTelemetry instrumentation
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(langfuse_wrapped)
            async def async_wrapper(*args, **kwargs):
                tracer = trace.get_tracer("graphiti-mcp")
                with tracer.start_as_current_span(name or func.__name__) as span:
                    # Add function parameters as span attributes
                    span.set_attributes(
                        {
                            f"param.{k}": str(v)[:100]  # Limit attribute size
                            for k, v in kwargs.items()
                        }
                    )

                    try:
                        result = await langfuse_wrapped(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return async_wrapper
        else:

            @functools.wraps(langfuse_wrapped)
            def sync_wrapper(*args, **kwargs):
                tracer = trace.get_tracer("graphiti-mcp")
                with tracer.start_as_current_span(name or func.__name__) as span:
                    # Add function parameters as span attributes
                    span.set_attributes(
                        {f"param.{k}": str(v)[:100] for k, v in kwargs.items()}
                    )

                    try:
                        result = langfuse_wrapped(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return sync_wrapper

    return decorator


# Singleton instance
_unified_instance: Optional[UnifiedObservability] = None


def get_unified_observability() -> UnifiedObservability:
    """Get or create singleton UnifiedObservability instance"""
    global _unified_instance

    if _unified_instance is None:
        _unified_instance = UnifiedObservability()

    return _unified_instance


# Export convenience functions
__all__ = [
    "UnifiedTraceContext",
    "UnifiedObservability",
    "unified_observe",
    "get_unified_observability",
]
