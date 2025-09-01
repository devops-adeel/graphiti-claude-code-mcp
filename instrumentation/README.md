# Dual Observability Instrumentation

This package provides unified observability for the Graphiti MCP server, combining:
- **Langfuse**: LLM operation tracking (prompts, completions, costs)
- **OpenTelemetry**: Infrastructure monitoring (memory, latency, Neo4j queries)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                      │
│  ┌──────────────────┐        ┌──────────────────────┐   │
│  │ Langfuse @observe│        │ TracedNeo4jWrapper   │   │
│  │   (LLM Traces)   │        │  (Infrastructure)    │   │
│  └────────┬─────────┘        └──────────┬───────────┘   │
│           │                              │                │
│  ┌────────▼──────────────────────────────▼───────────┐  │
│  │         TraceCorrelationBridge                     │  │
│  │    (Links Langfuse trace IDs ←→ OTEL trace IDs)   │  │
│  └────────┬──────────────────────────────┬───────────┘  │
│           │                              │                │
└───────────┼──────────────────────────────┼────────────────┘
            │                              │
    ┌───────▼────────┐            ┌───────▼────────┐
    │    Langfuse    │            │  Grafana Alloy  │
    │   Cloud/Local  │            │  OTLP Receiver  │
    └────────────────┘            └─────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │     Tempo       │
                                  │ (Trace Storage) │
                                  └─────────────────┘
```

## Key Components

### 1. TraceCorrelationBridge (`trace_bridge.py`)
Correlates Langfuse and OpenTelemetry traces for unified observability.

```python
from instrumentation.trace_bridge import TraceCorrelationBridge

bridge = TraceCorrelationBridge("graphiti.mcp")

# Correlate with existing Langfuse trace
bridge.correlate_with_langfuse(
    langfuse_trace_id="lf-xxx",
    langfuse_session_id="session-yyy"
)

# Use dual tracing
with bridge.dual_trace("operation_name", langfuse_context) as span:
    # Your operation here
    pass
```

### 2. AdaptiveInfrastructureSampler (`adaptive_sampler.py`)
Dynamically adjusts sampling rate based on system conditions.

**Sampling triggers:**
- Memory pressure > 70%
- Operation latency > 5s
- Error conditions
- Cascade patterns detected

```python
from instrumentation.adaptive_sampler import AdaptiveInfrastructureSampler

sampler = AdaptiveInfrastructureSampler()

context = {
    "operation_name": "add_episode",
    "episode_size": 10000,
    "langfuse_error": False
}

if sampler.should_sample_infrastructure(context):
    # Create trace
    pass
```

### 3. CascadeDetector (`cascade_detector.py`)
Identifies memory cascade patterns where one slow operation triggers chain reactions.

**Cascade types:**
- `MEMORY_EXHAUSTION`: Progressive memory consumption
- `LATENCY_PROPAGATION`: Spreading slowness
- `SEMAPHORE_STARVATION`: Resource contention
- `BATCH_OVERFLOW`: Batch processing issues
- `LLM_TIMEOUT`: LLM response delays

```python
from instrumentation.cascade_detector import CascadeDetector

detector = CascadeDetector()

cascade = detector.record_event(
    operation="search",
    duration=8.5,
    memory_delta=250,
    memory_percent=75
)

if cascade and cascade.is_critical:
    # Trigger mitigation
    pass
```

### 4. TracedNeo4jGraphitiWrapper (`traced_wrapper.py`)
Enhanced wrapper with dual observability for Neo4j operations.

```python
from instrumentation.traced_wrapper import TracedNeo4jGraphitiWrapper

wrapper = TracedNeo4jGraphitiWrapper(
    uri="bolt://neo4j:7687",
    user="neo4j",
    password="password",
    otlp_endpoint="alloy.local:4317",
    enable_tracing=True
)

# Operations automatically traced
result = await wrapper.add_episode(episode_data)
```

### 5. Neo4jQueryCorrelator (`neo4j_correlation.py`)
Correlates Neo4j query logs with OpenTelemetry traces.

```python
from instrumentation.neo4j_correlation import Neo4jQueryCorrelator

correlator = Neo4jQueryCorrelator()

# Find queries related to a trace
queries = correlator.correlate_with_trace(
    trace_id="otel-trace-123",
    timestamp=datetime.utcnow(),
    operation="search"
)

# Get optimization suggestions
suggestions = correlator.suggest_optimizations(query_pattern)
```

## Configuration

### Environment Variables

```bash
# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy.local:4317
OTEL_SERVICE_NAME=graphiti.mcp
OTEL_INSTRUMENTATION_ENABLED=true

