#!/usr/bin/env python3
"""
TDD Tests for Graphiti Memory System
Tests temporal weighting, supersession, and cross-domain search
"""

import pytest
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Set test environment
os.environ['GRAPHITI_GROUP_ID'] = 'test_shared_knowledge'
os.environ['FALKORDB_DATABASE'] = 'test_db'

from graphiti_memory import SharedMemory, MemoryStatus, get_shared_memory
from capture import PatternCapture, PatternType, get_pattern_capture


@pytest.fixture
async def mock_graphiti_client():
    """Mock Graphiti client for testing"""
    client = AsyncMock()
    client.add_episode = AsyncMock(return_value="test_memory_id_123")
    client.search = AsyncMock(return_value=[])
    client.add_observations = AsyncMock()
    client.create_relations = AsyncMock()
    client.build_indices_and_constraints = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
async def memory_with_mock(mock_graphiti_client):
    """SharedMemory instance with mocked Graphiti client"""
    memory = SharedMemory()
    
    # Mock the initialization
    with patch('graphiti_memory.FalkorDriver') as mock_driver:
        with patch('graphiti_memory.OpenAIClient') as mock_llm:
            with patch('graphiti_memory.OpenAIEmbedder') as mock_embedder:
                with patch('graphiti_memory.Graphiti', return_value=mock_graphiti_client):
                    await memory.initialize()
    
    return memory


