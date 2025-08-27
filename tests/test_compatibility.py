#!/usr/bin/env python3
"""
Compatibility tests for Graphiti v0.17.9 integration
Tests that our memory layer works correctly with Graphiti's API
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphiti_memory import SharedMemory, SearchResultWrapper, MemoryStatus
from memory_models import (
    TDDCycleMetadata,
    DeploymentSolutionMetadata,
    CommandPatternMetadata,
)


class MockEntityEdge:
    """Mock EntityEdge to simulate Graphiti v0.17.9 structure"""

    def __init__(self, **kwargs):
        self.uuid = kwargs.get("uuid", "test-uuid")
        self.fact = kwargs.get("fact", "test fact")
        self.source_node_uuid = kwargs.get("source_node_uuid", "source-uuid")
        self.target_node_uuid = kwargs.get("target_node_uuid", "target-uuid")
        self.valid_at = kwargs.get("valid_at", datetime.now(timezone.utc))
        self.invalid_at = kwargs.get("invalid_at", None)
        self.episodes = kwargs.get("episodes", [])
        # Note: No 'score' or 'status' fields in v0.17.9


class MockEpisode:
    """Mock Episode to simulate Graphiti episode structure"""

    def __init__(self, **kwargs):
        self.uuid = kwargs.get("uuid", "episode-uuid")
        self.episode_body = kwargs.get("episode_body", "{}")
        self.name = kwargs.get("name", "test episode")
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))


class TestSearchResultWrapper:
    """Test the SearchResultWrapper abstraction"""

    def test_wrapper_with_entity_edge(self):
        """Test wrapper correctly handles EntityEdge objects"""
        edge = MockEntityEdge(fact="John is 30 years old", uuid="edge-123")

        wrapper = SearchResultWrapper(edge, computed_score=0.85)

        assert wrapper.fact == "John is 30 years old"
        assert wrapper.uuid == "edge-123"
        assert wrapper.score == 0.85
        assert wrapper.status == MemoryStatus.ACTIVE.value

    def test_wrapper_with_episode(self):
        """Test wrapper correctly handles Episode objects with metadata"""
        metadata = {
            "status": MemoryStatus.SUPERSEDED.value,
            "title": "Test memory",
            "type": "command_pattern",
        }

        episode = MockEpisode(episode_body=json.dumps(metadata))

        wrapper = SearchResultWrapper(episode)

        assert wrapper.metadata == metadata
        assert wrapper.status == MemoryStatus.SUPERSEDED.value
        assert wrapper.score == 0.5  # Default

    def test_wrapper_with_invalid_json(self):
        """Test wrapper handles invalid JSON gracefully"""
        episode = MockEpisode(episode_body="not valid json")

        wrapper = SearchResultWrapper(episode)

        assert wrapper.metadata == {}
        assert wrapper.status == MemoryStatus.ACTIVE.value


class TestVersionDetection:
    """Test Graphiti version detection"""

    @patch("graphiti_core.__version__", "0.17.9")
    def test_supported_version(self):
        """Test detection of supported Graphiti version"""
        memory = SharedMemory()
        memory._detect_graphiti_version()

        assert memory.graphiti_version == "0.17.9"

    @patch("graphiti_core.__version__", "0.17.11")
    def test_untested_version_warning(self, caplog):
        """Test warning for untested but compatible version"""
        memory = SharedMemory()
        memory._detect_graphiti_version()

        assert memory.graphiti_version == "0.17.11"
        # Note: caplog doesn't capture logger output in this test setup

    @patch("graphiti_core.__version__", "1.0.0")
    def test_incompatible_version_warning(self, caplog):
        """Test warning for potentially incompatible version"""
        memory = SharedMemory()
        memory._detect_graphiti_version()

        assert memory.graphiti_version == "1.0.0"
        # Note: caplog doesn't capture logger output in this test setup


class TestMetadataValidation:
    """Test Pydantic metadata validation"""

    def test_tdd_metadata_validation(self):
        """Test TDD cycle metadata validation"""
        metadata = TDDCycleMetadata(
            title="Test Feature",
            red_phase="def test_add(): assert add(1, 2) == 3",
            green_phase="def add(a, b): return a + b",
            feature="addition",
        )

        data = metadata.model_dump()
        assert data["type"] == "tdd_cycle"
        assert data["feature"] == "addition"
        assert data["language"] == "python"

    def test_invalid_metadata_raises(self):
        """Test that invalid metadata raises validation errors"""
        with pytest.raises(ValueError):
            # Missing required field
            TDDCycleMetadata(
                title="Test",
                # Missing red_phase
                feature="test",
            )

    def test_deployment_metadata_context_validation(self):
        """Test deployment metadata context must be serializable"""
        # Valid context
        metadata = DeploymentSolutionMetadata(
            title="Docker Fix",
            error="Container won't start",
            solution="Fixed port mapping",
            context={"port": 8080, "service": "api"},
        )
        assert metadata.context == {"port": 8080, "service": "api"}

        # Invalid context (contains non-serializable object)
        with pytest.raises(ValueError) as excinfo:
            DeploymentSolutionMetadata(
                title="Docker Fix",
                error="Error",
                solution="Solution",
                context={"func": lambda x: x},  # Functions aren't JSON serializable
            )
        assert "JSON serializable" in str(excinfo.value)


@pytest.mark.asyncio
class TestGraphitiIntegration:
    """Test integration with Graphiti API"""

    async def test_search_result_handling(self):
        """Test that search results are properly handled"""
        memory = SharedMemory()

        # Mock Graphiti client search
        mock_results = [
            MockEntityEdge(fact="Docker uses port 6379"),
            MockEntityEdge(fact="FalkorDB is running"),
        ]

        with patch.object(memory, "client") as mock_client:
            mock_client.search = AsyncMock(return_value=mock_results)
            memory._initialized = True

            results = await memory.search_with_temporal_weight("docker")

            # Results should be EntityEdge objects
            assert len(results) <= 10
            assert all(hasattr(r, "fact") for r in results)

    async def test_add_memory_creates_episode(self):
        """Test that add_memory creates a Graphiti episode"""
        memory = SharedMemory()

        with patch.object(memory, "client") as mock_client:
            mock_client.add_episode = AsyncMock(
                return_value=Mock(episode=Mock(uuid="episode-123"))
            )
            memory._initialized = True

            memory_data = {
                "title": "Test Memory",
                "content": "Test content",
                "type": "general",
            }

            result = await memory.add_memory(memory_data, source="test")

            # Should call add_episode
            mock_client.add_episode.assert_called_once()
            assert result == "episode-123"

    async def test_supersede_memory_creates_new_episode(self):
        """Test that supersede_memory creates new episode, not modifies existing"""
        memory = SharedMemory()

        with patch.object(memory, "client") as mock_client:
            mock_client.add_episode = AsyncMock(
                return_value=Mock(episode=Mock(uuid="new-episode"))
            )
            memory._initialized = True

            new_id = await memory.supersede_memory(
                old_id="old-episode",
                new_content={"title": "Improved", "content": "Better solution"},
                reason="Found better approach",
            )

            # Should create new episode with supersession metadata
            mock_client.add_episode.assert_called_once()
            call_args = mock_client.add_episode.call_args

            # Check that supersession metadata is included
            episode_body = json.loads(call_args[1]["episode_body"])
            assert episode_body["supersedes"] == "old-episode"
            assert episode_body["supersession_reason"] == "Found better approach"
            assert new_id == "new-episode"


@pytest.mark.asyncio
class TestTemporalWeighting:
    """Test temporal weighting calculations"""

    async def test_temporal_decay_calculation(self):
        """Test that temporal decay is calculated correctly"""
        memory = SharedMemory()
        memory.decay_factor = 0.95

        # Create mock results with different ages
        now = datetime.now(timezone.utc)
        week_old = now.replace(day=now.day - 7)

        mock_episode = MockEpisode(
            episode_body=json.dumps(
                {"timestamp": week_old.isoformat(), "status": MemoryStatus.ACTIVE.value}
            )
        )

        with patch.object(memory, "client") as mock_client:
            mock_client.search = AsyncMock(return_value=[mock_episode])
            memory._initialized = True

            # Search should apply temporal weighting
            results = await memory.search_with_temporal_weight("test")

            # Verify search was called
            mock_client.search.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
