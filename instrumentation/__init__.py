"""
OpenTelemetry instrumentation for Graphiti MCP Server.

This package provides complementary tracing to existing Langfuse integration:
- Langfuse: Tracks LLM operations (prompts, completions, costs)
- OpenTelemetry: Tracks infrastructure (memory, latency, Neo4j queries)

The two systems are correlated via trace IDs for unified observability.
"""

from .trace_bridge import TraceCorrelationBridge
from .adaptive_sampler import AdaptiveInfrastructureSampler
from .cascade_detector import CascadeDetector
from .traced_wrapper import TracedNeo4jGraphitiWrapper

__all__ = [
    "TraceCorrelationBridge",
    "AdaptiveInfrastructureSampler",
    "CascadeDetector",
    "TracedNeo4jGraphitiWrapper",
]
