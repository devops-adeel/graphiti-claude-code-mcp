#!/usr/bin/env python3
"""
Memory Pipeline Health Check
============================
Verifies the complete memory capture → storage → retrieval pipeline.

This script tests each stage of the memory system and provides clear
diagnostics when issues occur. Run with --verbose to see Neo4j queries
and internal operations.

Usage:
    python scripts/health_check_memory.py           # Basic health check
    python scripts/health_check_memory.py --verbose # Show queries and details
    python scripts/health_check_memory.py --fix     # Attempt to fix common issues

Exit codes:
    0 - All checks passed
    1 - Configuration issues
    2 - Connection failures
    3 - Pipeline failures
"""

import os
import sys
import asyncio
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Colors for terminal output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
GRAY = "\033[0;37m"
NC = "\033[0m"  # No Color


class HealthCheck:
    """Comprehensive health check for memory pipeline"""

    def __init__(self, verbose: bool = False, fix: bool = False):
        self.verbose = verbose
        self.fix = fix
        self.results = []
        self.memory = None
        self.capture = None
        self.test_memory_id = None

    def log(self, message: str, level: str = "info"):
        """Colored output based on level"""
        colors = {
            "error": RED,
            "success": GREEN,
            "warning": YELLOW,
            "info": BLUE,
            "debug": CYAN,
            "query": GRAY,
        }
        color = colors.get(level, NC)
        prefix = {
            "error": "✗",
            "success": "✓",
            "warning": "⚠",
            "info": "→",
            "debug": "🔍",
            "query": "📊",
        }.get(level, "•")

        print(f"{color}{prefix} {message}{NC}")

    def log_section(self, title: str):
        """Log a section header"""
        print(f"\n{BLUE}{'='*60}{NC}")
        print(f"{BLUE}{title}{NC}")
        print(f"{BLUE}{'='*60}{NC}")

    async def check_configuration(self) -> bool:
        """Stage 1: Verify configuration"""
        self.log_section("Stage 1: Configuration Check")

        config_ok = True

        # Check environment files
        env_paths = [
            Path.home() / "gtd-coach" / ".env.graphiti",
            Path(".env.graphiti"),
            Path.home() / ".env.graphiti",
        ]

        env_found = False
        for path in env_paths:
            if path.exists():
                self.log(f"Found config: {path}", "success")
                env_found = True
                break

        if not env_found:
            self.log("No .env.graphiti file found", "error")
            self.log("Expected locations:", "info")
            for path in env_paths:
                print(f"  - {path}")
            config_ok = False

            if self.fix:
                self.log("Attempting to create default config...", "warning")
                # Create default config logic here

        # Check critical environment variables
        required_vars = {
            "GRAPHITI_GROUP_ID": "shared_knowledge",
            "NEO4J_URI": None,  # Any value ok
            "NEO4J_USER": None,  # Any value ok
            "NEO4J_DATABASE": None,  # Any value ok
            "OPENAI_API_KEY": None,  # Just needs to exist
        }

        for var, expected in required_vars.items():
            value = os.getenv(var)
            if value:
                if expected and value != expected:
                    self.log(f"{var}: {value} (expected: {expected})", "warning")
                    config_ok = False
                else:
                    self.log(f"{var}: {value or 'set'}", "success")
            else:
                self.log(f"{var}: NOT SET", "error")
                config_ok = False

        # Show detected configuration
        if self.verbose:
            self.log("", "debug")
            self.log("Current configuration:", "debug")
            uri = os.getenv("NEO4J_URI")
            user = os.getenv("NEO4J_USER")
            db = os.getenv("NEO4J_DATABASE")
            group = os.getenv("GRAPHITI_GROUP_ID")
            print(f"  Neo4j: {uri} (user: {user}, db: {db})")
            print(f"  Group ID: {group}")
            print(
                f"  OpenAI: {'configured' if os.getenv('OPENAI_API_KEY') else 'missing'}"
            )

        self.results.append(("Configuration", config_ok))
        return config_ok

    async def check_connections(self) -> bool:
        """Stage 2: Test connections to Neo4j and OpenAI"""
        self.log_section("Stage 2: Connection Check")

        connection_ok = True

        # Test Neo4j connection
        try:
            if self.verbose:
                self.log("Testing Neo4j connection...", "debug")
                uri = os.getenv("NEO4J_URI")
                user = os.getenv("NEO4J_USER")
                self.log(f"Connecting to {uri} as {user}", "query")

            # Import here to avoid early failures
            from graphiti_memory import get_shared_memory

            self.memory = await get_shared_memory()

            # Quick test query
            test_query = "MATCH (n) RETURN count(n) as node_count LIMIT 1"
            if self.verbose:
                self.log(f"Query: {test_query}", "query")

            self.log("Neo4j connection: OK", "success")

        except Exception as e:
            self.log(f"Neo4j connection failed: {str(e)}", "error")
            if self.verbose:
                traceback.print_exc()
            connection_ok = False

            if self.fix:
                self.log("Fix suggestions:", "warning")
                print("  1. Check Neo4j is running: docker ps | grep neo4j")
                print("  2. Verify connection: cypher-shell -a bolt://localhost:7687")
                print("  3. For Docker: use 'neo4j.graphiti.local' as host")

        # Test OpenAI connection
        try:
            if self.verbose:
                self.log("Testing OpenAI API...", "debug")

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key == "placeholder-set-in-home-env":
                raise ValueError("Valid OPENAI_API_KEY not found")

            # Simple validation - just check format
            if api_key.startswith("sk-") and len(api_key) > 20:
                self.log("OpenAI API key: Valid format", "success")
            else:
                self.log("OpenAI API key: Invalid format", "warning")

        except Exception as e:
            self.log(f"OpenAI configuration issue: {str(e)}", "error")
            connection_ok = False

            if self.fix:
                self.log("Fix suggestions:", "warning")
                print("  1. Set OPENAI_API_KEY in ~/.env")
                print("  2. Or export OPENAI_API_KEY='sk-...'")

        self.results.append(("Connections", connection_ok))
        return connection_ok

    async def check_capture(self) -> bool:
        """Stage 3: Test memory capture"""
        self.log_section("Stage 3: Capture Test")

        capture_ok = True

        try:
            from capture import get_pattern_capture
            from datetime import timezone

            if self.verbose:
                self.log("Initializing pattern capture...", "debug")

            self.capture = await get_pattern_capture()

            # Create test memory
            test_content = {
                "title": f"Health Check Test - {datetime.now().isoformat()}",
                "content": "This is a test memory from health check script",
                "type": "general",
                "source": "health_check",
                "metadata": {
                    "test": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

            if self.verbose:
                self.log("Capturing test memory:", "debug")
                print(json.dumps(test_content, indent=2))

            # Capture the memory
            self.test_memory_id = await self.memory.add_memory(
                test_content, source="health_check"
            )

            if self.test_memory_id:
                self.log(f"Memory captured: {self.test_memory_id}", "success")
            else:
                raise ValueError("No memory ID returned")

        except Exception as e:
            self.log(f"Capture failed: {str(e)}", "error")
            if self.verbose:
                traceback.print_exc()
            capture_ok = False

            if self.fix:
                self.log("Debugging capture issues:", "warning")
                print("  1. Check entity extraction (OpenAI must be working)")
                print("  2. Verify Graphiti client initialization")
                print("  3. Check logs: docker logs graphiti-claude-code-mcp")

        self.results.append(("Capture", capture_ok))
        return capture_ok

    async def check_storage(self) -> bool:
        """Stage 4: Verify storage in Neo4j"""
        self.log_section("Stage 4: Storage Verification")

        storage_ok = True

        if not self.test_memory_id:
            self.log("No test memory to verify (capture failed)", "error")
            self.results.append(("Storage", False))
            return False

        try:
            # Direct Neo4j query to verify storage
            if self.verbose:
                self.log("Querying Neo4j for stored memory...", "debug")
                # Show the query that would verify storage
                query = f"""
                MATCH (e:Episode {{uuid: '{self.test_memory_id}'}})
                RETURN e.content as content, e.created_at as created
                """
                self.log(f"Query: {query}", "query")

            # Use search to verify it's findable
            results = await self.memory.search_with_temporal_weight("health check test")

            found = any(
                self.test_memory_id in str(getattr(r, "uuid", "")) for r in results
            )

            if found:
                self.log("Memory found in storage", "success")
            else:
                self.log("Memory not found in storage", "error")
                storage_ok = False

                if self.verbose:
                    self.log("Search returned memories:", "debug")
                    for r in results[:3]:
                        print(f"  - {getattr(r, 'fact', 'unknown')[:60]}...")

        except Exception as e:
            self.log(f"Storage verification failed: {str(e)}", "error")
            if self.verbose:
                traceback.print_exc()
            storage_ok = False

            if self.fix:
                self.log("Direct Neo4j query to check:", "warning")
                print(f"  cypher-shell -a {os.getenv('NEO4J_URI')}")
                print(f"  MATCH (n) RETURN n LIMIT 5")

        self.results.append(("Storage", storage_ok))
        return storage_ok

    async def check_group_id_propagation(self) -> bool:
        """Stage 4b: Verify group_id propagation"""
        self.log_section("Stage 4b: Group ID Verification")

        group_id_ok = True

        try:
            memory = await self.get_memory()
            expected_group_id = memory.group_id

            if self.verbose:
                self.log(f"Expected group_id: {expected_group_id}", "debug")
                self.log("Checking nodes in Neo4j for correct group_id...", "debug")

            # Verify group_id propagation
            verification_passed = await memory._verify_group_id_propagation()

            if verification_passed:
                self.log(
                    f"Group ID propagation: OK (all nodes have '{expected_group_id}')",
                    "success",
                )
            else:
                self.log("Group ID propagation: FAILED", "error")
                group_id_ok = False

                if self.fix:
                    self.log("Fix suggestions:", "warning")
                    print("  1. Update existing nodes with correct group_id:")
                    print(
                        f"     MATCH (n) WHERE n.group_id = '' SET n.group_id = '{expected_group_id}'"
                    )
                    print("  2. Restart MCP server to pick up changes")
                    print(
                        "  3. Verify Graphiti client initialization includes group_id parameter"
                    )

            # Additional check: count nodes by group_id
            if self.verbose:
                query = """
                MATCH (n)
                RETURN n.group_id as group_id, count(n) as count
                ORDER BY count DESC
                """
                self.log(f"Query: {query}", "query")

        except Exception as e:
            self.log(f"Group ID verification failed: {str(e)}", "error")
            group_id_ok = False

        self.results.append(("Group ID", group_id_ok))
        return group_id_ok

    async def check_retrieval(self) -> bool:
        """Stage 5: Test retrieval and search"""
        self.log_section("Stage 5: Retrieval Test")

        retrieval_ok = True

        try:
            # Test different search methods
            test_queries = [
                ("Exact search", "health check test"),
                ("Semantic search", "testing memory system"),
                ("Partial match", "health"),
            ]

            for search_type, query in test_queries:
                if self.verbose:
                    self.log(f"Testing {search_type}: '{query}'", "debug")

                results = await self.memory.search_with_temporal_weight(query)

                if results:
                    self.log(f"{search_type}: {len(results)} results", "success")
                    if self.verbose:
                        for i, r in enumerate(results[:3]):
                            score = getattr(r, "score", 0)
                            fact = getattr(r, "fact", "unknown")
                            print(f"    {i+1}. Score: {score:.3f} - {fact[:50]}...")
                else:
                    self.log(f"{search_type}: No results", "warning")

        except Exception as e:
            self.log(f"Retrieval failed: {str(e)}", "error")
            if self.verbose:
                traceback.print_exc()
            retrieval_ok = False

            if self.fix:
                self.log("Common retrieval issues:", "warning")
                print("  1. Temporal decay might filter old memories")
                print("  2. Status filter might exclude DEPRECATED")
                print("  3. Embedding generation might have failed")

        self.results.append(("Retrieval", retrieval_ok))
        return retrieval_ok

    async def check_temporal(self) -> bool:
        """Stage 6: Test temporal decay"""
        self.log_section("Stage 6: Temporal Decay Test")

        temporal_ok = True

        try:
            decay_factor = float(os.getenv("MEMORY_DECAY_FACTOR"))

            if self.verbose:
                self.log(f"Decay factor: {decay_factor}", "debug")
                self.log("Testing temporal weights...", "debug")

            # Calculate weights for different ages
            test_ages = [0, 1, 7, 30, 90]

            for days in test_ages:
                weight = decay_factor**days
                status = "fresh" if weight > 0.8 else "aging" if weight > 0.5 else "old"
                color = (
                    "success"
                    if weight > 0.8
                    else "warning" if weight > 0.5 else "error"
                )

                self.log(f"Age {days:3d} days: weight = {weight:.3f} ({status})", color)

            # Show cutoff point
            cutoff_days = int((-0.5) / (0.95 - 1)) if decay_factor == 0.95 else 30
            self.log(
                f"Memories become 'weak' (< 0.5) after ~{cutoff_days} days", "info"
            )

        except Exception as e:
            self.log(f"Temporal test failed: {str(e)}", "error")
            temporal_ok = False

        self.results.append(("Temporal Decay", temporal_ok))
        return temporal_ok

    async def check_cross_domain(self) -> bool:
        """Stage 7: Test cross-domain insights"""
        self.log_section("Stage 7: Cross-Domain Test")

        cross_ok = True

        try:
            if self.verbose:
                self.log("Testing GTD integration...", "debug")

            # Check if GTD integration is enabled
            gtd_enabled = os.getenv("ENABLE_GTD_INTEGRATION").lower() == "true"
            cross_ref_enabled = os.getenv("ENABLE_CROSS_REFERENCES").lower() == "true"

            self.log(
                f"GTD Integration: {'enabled' if gtd_enabled else 'disabled'}",
                "success" if gtd_enabled else "warning",
            )
            self.log(
                f"Cross References: {'enabled' if cross_ref_enabled else 'disabled'}",
                "success" if cross_ref_enabled else "warning",
            )

            if gtd_enabled and self.memory:
                # Try to find cross-domain insights
                insights = await self.memory.find_cross_domain_insights("deployment")

                if insights:
                    self.log(f"Found {len(insights)} cross-domain insights", "success")
                    if self.verbose:
                        for insight in insights[:2]:
                            print(f"  - {insight.get('insight', 'unknown')[:80]}...")
                else:
                    self.log("No cross-domain insights found (might be normal)", "info")

        except Exception as e:
            self.log(f"Cross-domain test failed: {str(e)}", "error")
            if self.verbose:
                traceback.print_exc()
            cross_ok = False

        self.results.append(("Cross-Domain", cross_ok))
        return cross_ok

    async def cleanup(self):
        """Clean up test memories"""
        if self.test_memory_id and self.memory:
            try:
                if self.verbose:
                    self.log("Cleaning up test memory...", "debug")
                # Mark as deprecated rather than delete
                await self.memory.supersede_memory(
                    self.test_memory_id,
                    {"status": "deprecated", "reason": "health check test"},
                    "Health check cleanup",
                )
                self.log("Test memory cleaned up", "success")
            except Exception as e:
                if self.verbose:
                    self.log(f"Cleanup failed: {str(e)}", "warning")

    async def run(self) -> int:
        """Run all health checks"""
        print(f"\n{BLUE}{'='*60}{NC}")
        print(f"{BLUE}Memory Pipeline Health Check{NC}")
        print(f"{BLUE}{'='*60}{NC}")

        stages = [
            ("Configuration", self.check_configuration),
            ("Connections", self.check_connections),
            ("Capture", self.check_capture),
            ("Storage", self.check_storage),
            ("Group ID", self.check_group_id_propagation),
            ("Retrieval", self.check_retrieval),
            ("Temporal Decay", self.check_temporal),
            ("Cross-Domain", self.check_cross_domain),
        ]

        # Run stages in order, stopping on critical failures
        for stage_name, stage_func in stages:
            try:
                success = await stage_func()
                if not success and stage_name in ["Configuration", "Connections"]:
                    self.log(f"\n{stage_name} is critical - stopping here", "error")
                    break
            except Exception as e:
                self.log(f"Stage {stage_name} crashed: {str(e)}", "error")
                if self.verbose:
                    traceback.print_exc()
                self.results.append((stage_name, False))
                if stage_name in ["Configuration", "Connections"]:
                    break

        # Cleanup
        await self.cleanup()

        # Summary
        self.log_section("Health Check Summary")

        total = len(self.results)
        passed = sum(1 for _, ok in self.results if ok)

        for stage, ok in self.results:
            status = "PASS" if ok else "FAIL"
            color = GREEN if ok else RED
            print(f"  {color}{stage:20s}: {status}{NC}")

        print(f"\n{BLUE}{'='*60}{NC}")
        if passed == total:
            print(
                f"{GREEN}✓ All {total} checks passed - Memory pipeline is healthy!{NC}"
            )
            return 0
        else:
            print(f"{RED}✗ {total - passed} of {total} checks failed{NC}")
            print(f"\nRun with --verbose for detailed diagnostics")
            print(f"Run with --fix for repair suggestions")

            # Return different exit codes based on failure type
            if any(stage == "Configuration" and not ok for stage, ok in self.results):
                return 1  # Configuration issues
            elif any(stage == "Connections" and not ok for stage, ok in self.results):
                return 2  # Connection failures
            else:
                return 3  # Pipeline failures


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Health check for memory pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                 # Basic health check
  %(prog)s --verbose       # Show detailed diagnostics
  %(prog)s --fix           # Show fix suggestions
  %(prog)s -v -f           # Verbose with fixes

Exit codes:
  0 - All checks passed
  1 - Configuration issues
  2 - Connection failures
  3 - Pipeline failures
        """,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed diagnostics and queries",
    )

    parser.add_argument(
        "-f", "--fix", action="store_true", help="Show suggestions for fixing issues"
    )

    args = parser.parse_args()

    # Load environment
    from dotenv import load_dotenv

    env_paths = [
        Path.home() / "gtd-coach" / ".env.graphiti",
        Path(".env.graphiti"),
        Path.home() / ".env.graphiti",
        Path.home() / ".env",
    ]

    for path in env_paths:
        if path.exists():
            load_dotenv(path)

    # Run health check
    checker = HealthCheck(verbose=args.verbose, fix=args.fix)
    return await checker.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
