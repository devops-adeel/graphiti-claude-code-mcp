"""
Integration tests for dual observability tracing.

Tests the correlation between Langfuse and OpenTelemetry traces,
adaptive sampling, and cascade detection.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instrumentation.trace_bridge import TraceCorrelationBridge
from instrumentation.adaptive_sampler import AdaptiveInfrastructureSampler
from instrumentation.cascade_detector import CascadeDetector, CascadeType
from instrumentation.traced_wrapper import TracedNeo4jGraphitiWrapper
from instrumentation.neo4j_correlation import Neo4jQueryCorrelator


class TestTraceCorrelationBridge:
    """Test trace correlation between Langfuse and OpenTelemetry."""

    @pytest.fixture
    def bridge(self):
        """Create trace bridge instance."""
        return TraceCorrelationBridge(service_name="test.service")

    def test_correlate_with_langfuse(self, bridge):
        """Test adding Langfuse correlation to OpenTelemetry span."""
        with bridge.tracer.start_as_current_span("test_span") as span:
            bridge.correlate_with_langfuse(
                langfuse_trace_id="lf-trace-123",
                langfuse_span_id="lf-span-456",
                langfuse_session_id="lf-session-789",
            )

            # Verify attributes were set
            assert span.attributes.get("langfuse.trace_id") == "lf-trace-123"
            assert span.attributes.get("langfuse.span_id") == "lf-span-456"
            assert span.attributes.get("langfuse.session_id") == "lf-session-789"
            assert span.attributes.get("correlation.type") == "langfuse-otel"

    def test_dual_trace_context_manager(self, bridge):
        """Test dual trace context manager."""
        langfuse_context = {
            "trace_id": "lf-trace-abc",
            "span_id": "lf-span-def",
            "session_id": "lf-session-ghi",
        }

        with bridge.dual_trace("test_operation", langfuse_context) as span:
            assert span is not None
            assert span.is_recording()
            assert span.attributes.get("trace.dual") == True
            assert span.attributes.get("trace.operation") == "test_operation"
            assert span.attributes.get("langfuse.trace_id") == "lf-trace-abc"

    def test_create_trace_link(self, bridge):
        """Test creating bidirectional trace link."""
        link = bridge.create_trace_link(
            otel_trace_id="otel-trace-123", langfuse_trace_id="lf-trace-456"
        )

        assert link["otel_trace_id"] == "otel-trace-123"
        assert link["langfuse_trace_id"] == "lf-trace-456"
        assert link["correlation_id"] == "otel-tra-lf-trace"
        assert link["service"] == "test.service"
        assert "timestamp" in link


class TestAdaptiveInfrastructureSampler:
    """Test adaptive sampling based on system conditions."""

    @pytest.fixture
    def sampler(self):
        """Create sampler instance."""
        return AdaptiveInfrastructureSampler()

    def test_always_sample_errors(self, sampler):
        """Test that errors are always sampled."""
        context = {
            "operation_name": "test_op",
            "langfuse_error": True,
            "episode_size": 100,
        }

        assert sampler.should_sample_infrastructure(context) == True
        assert sampler.metrics.error_triggered == 1

    @patch("instrumentation.adaptive_sampler.psutil")
    def test_memory_pressure_sampling(self, mock_psutil, sampler):
        """Test sampling under memory pressure."""
        # Mock high memory usage
        mock_memory = Mock()
        mock_memory.percent = 75  # Above threshold
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 500  # 500MB
        mock_psutil.Process.return_value = mock_process

        context = {"operation_name": "test_op", "episode_size": 100}

        assert sampler.should_sample_infrastructure(context) == True
        assert sampler.metrics.memory_triggered == 1

    def test_cascade_detection(self, sampler):
        """Test cascade pattern detection."""
        # Simulate multiple slow operations
        for i in range(4):
            sampler.recent_operations.append(
                {
                    "timestamp": datetime.utcnow(),
                    "operation": f"op_{i}",
                    "duration": 6.0,  # Slow operation
                    "memory_delta": 150,  # Memory increase
                }
            )

        context = {"operation_name": "test_op", "episode_size": 100}

        assert sampler._detect_cascade_pattern(context) == True
        assert sampler.metrics.cascade_triggered == 1

    def test_adaptive_rate_adjustment(self, sampler):
        """Test adaptive sampling rate changes."""
        initial_rate = sampler._get_adaptive_rate()

        # Trigger escalation
        sampler._escalate_sampling("test_reason")
        escalated_rate = sampler._get_adaptive_rate()

        assert escalated_rate > initial_rate
        assert sampler.escalation_level == 1

        # Test decay
        sampler.last_escalation = datetime.utcnow() - timedelta(minutes=2)
        sampler._decay_escalation()

        assert sampler.escalation_level == 0

    def test_sampling_statistics(self, sampler):
        """Test sampling statistics tracking."""
        # Simulate some sampling decisions
        for i in range(10):
            context = {
                "operation_name": f"op_{i}",
                "episode_size": 100,
                "error": i == 5,  # One error
            }
            sampler.should_sample_infrastructure(context)

        stats = sampler.get_sampling_stats()

        assert stats["metrics"]["total_decisions"] == 10
        assert stats["metrics"]["error_triggered"] == 1
        assert "current_rate" in stats
        assert "escalation_level" in stats


class TestCascadeDetector:
    """Test memory cascade pattern detection."""

    @pytest.fixture
    def detector(self):
        """Create cascade detector instance."""
        return CascadeDetector(window_seconds=60, min_events_for_cascade=3)

    def test_cascade_event_recording(self, detector):
        """Test recording cascade events."""
        cascade = detector.record_event(
            operation="test_op",
            duration=7.0,
            memory_delta=200,
            memory_percent=75,
            trace_id="trace-123",
        )

        # First event shouldn't trigger cascade
        assert cascade is None
        assert len(detector.recent_events) == 1

    def test_cascade_pattern_detection(self, detector):
        """Test detecting cascade patterns."""
        # Record multiple problematic events
        for i in range(4):
            cascade = detector.record_event(
                operation=f"op_{i}",
                duration=6.0 + i,  # Increasing latency
                memory_delta=100 + i * 50,  # Increasing memory
                memory_percent=70 + i * 3,
                trace_id=f"trace-{i}",
            )

        # Should detect cascade after enough events
        assert cascade is not None
        assert cascade.cascade_type in [
            CascadeType.MEMORY_EXHAUSTION,
            CascadeType.LATENCY_PROPAGATION,
        ]
        assert len(cascade.events) >= 3
        assert cascade.total_memory_impact > 0
        assert cascade.max_latency > 6.0

    def test_cascade_severity_scoring(self, detector):
        """Test cascade severity calculation."""
        # Create severe cascade
        for i in range(5):
            detector.record_event(
                operation="heavy_op",
                duration=12.0,  # Very slow
                memory_delta=600,  # High memory
                memory_percent=85,  # High pressure
                error="Timeout error",
            )

        active = detector.get_active_cascades()
        if active:
            cascade = active[0]
            assert cascade.is_critical == True
            assert cascade.severity_score > 5.0

    def test_cascade_mitigation_suggestions(self, detector):
        """Test mitigation strategy suggestions."""
        # Create memory exhaustion cascade
        for i in range(3):
            detector.record_event(
                operation="memory_op",
                duration=3.0,
                memory_delta=300,
                memory_percent=80 + i * 2,
            )

        active = detector.get_active_cascades()
        if active:
            cascade = active[0]
            suggestions = detector._suggest_mitigation(cascade)

            assert len(suggestions) > 0
            assert any("memory" in s.lower() for s in suggestions)

    def test_cascade_risk_prediction(self, detector):
        """Test cascade risk prediction."""
        metrics = {"memory_percent": 75, "avg_latency": 4.0, "error_rate": 0.15}

        risk_score, predicted_type = detector.predict_cascade_risk(metrics)

        assert 0 <= risk_score <= 1.0
        assert risk_score > 0.3  # Should indicate some risk
        assert predicted_type is not None


class TestTracedNeo4jGraphitiWrapper:
    """Test traced wrapper integration."""

    @pytest.fixture
    async def wrapper(self):
        """Create traced wrapper instance."""
        # Mock the parent class initialization
        with patch("instrumentation.traced_wrapper.Neo4jGraphitiWrapper.__init__"):
            wrapper = TracedNeo4jGraphitiWrapper(
                otlp_endpoint="localhost:4317",
                service_name="test.graphiti",
                enable_tracing=True,
            )
            # Mock required attributes
            wrapper.batch_size = 5
            wrapper.max_concurrent_batches = 3
            wrapper.semaphore = asyncio.Semaphore(3)
            return wrapper

    @pytest.mark.asyncio
    async def test_traced_operation(self, wrapper):
        """Test tracing an operation."""
        # Mock parent method
        wrapper.add_episode = AsyncMock(return_value={"status": "success"})

        with patch.object(wrapper, "_should_trace", return_value=True):
            async with wrapper._trace_operation(
                "test_operation", episode_size=1000
            ) as span:
                assert span is not None
                # Verify attributes are set
                assert "graphiti.operation" in span.attributes
                assert "graphiti.batch_size" in span.attributes

    @pytest.mark.asyncio
    async def test_cascade_flagging(self, wrapper):
        """Test cascade condition flagging."""
        wrapper._flag_cascade_condition("slow_op", 10.0, 200.0)

        assert wrapper.cascade_active == True
        assert wrapper.last_cascade_time is not None

        # Test auto-clear (mock the sleep)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await wrapper._clear_cascade_flag()
            assert wrapper.cascade_active == False

    @pytest.mark.asyncio
    async def test_memory_pressure_info(self, wrapper):
        """Test getting memory pressure information."""
        pressure_info = await wrapper.get_memory_pressure()

        assert "timestamp" in pressure_info
        assert "memory_metrics" in pressure_info
        assert "cascade_active" in pressure_info
        assert "sampling_stats" in pressure_info

    @pytest.mark.asyncio
    async def test_instrumentation_stats(self, wrapper):
        """Test getting instrumentation statistics."""
        stats = wrapper.get_instrumentation_stats()

        assert stats["tracing_enabled"] == True
        assert "cascade_active" in stats
        assert "sampling" in stats
        assert "memory" in stats


class TestNeo4jQueryCorrelator:
    """Test Neo4j query log correlation."""

    @pytest.fixture
    def correlator(self):
        """Create query correlator instance."""
        return Neo4jQueryCorrelator(
            log_file_path="/tmp/test_query.log", correlation_window_seconds=5
        )

    def test_parse_query_log_line(self, correlator):
        """Test parsing Neo4j query log lines."""
        log_line = (
            "2024-01-15 10:30:45.123+0000 INFO  Query completed successfully "
            "database=neo4j txId=tx-123-456 runtime=150 "
            "query=MATCH (n:Node) WHERE n.name = 'test' RETURN n "
            "planning=10 cpu=140 allocatedBytes=1048576 pageHits=100 pageFaults=2"
        )

        query = correlator.parse_query_log_line(log_line)

        assert query is not None
        assert query.database == "neo4j"
        assert query.transaction_id == "tx-123-456"
        assert query.duration_ms == 150
        assert query.planning_time_ms == 10
        assert query.cpu_time_ms == 140
        assert query.memory_bytes == 1048576
        assert query.is_slow == True

    def test_query_pattern_extraction(self, correlator):
        """Test extracting query patterns."""
        query1 = "MATCH (n:Node) WHERE n.id = 123 RETURN n"
        query2 = "MATCH (n:Node) WHERE n.id = 456 RETURN n"

        pattern1 = correlator._extract_query_pattern(query1)
        pattern2 = correlator._extract_query_pattern(query2)

        # Should produce same pattern
        assert pattern1 == pattern2
        assert "?" in pattern1  # Numbers replaced

    def test_trace_correlation(self, correlator):
        """Test correlating queries with traces."""
        # Add some test queries
        now = datetime.utcnow()
        test_query = type(
            "obj",
            (object,),
            {
                "timestamp": now,
                "query": "MATCH (n) RETURN n",
                "duration_ms": 200,
                "database": "neo4j",
                "transaction_id": "tx-test-123",
                "memory_bytes": None,
            },
        )()

        correlator.recent_queries.append(test_query)

        # Correlate with trace
        correlated = correlator.correlate_with_trace(
            trace_id="trace-abc",
            timestamp=now + timedelta(seconds=1),
            operation="search",
        )

        assert len(correlated) == 1
        assert correlated[0].transaction_id == "tx-test-123"

    def test_optimization_suggestions(self, correlator):
        """Test query optimization suggestions."""
        pattern = "MATCH (a:Node), (b:Node) COLLECT(a) AS nodes RETURN nodes, b.*"

        suggestions = correlator.suggest_optimizations(pattern)

        assert len(suggestions) > 0
        assert any("cartesian" in s.lower() for s in suggestions)
        assert any("collect" in s.lower() for s in suggestions)
        assert any("*" in s for s in suggestions)


@pytest.mark.asyncio
async def test_end_to_end_integration():
    """Test end-to-end integration of all components."""
    # Create all components
    bridge = TraceCorrelationBridge("test.integration")
    sampler = AdaptiveInfrastructureSampler()
    detector = CascadeDetector()
    correlator = Neo4jQueryCorrelator()

    # Simulate a problematic operation
    with bridge.dual_trace("integration_test") as span:
        # Record high latency operation
        cascade = detector.record_event(
            operation="integration_op",
            duration=8.0,
            memory_delta=300,
            memory_percent=75,
            trace_id=format(span.get_span_context().trace_id, "032x"),
        )

        # Check sampling decision
        context = {
            "operation_name": "integration_op",
            "episode_size": 5000,
            "start_time": time.time(),
        }
        should_sample = sampler.should_sample_infrastructure(context)

        # Verify components work together
        assert span is not None
        assert should_sample == True  # Should sample due to cascade

        # Record result for adaptive learning
        sampler.record_operation_result(context, 8.0, 1000, 1300)

    # Verify statistics
    sampler_stats = sampler.get_sampling_stats()
    cascade_stats = detector.get_cascade_statistics()

    assert sampler_stats["metrics"]["total_decisions"] > 0
    assert cascade_stats["active_cascades"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