# Adaptive Sampling
INFRASTRUCTURE_BASE_SAMPLE_RATE=0.1      # 10% baseline
INFRASTRUCTURE_MAX_SAMPLE_RATE=1.0       # 100% maximum
MEMORY_PRESSURE_THRESHOLD=70             # Trigger at 70% memory
LATENCY_THRESHOLD_SECONDS=5.0            # Slow operation threshold
CASCADE_WINDOW_SECONDS=60                 # Cascade detection window
```

### Docker Compose Integration

The `docker-compose.yml` has been updated with:
- OTEL environment variables
- Neo4j query log volume mount
- Memory monitoring configuration

## Grafana Dashboard

A unified dashboard (`graphiti-dual-observability.json`) provides:

### Overview Metrics
- MCP Tool Success Rate
- Memory Pressure Gauge
- Cascade Events Counter
- Adaptive Sampling Rate

### Episode Processing
- Recent episode traces from Tempo
- Operation latency percentiles (p50, p95)

### Memory Cascade Detection
- Memory pressure timeline
- Cascade pattern visualization
- Pattern type distribution

### Neo4j Correlation
- Slowest queries table
- Neo4j query rate

### Langfuse Metrics
- LLM token usage rate
- Response latency percentiles

## Usage Patterns

### 1. Basic Integration

```python
# In your MCP server
from instrumentation.traced_wrapper import TracedNeo4jGraphitiWrapper

# Replace standard wrapper
wrapper = TracedNeo4jGraphitiWrapper(
    uri=NEO4J_URI,
    user=NEO4J_USER,
    password=NEO4J_PASSWORD
)

# Use normally - tracing happens automatically
@observe()  # Langfuse decorator
async def search_memory(query: str):
    # Infrastructure traced automatically
    results = await wrapper.search(query)
    return results
```

### 2. Manual Correlation

```python
from instrumentation.trace_bridge import TraceCorrelationBridge

bridge = TraceCorrelationBridge()

# In your Langfuse-decorated function
@observe()
async def process_episode(episode):
    # Get Langfuse context
    langfuse_context = {
        "trace_id": get_current_langfuse_trace_id(),
        "session_id": get_current_session_id()
    }

    # Correlate with infrastructure tracing
    with bridge.dual_trace("process_episode", langfuse_context):
        # Your processing logic
        pass
```

### 3. Cascade Monitoring

```python
from instrumentation.cascade_detector import CascadeDetector

detector = CascadeDetector()

# In your operation loop
async def process_batch(items):
    start = time.time()
    memory_before = get_memory_usage()

    try:
        result = await process_items(items)
    finally:
        duration = time.time() - start
        memory_after = get_memory_usage()

        cascade = detector.record_event(
            operation="batch_process",
            duration=duration,
            memory_delta=memory_after - memory_before,
            memory_percent=get_memory_percent()
        )

        if cascade and cascade.is_critical:
            # Reduce batch size
            # Trigger garbage collection
            # Alert operators
            pass
```

## Troubleshooting

### Missing Traces
1. Check OTEL_INSTRUMENTATION_ENABLED=true
2. Verify Alloy receiver is running: `curl http://alloy.local:4318/v1/traces`
3. Check sampling rate isn't too low

### Memory Pressure Not Detected
1. Verify psutil is installed: `pip install psutil`
2. Check MEMORY_PRESSURE_THRESHOLD (default 70%)
3. Monitor with: `docker stats graphiti-claude-code-mcp`

### Cascade False Positives
1. Adjust CASCADE_WINDOW_SECONDS (default 60)
2. Increase min_events_for_cascade (default 3)
3. Review cascade_detector.get_cascade_history()

### Neo4j Queries Not Correlating
1. Ensure query.log is mounted in container
2. Check Neo4j slow query threshold (>100ms)
3. Verify correlation window (default 5s)

## Performance Impact

- **Baseline overhead**: <2% CPU, <10MB memory
- **During cascade**: Up to 100% sampling, +5% CPU
- **Trace storage**: ~1KB per trace
- **Query correlation**: <1ms per query

## Testing

Run integration tests:

```bash
pytest tests/test_dual_tracing.py -v
```

Test cascade detection:

```python
# Simulate memory pressure
for i in range(5):
    context = {
        "operation_name": f"heavy_op_{i}",
        "episode_size": 100000,
        "start_time": time.time()
    }
    sampler.should_sample_infrastructure(context)
    time.sleep(0.5)

# Check escalation
stats = sampler.get_sampling_stats()
assert stats["escalation_level"] > 0
```

## Metrics Reference

### Prometheus Metrics
- `graphiti_operation_duration_seconds`: Operation latency histogram
- `graphiti_cascade_patterns_total`: Cascade events counter
- `graphiti_adaptive_sampling_rate`: Current sampling rate gauge
- `graphiti_memory_pressure_percent`: Memory usage percentage

### Trace Attributes
- `langfuse.trace_id`: Langfuse trace identifier
- `graphiti.operation`: Operation name
- `graphiti.memory_delta_mb`: Memory change during operation
- `graphiti.duration_seconds`: Operation duration
- `graphiti.cascade_active`: Cascade condition flag

## Contributing

When adding new instrumentation:

1. Extend `TracedNeo4jGraphitiWrapper` for new operations
2. Add cascade patterns to `CascadeDetector`
3. Update Grafana dashboard for new metrics
4. Add tests to `test_dual_tracing.py`
5. Document environment variables

## License

Part of the Graphiti Claude Code MCP project.
