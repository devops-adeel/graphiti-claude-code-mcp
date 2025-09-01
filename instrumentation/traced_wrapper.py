"""
Traced wrapper for Neo4jGraphitiWrapper with dual observability.

Integrates OpenTelemetry infrastructure tracing with existing Langfuse LLM tracing,
providing unified observability for the entire episode processing pipeline.
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from contextlib import asynccontextmanager

try:
    import psutil
except ImportError:
    psutil = None

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from neo4j_graphiti_wrapper import Neo4jGraphitiWrapper
from .trace_bridge import TraceCorrelationBridge
from .adaptive_sampler import AdaptiveInfrastructureSampler

logger = logging.getLogger(__name__)


class TracedNeo4jGraphitiWrapper(Neo4jGraphitiWrapper):
    """
    Enhanced Neo4jGraphitiWrapper with dual-layer observability.

    Adds infrastructure tracing to complement existing Langfuse LLM tracing,
    with adaptive sampling based on memory pressure and cascade detection.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize traced wrapper with observability components.

        Accepts all Neo4jGraphitiWrapper arguments plus:
        - otlp_endpoint: OTLP collector endpoint (default: alloy.local:4317)
        - service_name: Service name for traces (default: graphiti.mcp)
        - enable_tracing: Whether to enable tracing (default: True)
        """
        # Extract tracing configuration
        self.otlp_endpoint = kwargs.pop("otlp_endpoint", "alloy.local:4317")
        self.service_name = kwargs.pop("service_name", "graphiti.mcp")
        self.enable_tracing = kwargs.pop("enable_tracing", True)

        # Initialize parent wrapper
        super().__init__(*args, **kwargs)

        # Initialize observability components
        if self.enable_tracing:
            self._setup_tracing()
            self.trace_bridge = TraceCorrelationBridge(self.service_name)
            self.sampler = AdaptiveInfrastructureSampler()
        else:
            self.trace_bridge = None
            self.sampler = None

        # Track cascade detection state
        self.cascade_active = False
        self.last_cascade_time = None

        logger.info(
            f"TracedNeo4jGraphitiWrapper initialized: "
            f"tracing={'enabled' if self.enable_tracing else 'disabled'}, "
            f"endpoint={self.otlp_endpoint}"
        )

    def _setup_tracing(self):
        """Configure OpenTelemetry tracing."""
        # Create resource with service information
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: self.service_name,
                ResourceAttributes.SERVICE_VERSION: "1.0.0",
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: "development",
            }
        )

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=self.otlp_endpoint,
            insecure=True,  # For local development
        )

        # Setup tracer provider
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(processor)

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer for this module
        self.tracer = trace.get_tracer(__name__, "1.0.0")

    def _get_memory_metrics(self) -> Dict[str, float]:
        """Get current memory metrics."""
        if not psutil:
            return {}

        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()

            return {
                "process_memory_mb": memory_info.rss / 1024 / 1024,
                "process_memory_percent": process.memory_percent(),
                "system_memory_percent": system_memory.percent,
                "available_memory_gb": system_memory.available / 1024 / 1024 / 1024,
            }
        except Exception as e:
            logger.error(f"Error getting memory metrics: {e}")
            return {}

    def _should_trace(self, operation: str, context: Dict[str, Any]) -> bool:
        """
        Determine if operation should be traced based on sampling.

        Args:
            operation: Name of the operation
            context: Operation context for sampling decision

        Returns:
            Boolean indicating whether to trace
        """
        if not self.enable_tracing or not self.sampler:
            return False

        # Add memory metrics to context
        context.update(self._get_memory_metrics())

        # Check for cascade pattern
        if self.cascade_active:
            context["cascade_active"] = True

        # Let sampler decide
        return self.sampler.should_sample_infrastructure(context)

    @asynccontextmanager
    async def _trace_operation(
        self,
        operation_name: str,
        langfuse_context: Optional[Dict[str, Any]] = None,
        **attributes,
    ):
        """
        Trace an operation with dual observability.

        Args:
            operation_name: Name of the operation
            langfuse_context: Optional Langfuse trace context
            **attributes: Additional span attributes
        """
        if not self.enable_tracing:
            yield None
            return

        # Prepare context for sampling decision
        context = {
            "operation_name": operation_name,
            "start_time": time.time(),
            "episode_size": attributes.get("episode_size", 0),
            "langfuse_error": attributes.get("error", False),
        }

        # Check if we should trace
        if not self._should_trace(operation_name, context):
            yield None
            return

        # Get memory before operation
        memory_before = self._get_memory_metrics().get("process_memory_mb", 0)

        # Start dual trace
        with self.trace_bridge.dual_trace(
            operation_name, langfuse_context=langfuse_context, attributes=attributes
        ) as span:
            try:
                # Add infrastructure attributes
                span.set_attribute("graphiti.operation", operation_name)
                span.set_attribute("graphiti.memory_before_mb", memory_before)

                # Add semaphore state if available
                if hasattr(self, "semaphore"):
                    span.set_attribute(
                        "graphiti.semaphore_available",
                        (
                            self.semaphore._value
                            if hasattr(self.semaphore, "_value")
                            else 0
                        ),
                    )

                # Add batch configuration
                span.set_attribute("graphiti.batch_size", self.batch_size)
                span.set_attribute(
                    "graphiti.max_concurrent", self.max_concurrent_batches
                )

                yield span

            finally:
                # Record operation result
                duration = time.time() - context["start_time"]
                memory_after = self._get_memory_metrics().get("process_memory_mb", 0)
                memory_delta = memory_after - memory_before

                # Update span with results
                span.set_attribute("graphiti.duration_seconds", duration)
                span.set_attribute("graphiti.memory_after_mb", memory_after)
                span.set_attribute("graphiti.memory_delta_mb", memory_delta)

                # Record in sampler for adaptive learning
                if self.sampler:
                    self.sampler.record_operation_result(
                        context, duration, memory_before, memory_after
                    )

                # Check for cascade condition
                if memory_delta > 100 or duration > 5:
                    self._flag_cascade_condition(operation_name, duration, memory_delta)

    def _flag_cascade_condition(
        self, operation: str, duration: float, memory_delta: float
    ):
        """Flag potential cascade condition."""
        self.cascade_active = True
        self.last_cascade_time = datetime.utcnow()

        logger.warning(
            f"Cascade condition detected in {operation}: "
            f"duration={duration:.2f}s, memory_delta={memory_delta:.1f}MB"
        )

        # Auto-clear cascade flag after 60 seconds
        asyncio.create_task(self._clear_cascade_flag())

    async def _clear_cascade_flag(self):
        """Clear cascade flag after timeout."""
        await asyncio.sleep(60)
        self.cascade_active = False
        logger.info("Cascade condition cleared")

    # Override key methods with tracing

    async def add_episode(
        self,
        episode_data: Dict[str, Any],
        langfuse_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add episode with dual tracing.

        Args:
            episode_data: Episode data to add
            langfuse_context: Optional Langfuse trace context

        Returns:
            Result from parent add_episode
        """
        attributes = {
            "episode_size": len(str(episode_data)),
            "episode_type": episode_data.get("type", "unknown"),
        }

        async with self._trace_operation("add_episode", langfuse_context, **attributes):
            return await super().add_episode(episode_data)

    async def search(
        self, query: str, langfuse_context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search with dual tracing.

        Args:
            query: Search query
            langfuse_context: Optional Langfuse trace context
            **kwargs: Additional search parameters

        Returns:
            Search results from parent search
        """
        attributes = {
            "query_length": len(query),
            "search_type": kwargs.get("type", "default"),
        }

        async with self._trace_operation(
            "search", langfuse_context, **attributes
        ) as span:
            results = await super().search(query, **kwargs)

            if span:
                span.set_attribute("graphiti.result_count", len(results))

            return results

    async def get_memory_pressure(self) -> Dict[str, Any]:
        """
        Get current memory pressure metrics.

        Returns:
            Dictionary with memory pressure information
        """
        metrics = self._get_memory_metrics()

        pressure_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "memory_metrics": metrics,
            "cascade_active": self.cascade_active,
        }

        if self.sampler:
            pressure_info["sampling_stats"] = self.sampler.get_sampling_stats()

        return pressure_info

    async def get_trace_correlation(
        self, trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get trace correlation information.

        Args:
            trace_id: Optional specific trace ID to look up

        Returns:
            Correlation information between Langfuse and OpenTelemetry
        """
        if not self.trace_bridge:
            return {"error": "Tracing not enabled"}

        current_context = self.trace_bridge.extract_langfuse_context()

        correlation = {
            "current_langfuse_context": current_context,
            "service_name": self.service_name,
            "otlp_endpoint": self.otlp_endpoint,
        }

        # Get current OpenTelemetry trace if active
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            correlation["otel_trace_id"] = format(span_context.trace_id, "032x")
            correlation["otel_span_id"] = format(span_context.span_id, "016x")

            # Create correlation link if both systems have traces
            if current_context.get("trace_id"):
                correlation["trace_link"] = self.trace_bridge.create_trace_link(
                    correlation["otel_trace_id"], current_context["trace_id"]
                )

        return correlation

    def get_instrumentation_stats(self) -> Dict[str, Any]:
        """
        Get instrumentation statistics.

        Returns:
            Statistics about the instrumentation layer
        """
        stats = {
            "tracing_enabled": self.enable_tracing,
            "cascade_active": self.cascade_active,
            "last_cascade_time": (
                self.last_cascade_time.isoformat() if self.last_cascade_time else None
            ),
        }

        if self.sampler:
            stats["sampling"] = self.sampler.get_sampling_stats()

        stats["memory"] = self._get_memory_metrics()

        return stats