class TestSharedMemory:
    """Test SharedMemory functionality"""
    
    async def test_initialization(self, memory_with_mock):
        """Test memory initialization with shared group_id"""
        assert memory_with_mock.group_id == 'test_shared_knowledge'
        assert memory_with_mock.database == 'test_db'
        assert memory_with_mock._initialized == True
    
    async def test_add_memory(self, memory_with_mock):
        """Test adding memory with metadata"""
        content = {
            'title': 'Test Solution',
            'error': 'Test error',
            'solution': 'Test fix'
        }
        
        memory_id = await memory_with_mock.add_memory(content, source='claude_code')
        
        assert memory_id == "test_memory_id_123"
        
        # Verify episode was created with correct parameters
        memory_with_mock.client.add_episode.assert_called_once()
        call_args = memory_with_mock.client.add_episode.call_args
        
        assert 'claude_code: Test Solution' in call_args.kwargs['name']
        assert call_args.kwargs['group_id'] == 'test_shared_knowledge'
        
        # Check metadata was added
        episode_body = json.loads(call_args.kwargs['episode_body'])
        assert episode_body['source'] == 'claude_code'
        assert episode_body['status'] == MemoryStatus.ACTIVE.value
        assert 'timestamp' in episode_body
    
    async def test_cross_reference_detection(self, memory_with_mock):
        """Test detection of cross-domain references"""
        content = {
            'title': 'Docker Deployment Fix',
            'solution': 'Fixed docker compose issue',
            'context': 'TDD testing with pytest'
        }
        
        await memory_with_mock.add_memory(content, source='claude_code')
        
        call_args = memory_with_mock.client.add_episode.call_args
        episode_body = json.loads(call_args.kwargs['episode_body'])
        
        # Should detect Docker and TDD references
        assert '@computer context' in episode_body['cross_references']
        assert 'deployment task' in episode_body['cross_references']
        assert 'testing methodology' in episode_body['cross_references']
    
    async def test_temporal_weighting(self, memory_with_mock):
        """Test temporal decay in search results"""
        # Create mock search results with different ages
        mock_results = [
            Mock(
                episode_body=json.dumps({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'status': 'active',
                    'title': 'Recent solution'
                }),
                score=0.9
            ),
            Mock(
                episode_body=json.dumps({
                    'timestamp': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                    'status': 'active',
                    'title': 'Old solution'
                }),
                score=0.9
            )
        ]
        
        memory_with_mock.client.search.return_value = mock_results
        
        results = await memory_with_mock.search_with_temporal_weight('test query')
        
        # Recent solution should score higher
        assert results[0].final_score > results[1].final_score
        
        # Check decay factor was applied
        expected_decay = memory_with_mock.decay_factor ** 30
        old_score = results[1].final_score
        assert old_score == pytest.approx(0.9 * expected_decay, rel=0.01)
    
    async def test_supersede_memory(self, memory_with_mock):
        """Test memory supersession preserves history"""
        old_id = "old_memory_123"
        new_content = {
            'title': 'Improved Solution',
            'solution': 'Better fix'
        }
        
        new_id = await memory_with_mock.supersede_memory(
            old_id, 
            new_content, 
            "Found better solution"
        )
        
        # Check new memory was created
        assert new_id == "test_memory_id_123"
        
        # Verify old memory was marked as superseded
        memory_with_mock.client.add_observations.assert_called_once()
        obs_call = memory_with_mock.client.add_observations.call_args
        observations = obs_call.kwargs['observations'][0]['contents']
        
        assert f"SUPERSEDED_BY: {new_id}" in observations
        assert "REASON: Found better solution" in observations
        assert f"STATUS: {MemoryStatus.SUPERSEDED.value}" in observations
        
        # Verify supersession relationship was created
        memory_with_mock.client.create_relations.assert_called_once()
        rel_call = memory_with_mock.client.create_relations.call_args
        relation = rel_call.kwargs['relations'][0]
        
        assert relation['from'] == new_id
        assert relation['to'] == old_id
        assert relation['relationType'] == 'supersedes'
    
    async def test_status_filtering(self, memory_with_mock):
        """Test filtering by memory status"""
        mock_results = [
            Mock(
                episode_body=json.dumps({
                    'status': MemoryStatus.ACTIVE.value,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }),
                score=1.0
            ),
            Mock(
                episode_body=json.dumps({
                    'status': MemoryStatus.DEPRECATED.value,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }),
                score=1.0
            ),
            Mock(
                episode_body=json.dumps({
                    'status': MemoryStatus.HISTORICAL.value,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }),
                score=1.0
            )
        ]
        
        memory_with_mock.client.search.return_value = mock_results
        
        # Search without historical
        results = await memory_with_mock.search_with_temporal_weight(
            'test', 
            include_historical=False
        )
        
        # Should only return active memory
        assert len(results) == 1
        assert results[0].status == MemoryStatus.ACTIVE.value
        
        # Search with historical
        results = await memory_with_mock.search_with_temporal_weight(
            'test',
            include_historical=True
        )
        
        # Should return active and historical, but not deprecated
        assert len(results) == 2
        statuses = [r.status for r in results]
        assert MemoryStatus.ACTIVE.value in statuses
        assert MemoryStatus.HISTORICAL.value in statuses
        assert MemoryStatus.DEPRECATED.value not in statuses
    
    async def test_source_filtering(self, memory_with_mock):
        """Test filtering by source"""
        mock_results = [
            Mock(
                episode_body=json.dumps({
                    'source': 'claude_code',
                    'status': 'active',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }),
                score=1.0
            ),
            Mock(
                episode_body=json.dumps({
                    'source': 'gtd_coach',
                    'status': 'active',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }),
                score=1.0
            )
        ]
        
        memory_with_mock.client.search.return_value = mock_results
        
        # Filter for claude_code only
        results = await memory_with_mock.search_with_temporal_weight(
            'test',
            filter_source='claude_code'
        )
        
        assert len(results) == 1
        assert results[0].metadata['source'] == 'claude_code'
    
    async def test_cross_domain_insights(self, memory_with_mock):
        """Test finding cross-domain insights"""
        mock_results = [
            Mock(
                id='memory_1',
                episode_body=json.dumps({
                    'source': 'claude_code',
                    'cross_references': ['@computer context', 'testing methodology'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }),
                score=1.0,
                final_score=1.0,
                metadata={'cross_references': ['@computer context', 'testing methodology']}
            )
        ]
        
        memory_with_mock.client.search.return_value = mock_results
        
        insights = await memory_with_mock.find_cross_domain_insights('docker')
        
        assert len(insights) == 1
        assert insights[0]['memory_id'] == 'memory_1'
        assert '@computer context' in insights[0]['cross_references']
        assert 'coding' in insights[0]['domains']
    
    async def test_memory_evolution(self, memory_with_mock):
        """Test tracking memory evolution"""
        mock_results = [
            Mock(
                id='new_memory',
                episode_body=json.dumps({
                    'supersedes': 'old_memory',
                    'supersession_reason': 'Improved solution',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }),
                metadata={
                    'supersedes': 'old_memory',
                    'supersession_reason': 'Improved solution',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                status='active',
                score=0.9
            ),
            Mock(
                id='old_memory',
                episode_body=json.dumps({
                    'timestamp': (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                }),
                metadata={
                    'timestamp': (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                },
                status='superseded',
                score=0.5
            )
        ]
        
        memory_with_mock.client.search.return_value = mock_results
        
        evolution = await memory_with_mock.get_memory_evolution('test topic')
        
        assert 'old_memory' in evolution
        assert evolution['old_memory'][0]['improved_to'] == 'new_memory'
        assert evolution['old_memory'][0]['reason'] == 'Improved solution'


class TestPatternCapture:
    """Test pattern capture functionality"""
    
    @pytest.fixture
    async def capture_with_mock(self, memory_with_mock):
        """PatternCapture with mocked memory"""
        capture = PatternCapture()
        capture.memory = memory_with_mock
        return capture
    
    async def test_capture_tdd_cycle(self, capture_with_mock):
        """Test capturing TDD red-green-refactor cycle"""
        test_code = "def test_feature(): assert False"
        implementation = "def feature(): return True"
        
        memory_id = await capture_with_mock.capture_tdd_cycle(
            test_code=test_code,
            implementation=implementation,
            feature_name="test_feature"
        )
        
        assert memory_id == "test_memory_id_123"
        
        # Check captured data
        call_args = capture_with_mock.memory.client.add_episode.call_args
        episode_body = json.loads(call_args.kwargs['episode_body'])
        
        assert episode_body['type'] == PatternType.TDD_CYCLE.value
        assert episode_body['red_phase'] == test_code
        assert episode_body['green_phase'] == implementation
        assert episode_body['feature'] == "test_feature"
        assert episode_body['methodology'] == 'TDD'
    
    async def test_capture_deployment_solution(self, capture_with_mock):
        """Test capturing deployment solutions"""
        capture_with_mock.memory.search_with_temporal_weight = AsyncMock(return_value=[])
        
        memory_id = await capture_with_mock.capture_deployment_solution(
            error="Docker build failed",
            solution="Clear cache and rebuild",
            context={"environment": "OrbStack"}
        )
        
        assert memory_id == "test_memory_id_123"
        
        call_args = capture_with_mock.memory.client.add_episode.call_args
        episode_body = json.loads(call_args.kwargs['episode_body'])
        
        assert episode_body['type'] == PatternType.DEPLOYMENT_SOLUTION.value
        assert episode_body['error'] == "Docker build failed"
        assert episode_body['solution'] == "Clear cache and rebuild"
        assert episode_body['context']['orbstack'] == True
    
    async def test_capture_command_pattern(self, capture_with_mock):
        """Test capturing command patterns"""
        capture_with_mock.memory.search_with_temporal_weight = AsyncMock(return_value=[])
        
        memory_id = await capture_with_mock.capture_command_pattern(
            command="docker compose up -d",
            context="deployment",
            success=True
        )
        
        assert memory_id == "test_memory_id_123"
        
        call_args = capture_with_mock.memory.client.add_episode.call_args
        episode_body = json.loads(call_args.kwargs['episode_body'])
        
        assert episode_body['type'] == PatternType.COMMAND_PATTERN.value
        assert episode_body['command'] == "docker compose up -d"
        assert episode_body['success'] == True
        assert episode_body['frequency'] == 1
    
    async def test_update_command_frequency(self, capture_with_mock):
        """Test updating frequency for existing command"""
        # Mock existing command with frequency
        existing = Mock(
            id='existing_cmd',
            final_score=0.95,
            metadata={
                'command': 'docker compose up -d',
                'frequency': 5
            }
        )
        
        capture_with_mock.memory.search_with_temporal_weight = AsyncMock(
            return_value=[existing]
        )
        capture_with_mock.memory.supersede_memory = AsyncMock(
            return_value="updated_cmd_id"
        )
        
        memory_id = await capture_with_mock.capture_command_pattern(
            command="docker compose up -d",
            context="deployment",
            success=True
        )
        
        # Should have called supersede with incremented frequency
        capture_with_mock.memory.supersede_memory.assert_called_once()
        call_args = capture_with_mock.memory.supersede_memory.call_args
        
        assert call_args.args[1]['frequency'] == 6  # Incremented from 5


class TestIntegration:
    """Integration tests for the memory system"""
    
    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test singleton pattern for shared memory"""
        with patch('graphiti_memory.SharedMemory.initialize', new_callable=AsyncMock):
            memory1 = await get_shared_memory()
            memory2 = await get_shared_memory()
            
            assert memory1 is memory2
    
    @pytest.mark.asyncio
    async def test_capture_singleton(self):
        """Test singleton pattern for pattern capture"""
        with patch('capture.PatternCapture.initialize', new_callable=AsyncMock):
            capture1 = await get_pattern_capture()
            capture2 = await get_pattern_capture()
            
            assert capture1 is capture2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])