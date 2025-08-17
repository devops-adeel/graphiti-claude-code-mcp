#!/usr/bin/env python3
"""
Unified Graphiti Memory Client for Claude Code
Shares knowledge graph with GTD Coach using same group_id
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.nodes import EpisodeType

logger = logging.getLogger(__name__)


class MemoryStatus(Enum):
    """Status for memory lifecycle management"""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    HISTORICAL = "historical"
    DEPRECATED = "deprecated"


class SharedMemory:
    """
    Memory layer sharing knowledge with GTD Coach
    Uses same FalkorDB instance and group_id for unified knowledge graph
    """
    
    def __init__(self):
        """Initialize with shared configuration"""
        # Load environment configuration
        self._load_config()
        
        # CRITICAL: Use same group_id as GTD Coach for shared knowledge
        self.group_id = os.getenv('GRAPHITI_GROUP_ID', 'shared_gtd_knowledge')
        self.database = os.getenv('FALKORDB_DATABASE', 'shared_knowledge_graph')
        
        # Memory configuration
        self.decay_factor = float(os.getenv('MEMORY_DECAY_FACTOR', '0.95'))
        self.include_historical = os.getenv('MEMORY_INCLUDE_HISTORICAL', 'false').lower() == 'true'
        
        # Cross-domain features
        self.enable_gtd = os.getenv('ENABLE_GTD_INTEGRATION', 'true').lower() == 'true'
        self.enable_cross_ref = os.getenv('ENABLE_CROSS_REFERENCES', 'true').lower() == 'true'
        
        self.client = None
        self.user_node_uuid = None
        self._initialized = False
        
        logger.info(f"SharedMemory configured with group_id: {self.group_id}")
    
    def _load_config(self):
        """Load configuration from shared .env.graphiti file"""
        # Try GTD Coach location first
        env_paths = [
            Path.home() / "gtd-coach" / ".env.graphiti",
            Path(".env.graphiti"),
            Path.home() / ".env.graphiti"
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded configuration from {env_path}")
                return
        
        logger.warning("No .env.graphiti found, using environment variables")
    
    async def initialize(self):
        """Connect to shared FalkorDB instance"""
        if self._initialized:
            return self.client
        
        try:
            # Initialize FalkorDB driver
            driver = FalkorDriver(
                host=os.getenv('FALKORDB_HOST', 'localhost'),
                port=int(os.getenv('FALKORDB_PORT', '6380')),
                database=self.database
            )
            
            # Initialize LLM client
            llm_config = LLMConfig(
                api_key=os.getenv('OPENAI_API_KEY'),
                model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
                temperature=0.1,
                max_tokens=4096
            )
            llm_client = OpenAIClient(config=llm_config)
            
            # Initialize embedder
            embedder_config = OpenAIEmbedderConfig(
                api_key=os.getenv('OPENAI_API_KEY'),
                embedding_model=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
            )
            embedder = OpenAIEmbedder(config=embedder_config)
            
            # Initialize Graphiti client
            self.client = Graphiti(
                graph_driver=driver,
                llm_client=llm_client,
                embedder=embedder
            )
            
            # Build indices and constraints
            await self.client.build_indices_and_constraints()
            
            self._initialized = True
            logger.info(f"✅ Connected to shared knowledge graph: {self.database}/{self.group_id}")
            
            return self.client
            
        except Exception as e:
            logger.error(f"Failed to initialize SharedMemory: {e}")
            raise
    
    async def add_memory(self, content: dict, source: str = "claude_code") -> str:
        """
        Add memory with context awareness
        
        Args:
            content: Memory content dictionary
            source: Source identifier (claude_code, gtd_coach, etc.)
        
        Returns:
            Memory ID
        """
        if not self._initialized:
            await self.initialize()
        
        # Add metadata
        content['source'] = source
        content['timestamp'] = datetime.now(timezone.utc).isoformat()
        content['status'] = MemoryStatus.ACTIVE.value
        
        # Detect cross-references if enabled
        if self.enable_cross_ref:
            content['cross_references'] = self._detect_cross_references(content)
        
        # Create episode
        episode_id = await self.client.add_episode(
            name=f"{source}: {content.get('title', 'Memory')}",
            episode_body=json.dumps(content),
            source=EpisodeType.json,
            source_description=source,
            group_id=self.group_id,
            reference_time=datetime.now(timezone.utc)
        )
        
        logger.info(f"Added memory to shared graph: {episode_id}")
        return episode_id
    
    def _detect_cross_references(self, content: dict) -> List[str]:
        """Detect connections between GTD and coding domains"""
        refs = []
        content_str = json.dumps(content).lower()
        
        # Coding to GTD references
        if 'docker' in content_str or 'deploy' in content_str:
            refs.append("@computer context")
            refs.append("deployment task")
        
        if 'tdd' in content_str or 'test' in content_str:
            refs.append("testing methodology")
            refs.append("quality practice")
        
        if 'python' in content_str:
            refs.append("python project")
            refs.append("@computer development")
        
        # GTD to coding references
        if 'task' in content_str or 'project' in content_str:
            refs.append("gtd workflow")
        
        if 'review' in content_str:
            refs.append("retrospective")
            refs.append("continuous improvement")
        
        return refs
    
    async def supersede_memory(self, old_id: str, new_content: dict, reason: str) -> str:
        """
        Mark old memory as superseded and create new one
        Preserves temporal history - never deletes
        
        Args:
            old_id: ID of memory to supersede
            new_content: New memory content
            reason: Reason for supersession
        
        Returns:
            New memory ID
        """
        if not self._initialized:
            await self.initialize()
        
        # Add supersession metadata
        new_content['supersedes'] = old_id
        new_content['supersession_reason'] = reason
        new_content['status'] = MemoryStatus.ACTIVE.value
        
        # Create new memory
        new_id = await self.add_memory(new_content, new_content.get('source', 'claude_code'))
        
        # Mark old memory as superseded (via observations)
        await self.client.add_observations(
            observations=[{
                "entityName": old_id,
                "contents": [
                    f"SUPERSEDED_BY: {new_id}",
                    f"REASON: {reason}",
                    f"STATUS: {MemoryStatus.SUPERSEDED.value}",
                    f"SUPERSEDED_AT: {datetime.now(timezone.utc).isoformat()}"
                ]
            }],
            group_id=self.group_id
        )
        
        # Create explicit supersession relationship
        await self.client.create_relations(
            relations=[{
                "from": new_id,
                "to": old_id,
                "relationType": "supersedes"
            }],
            group_id=self.group_id
        )
        
        logger.info(f"Superseded {old_id} with {new_id}: {reason}")
        return new_id
    
    async def search_with_temporal_weight(
        self, 
        query: str, 
        include_historical: bool = None,
        filter_source: str = None
    ) -> List[Any]:
        """
        Search with temporal weighting and status awareness
        
        Args:
            query: Search query
            include_historical: Include historical memories
            filter_source: Filter by source (claude_code, gtd_coach, etc.)
        
        Returns:
            Weighted and filtered search results
        """
        if not self._initialized:
            await self.initialize()
        
        if include_historical is None:
            include_historical = self.include_historical
        
        # Search in shared group
        results = await self.client.search(
            query,
            group_ids=[self.group_id],
            num_results=30  # Get more, then filter and weight
        )
        
        now = datetime.now(timezone.utc)
        weighted_results = []
        
        for result in results:
            # Parse result metadata
            try:
                if hasattr(result, 'episode_body'):
                    metadata = json.loads(result.episode_body)
                else:
                    metadata = {}
            except:
                metadata = {}
            
            # Apply temporal weighting
            if 'timestamp' in metadata:
                created_at = datetime.fromisoformat(metadata['timestamp'].replace('Z', '+00:00'))
                age_days = (now - created_at).days
                temporal_weight = self.decay_factor ** age_days
            else:
                temporal_weight = 0.5
            
            # Apply status weighting
            status = metadata.get('status', MemoryStatus.ACTIVE.value)
            status_weights = {
                MemoryStatus.ACTIVE.value: 1.0,
                MemoryStatus.SUPERSEDED.value: 0.3,
                MemoryStatus.HISTORICAL.value: 0.1,
                MemoryStatus.DEPRECATED.value: 0.0
            }
            status_weight = status_weights.get(status, 0.5)
            
            # Filter by status
            if status == MemoryStatus.DEPRECATED.value:
                continue
            if not include_historical and status == MemoryStatus.HISTORICAL.value:
                continue
            
            # Filter by source if requested
            if filter_source and metadata.get('source') != filter_source:
                continue
            
            # Calculate final score
            base_score = getattr(result, 'score', 0.5)
            final_score = base_score * temporal_weight * status_weight
            
            # Add to results
            result.final_score = final_score
            result.status = status
            result.metadata = metadata
            weighted_results.append(result)
        
        # Sort by final score
        weighted_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return weighted_results[:10]  # Return top 10
    
    async def find_cross_domain_insights(self, topic: str) -> List[Dict]:
        """
        Find insights that span GTD and coding domains
        
        Args:
            topic: Topic to search for
        
        Returns:
            List of cross-domain insights
        """
        if not self.enable_cross_ref:
            return []
        
        results = await self.search_with_temporal_weight(topic)
        
        insights = []
        for result in results:
            if hasattr(result, 'metadata'):
                cross_refs = result.metadata.get('cross_references', [])
                if cross_refs:
                    insights.append({
                        'memory_id': getattr(result, 'id', None),
                        'content': result.metadata,
                        'cross_references': cross_refs,
                        'score': result.final_score,
                        'domains': self._identify_domains(result.metadata)
                    })
        
        return insights
    
    def _identify_domains(self, metadata: dict) -> List[str]:
        """Identify which domains a memory belongs to"""
        domains = []
        
        source = metadata.get('source', '')
        if 'claude_code' in source:
            domains.append('coding')
        if 'gtd' in source:
            domains.append('productivity')
        
        # Check content for domain indicators
        content_str = json.dumps(metadata).lower()
        if any(word in content_str for word in ['task', 'project', 'review', 'weekly']):
            if 'productivity' not in domains:
                domains.append('productivity')
        if any(word in content_str for word in ['code', 'python', 'docker', 'test']):
            if 'coding' not in domains:
                domains.append('coding')
        
        return domains if domains else ['general']
    
    async def get_memory_evolution(self, topic: str) -> Dict[str, List]:
        """
        Get complete timeline of how understanding evolved
        
        Args:
            topic: Topic to trace evolution for
        
        Returns:
            Evolution tree showing supersession chains
        """
        # Get all related memories including historical
        all_memories = await self.search_with_temporal_weight(
            topic, 
            include_historical=True
        )
        
        evolution = {}
        
        for memory in all_memories:
            if hasattr(memory, 'metadata'):
                supersedes = memory.metadata.get('supersedes')
                if supersedes:
                    if supersedes not in evolution:
                        evolution[supersedes] = []
                    
                    evolution[supersedes].append({
                        'improved_to': getattr(memory, 'id', 'unknown'),
                        'reason': memory.metadata.get('supersession_reason', 'Unknown'),
                        'when': memory.metadata.get('timestamp', 'Unknown'),
                        'status': memory.status
                    })
        
        return evolution
    
    async def link_to_gtd_task(self, memory_id: str, task_id: str):
        """
        Link a memory to a GTD task
        
        Args:
            memory_id: Claude Code memory ID
            task_id: GTD task ID
        """
        if not self.enable_gtd:
            return
        
        if not self._initialized:
            await self.initialize()
        
        await self.client.create_relations(
            relations=[{
                "from": task_id,
                "to": memory_id,
                "relationType": "implemented_by"
            }],
            group_id=self.group_id
        )
        
        logger.info(f"Linked memory {memory_id} to GTD task {task_id}")
    
    async def close(self):
        """Close the Graphiti client connection"""
        if self.client:
            try:
                await self.client.close()
                logger.info("SharedMemory client closed")
            except Exception as e:
                logger.error(f"Error closing SharedMemory: {e}")
            finally:
                self._initialized = False


# Singleton instance
_shared_memory_instance = None


async def get_shared_memory() -> SharedMemory:
    """Get or create the singleton SharedMemory instance"""
    global _shared_memory_instance
    
    if _shared_memory_instance is None:
        _shared_memory_instance = SharedMemory()
        await _shared_memory_instance.initialize()
    
    return _shared_memory_instance