"""
Neo4j query log correlation for dual observability.

Parses Neo4j query logs and correlates them with OpenTelemetry traces,
enabling unified debugging across the entire data pipeline.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Neo4jQuery:
    """Parsed Neo4j query with metadata."""

    timestamp: datetime
    query: str
    duration_ms: float
    database: str
    transaction_id: Optional[str] = None
    planning_time_ms: Optional[float] = None
    waiting_time_ms: Optional[float] = None
    cpu_time_ms: Optional[float] = None
    memory_bytes: Optional[int] = None
    page_hits: Optional[int] = None
    page_faults: Optional[int] = None

    @property
    def is_slow(self) -> bool:
        """Check if query is slow (>100ms as configured)."""
        return self.duration_ms > 100

    @property
    def is_memory_intensive(self) -> bool:
        """Check if query is memory intensive."""
        return self.memory_bytes and self.memory_bytes > 100_000_000  # 100MB


class Neo4jQueryCorrelator:
    """
    Correlates Neo4j query logs with OpenTelemetry traces.

    Enables correlation between:
    - Neo4j transaction IDs and trace IDs
    - Query patterns and performance issues
    - Memory usage and cascade events
    """

    # Neo4j query log pattern (based on Neo4j 5.x format)
    QUERY_LOG_PATTERN = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\+\d{4} "
        r".*?database=(?P<database>\w+).*?"
        r"(?:txId=(?P<tx_id>[a-z0-9-]+))?.*?"
        r"runtime=(?P<duration>\d+).*?"
        r"query=(?P<query>.*?)(?:\s+planning=|$)"
    )

    # Additional metrics pattern
    METRICS_PATTERN = re.compile(
        r"planning=(?P<planning>\d+)|"
        r"waiting=(?P<waiting>\d+)|"
        r"cpu=(?P<cpu>\d+)|"
        r"allocatedBytes=(?P<memory>\d+)|"
        r"pageHits=(?P<page_hits>\d+)|"
        r"pageFaults=(?P<page_faults>\d+)"
    )

    def __init__(
        self, log_file_path: Optional[str] = None, correlation_window_seconds: int = 5
    ):
        """
        Initialize Neo4j query correlator.

        Args:
            log_file_path: Path to Neo4j query.log file
            correlation_window_seconds: Time window for correlation
        """
        self.log_file_path = log_file_path or "/var/lib/neo4j/logs/query.log"
        self.correlation_window = timedelta(seconds=correlation_window_seconds)

        # Query tracking
        self.recent_queries: List[Neo4jQuery] = []
        self.query_patterns: Dict[str, List[Neo4jQuery]] = defaultdict(list)
        self.trace_correlations: Dict[str, List[str]] = defaultdict(list)

        # Performance analysis
        self.slow_query_patterns: Dict[str, int] = defaultdict(int)
        self.memory_intensive_patterns: Dict[str, int] = defaultdict(int)

        logger.info(
            f"Neo4jQueryCorrelator initialized: log_file={log_file_path}, "
            f"correlation_window={correlation_window_seconds}s"
        )

    def parse_query_log_line(self, line: str) -> Optional[Neo4jQuery]:
        """
        Parse a single Neo4j query log line.

        Args:
            line: Log line to parse

        Returns:
            Parsed Neo4jQuery or None
        """
        # Match main query pattern
        match = self.QUERY_LOG_PATTERN.search(line)
        if not match:
            return None

        # Extract base fields
        timestamp_str = match.group("timestamp")
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")

        query = Neo4jQuery(
            timestamp=timestamp,
            query=match.group("query").strip(),
            duration_ms=float(match.group("duration")),
            database=match.group("database"),
            transaction_id=match.group("tx_id"),
        )

        # Extract additional metrics
        for metrics_match in self.METRICS_PATTERN.finditer(line):
            if metrics_match.group("planning"):
                query.planning_time_ms = float(metrics_match.group("planning"))
            if metrics_match.group("waiting"):
                query.waiting_time_ms = float(metrics_match.group("waiting"))
            if metrics_match.group("cpu"):
                query.cpu_time_ms = float(metrics_match.group("cpu"))
            if metrics_match.group("memory"):
                query.memory_bytes = int(metrics_match.group("memory"))
            if metrics_match.group("page_hits"):
                query.page_hits = int(metrics_match.group("page_hits"))
            if metrics_match.group("page_faults"):
                query.page_faults = int(metrics_match.group("page_faults"))

        return query

    async def tail_query_log(self, callback=None):
        """
        Tail Neo4j query log for real-time correlation.

        Args:
            callback: Optional callback for each parsed query
        """
        try:
            # Open log file
            with open(self.log_file_path, "r") as f:
                # Move to end of file
                f.seek(0, 2)

                while True:
                    line = f.readline()
                    if line:
                        query = self.parse_query_log_line(line)
                        if query:
                            self._track_query(query)
                            if callback:
                                await callback(query)
                    else:
                        await asyncio.sleep(0.1)

        except FileNotFoundError:
            logger.error(f"Neo4j query log not found: {self.log_file_path}")
        except Exception as e:
            logger.error(f"Error tailing query log: {e}")

    def _track_query(self, query: Neo4jQuery):
        """Track query for correlation and analysis."""
        # Add to recent queries
        self.recent_queries.append(query)

        # Limit recent queries to last 1000
        if len(self.recent_queries) > 1000:
            self.recent_queries = self.recent_queries[-1000:]

        # Track query pattern
        pattern = self._extract_query_pattern(query.query)
        self.query_patterns[pattern].append(query)

        # Track slow queries
        if query.is_slow:
            self.slow_query_patterns[pattern] += 1

        # Track memory intensive queries
        if query.is_memory_intensive:
            self.memory_intensive_patterns[pattern] += 1

    def _extract_query_pattern(self, query: str) -> str:
        """
        Extract query pattern for grouping similar queries.

        Args:
            query: Cypher query string

        Returns:
            Query pattern with literals removed
        """
        # Remove string literals
        pattern = re.sub(r"'[^']*'", "'?'", query)
        pattern = re.sub(r'"[^"]*"', '"?"', pattern)

        # Remove numeric literals
        pattern = re.sub(r"\b\d+\b", "?", pattern)

        # Remove whitespace variations
        pattern = " ".join(pattern.split())

        # Truncate to reasonable length
        if len(pattern) > 200:
            pattern = pattern[:200] + "..."

        return pattern

    def correlate_with_trace(
        self, trace_id: str, timestamp: datetime, operation: str
    ) -> List[Neo4jQuery]:
        """
        Find Neo4j queries that correlate with a trace.

        Args:
            trace_id: OpenTelemetry trace ID
            timestamp: Operation timestamp
            operation: Operation name

        Returns:
            List of correlated Neo4j queries
        """
        correlated = []

        # Time-based correlation
        window_start = timestamp - self.correlation_window
        window_end = timestamp + self.correlation_window

        for query in self.recent_queries:
            if window_start <= query.timestamp <= window_end:
                correlated.append(query)

                # Track correlation
                if query.transaction_id:
                    self.trace_correlations[trace_id].append(query.transaction_id)

        # Sort by timestamp proximity
        correlated.sort(key=lambda q: abs((q.timestamp - timestamp).total_seconds()))

        return correlated

    def get_query_statistics(
        self, pattern: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get query statistics for a pattern or all queries.

        Args:
            pattern: Optional query pattern to filter
            hours: Hours of history to analyze

        Returns:
            Query statistics
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        if pattern:
            queries = [
                q for q in self.query_patterns.get(pattern, []) if q.timestamp >= cutoff
            ]
        else:
            queries = [q for q in self.recent_queries if q.timestamp >= cutoff]

        if not queries:
            return {"count": 0, "pattern": pattern}

        # Calculate statistics
        durations = [q.duration_ms for q in queries]
        memory_usage = [q.memory_bytes for q in queries if q.memory_bytes]

        stats = {
            "pattern": pattern,
            "count": len(queries),
            "slow_count": sum(1 for q in queries if q.is_slow),
            "memory_intensive_count": sum(1 for q in queries if q.is_memory_intensive),
            "duration": {
                "min": min(durations),
                "max": max(durations),
                "avg": sum(durations) / len(durations),
                "p50": sorted(durations)[len(durations) // 2],
                "p95": (
                    sorted(durations)[int(len(durations) * 0.95)]
                    if len(durations) > 20
                    else max(durations)
                ),
            },
            "unique_transactions": len(
                {q.transaction_id for q in queries if q.transaction_id}
            ),
        }

        if memory_usage:
            stats["memory"] = {
                "min_mb": min(memory_usage) / 1_000_000,
                "max_mb": max(memory_usage) / 1_000_000,
                "avg_mb": sum(memory_usage) / len(memory_usage) / 1_000_000,
            }

        return stats

    def identify_problematic_patterns(
        self, threshold_slow_count: int = 10, threshold_memory_count: int = 5
    ) -> List[Tuple[str, Dict]]:
        """
        Identify problematic query patterns.

        Args:
            threshold_slow_count: Threshold for slow query count
            threshold_memory_count: Threshold for memory intensive count

        Returns:
            List of (pattern, statistics) tuples
        """
        problematic = []

        for pattern in self.query_patterns:
            if (
                self.slow_query_patterns[pattern] >= threshold_slow_count
                or self.memory_intensive_patterns[pattern] >= threshold_memory_count
            ):

                stats = self.get_query_statistics(pattern, hours=1)
                problematic.append((pattern, stats))

        # Sort by severity (slow count + memory count)
        problematic.sort(
            key=lambda x: x[1].get("slow_count", 0)
            + x[1].get("memory_intensive_count", 0),
            reverse=True,
        )

        return problematic

    def suggest_optimizations(self, pattern: str) -> List[str]:
        """
        Suggest optimizations for a query pattern.

        Args:
            pattern: Query pattern to analyze

        Returns:
            List of optimization suggestions
        """
        suggestions = []
        queries = self.query_patterns.get(pattern, [])

        if not queries:
            return suggestions

        # Analyze pattern characteristics
        stats = self.get_query_statistics(pattern, hours=24)

        # Check for missing indexes
        if "MATCH" in pattern and stats["duration"]["avg"] > 500:
            suggestions.append(
                "Consider adding indexes on frequently matched properties"
            )

        # Check for cartesian products
        if pattern.count("MATCH") > 1 and "WHERE" not in pattern:
            suggestions.append(
                "Potential cartesian product - add WHERE clauses to connect patterns"
            )

        # Check for large result sets
        if stats.get("memory", {}).get("avg_mb", 0) > 100:
            suggestions.append(
                "Large memory usage - consider pagination with SKIP/LIMIT"
            )

        # Check for expensive operations
        if "COLLECT" in pattern or "UNWIND" in pattern:
            suggestions.append(
                "Collection operations can be expensive - consider streaming approach"
            )

        # Check for property access patterns
        if "*" in pattern:
            suggestions.append(
                "Avoid using * to return all properties - specify needed properties"
            )

        # Check planning time
        avg_planning = sum(q.planning_time_ms or 0 for q in queries) / len(queries)
        if avg_planning > 50:
            suggestions.append(
                f"High planning time ({avg_planning:.1f}ms) - consider query hints"
            )

        return suggestions

    def export_correlation_data(self) -> Dict[str, Any]:
        """Export correlation data for analysis."""
        return {
            "total_queries": len(self.recent_queries),
            "unique_patterns": len(self.query_patterns),
            "slow_patterns": dict(self.slow_query_patterns),
            "memory_patterns": dict(self.memory_intensive_patterns),
            "trace_correlations": dict(self.trace_correlations),
            "problematic_patterns": [
                {
                    "pattern": pattern,
                    "stats": stats,
                    "suggestions": self.suggest_optimizations(pattern),
                }
                for pattern, stats in self.identify_problematic_patterns()
            ],
        }
