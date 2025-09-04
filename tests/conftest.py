"""
Pytest configuration and shared fixtures for Langfuse MCP tests.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock
import pytest
import pytest_asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure asyncio for pytest
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables"""
    env_vars = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "test-openai-key"),
        "LANGFUSE_PUBLIC_KEY": os.environ.get("LANGFUSE_PUBLIC_KEY", "test-public-key"),
        "LANGFUSE_SECRET_KEY": os.environ.get("LANGFUSE_SECRET_KEY", "test-secret-key"),
        "LANGFUSE_HOST": os.environ.get("LANGFUSE_HOST", "http://langfuse.local"),
        "NEO4J_HOST": os.environ.get("NEO4J_HOST", "neo4j.graphiti.local"),
        "NEO4J_PORT": os.environ.get("NEO4J_PORT", "7687"),
        "GRAPHITI_GROUP_ID": "test_graphiti_mcp",
        "NEO4J_DATABASE": "neo4j",  # Must be "neo4j" for Community Edition
        "LOG_LEVEL": "ERROR",  # Reduce test noise
    }

    # Save original env
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield env_vars

    # Restore original env
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest_asyncio.fixture
async def mock_langfuse_client():
    """Create a mock Langfuse client"""
    from tests.fixtures.langfuse_test_data import MockLangfuseClient

    return MockLangfuseClient()


@pytest_asyncio.fixture
async def mock_graphiti_memory():
    """Create a mock Graphiti memory instance"""
    memory = AsyncMock()
    memory.group_id = "test_graphiti_mcp"
    memory.search_with_temporal_weight = AsyncMock(return_value=[])
    memory.add_memory = AsyncMock(return_value="mock-memory-id")
    memory.supersede_memory = AsyncMock(return_value=True)
    memory.find_cross_domain_insights = AsyncMock(return_value=[])
    memory.get_memory_evolution = AsyncMock(return_value=[])
    memory.link_to_gtd_task = AsyncMock(return_value=True)
    return memory


@pytest_asyncio.fixture
async def mock_pattern_capture():
    """Create a mock pattern capture instance"""
    capture = AsyncMock()
    capture.capture_deployment_solution = AsyncMock(return_value="mock-solution-id")
    capture.capture_tdd_cycle = AsyncMock(return_value="mock-tdd-id")
    capture.capture_docker_fix = AsyncMock(return_value="mock-docker-id")
    capture.capture_command_pattern = AsyncMock(return_value="mock-command-id")
    return capture


@pytest_asyncio.fixture
async def mock_mcp_server():
    """Create a mock MCP server for testing"""
    from mcp.server import Server

    server = MagicMock(spec=Server)
    server.name = "test-graphiti-mcp"
    server.version = "0.1.0"

    # Mock server methods
    server.list_tools = AsyncMock(return_value=[])
    server.call_tool = AsyncMock(return_value={"status": "success"})
    server.list_resources = AsyncMock(return_value=[])
    server.read_resource = AsyncMock(return_value={"content": "test"})

    return server


@pytest.fixture
def langfuse_test_scenarios():
    """Get all Langfuse test scenarios"""
    from tests.fixtures.langfuse_test_data import LangfuseTestData

    return LangfuseTestData.get_all_test_scenarios()


@pytest.fixture
def pattern_detector():
    """Get a pattern detector instance"""
    from langfuse_integration.langfuse_patterns import PatternDetector

    return PatternDetector()


# Test markers
pytest.mark.slow = pytest.mark.slow
pytest.mark.integration = pytest.mark.integration
pytest.mark.unit = pytest.mark.unit


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# Skip slow tests by default in CI
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers"""
    if config.getoption("--ci"):
        skip_slow = pytest.mark.skip(reason="Slow test skipped in CI")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--ci",
        action="store_true",
        default=False,
        help="Run in CI mode (skip slow tests)",
    )
    parser.addoption(
        "--real-langfuse",
        action="store_true",
        default=False,
        help="Run tests against real Langfuse instance",
    )
    parser.addoption(
        "--real-neo4j",
        action="store_true",
        default=False,
        help="Run tests against real Neo4j instance",
    )
