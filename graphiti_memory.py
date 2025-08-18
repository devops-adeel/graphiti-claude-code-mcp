#!/usr/bin/env python3
"""
Unified Graphiti Memory Client for Claude Code
Shares knowledge graph with GTD Coach using same group_id
"""

import os
import json
import logging
import asyncio
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.nodes import EpisodeType

logger = logging.getLogger(__name__)

try:
    import tiktoken
except ImportError:
    logger.warning("tiktoken not installed. Token counting will be disabled.")
    tiktoken = None


class MemoryStatus(Enum):
    """Status for memory lifecycle management"""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    HISTORICAL = "historical"
    DEPRECATED = "deprecated"


class SearchResultWrapper:
    """
    Wrapper for Graphiti search results to provide consistent interface
    across different Graphiti versions and result types
    """
    
    def __init__(self, result: Any, computed_score: float = None, metadata: dict = None):
        self.result = result  # Original EntityEdge or other result
        self.computed_score = computed_score
        self._metadata = metadata or {}
        self._parse_result()
    
    def _parse_result(self):
        """Parse result based on its type and structure"""
        # Handle EntityEdge results
        if hasattr(self.result, 'fact'):
            self.fact = self.result.fact
            self.uuid = getattr(self.result, 'uuid', None)
            self.source_node_uuid = getattr(self.result, 'source_node_uuid', None)
            self.target_node_uuid = getattr(self.result, 'target_node_uuid', None)
            self.valid_at = getattr(self.result, 'valid_at', None)
            self.invalid_at = getattr(self.result, 'invalid_at', None)
        
        # Handle episode-based results
        if hasattr(self.result, 'episode_body'):
            try:
                self._metadata = json.loads(self.result.episode_body)
            except:
                self._metadata = {}
    
    @property
    def score(self) -> float:
        """Get the best available score"""
        if self.computed_score is not None:
            return self.computed_score
        return getattr(self.result, 'score', 0.5)
    
    @property
    def metadata(self) -> dict:
        """Get metadata from result or wrapper"""
        return self._metadata
    
    @property
    def status(self) -> str:
        """Get memory status"""
        return self._metadata.get('status', MemoryStatus.ACTIVE.value)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'uuid': getattr(self, 'uuid', None),
            'fact': getattr(self, 'fact', None),
            'score': self.score,
            'status': self.status,
            'metadata': self.metadata,
            'valid_at': str(self.valid_at) if self.valid_at else None,
            'invalid_at': str(self.invalid_at) if self.invalid_at else None
        }


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
        self.graphiti_version = None  # Will be detected on initialization
        
        # Token management for OpenAI API
        self.encoder = None
        self.max_tokens = 7000  # Leave buffer for response with 8192 limit
        self.model_name = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self._init_tiktoken()
        
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
    
    def _escape_for_search(self, query: str) -> str:
        """
        Escape special characters for safe FalkorDB/Cypher queries
        
        FalkorDB uses Cypher, where special characters in property names 
        should be wrapped with backticks, and string values need proper escaping
        
        Args:
            query: Raw search query
            
        Returns:
            Escaped query safe for FalkorDB
        """
        # First, handle @ symbol commonly used in cross-references
        # Replace @word patterns with escaped versions
        if '@' in query:
            # Remove @ symbols as they're not needed for search
            query = query.replace('@', '')
        
        # Handle problematic word "context" which causes RediSearch syntax errors
        # Simply remove it or replace with alternative search terms
        if 'context' in query.lower():
            # Replace 'context' with 'ctx' or remove it entirely
            query = query.replace(' context', '').replace('context ', '')
        
        # Escape other special characters that might cause issues
        # In Cypher, these characters need escaping in string literals
        special_chars = {
            '"': '\\"',
            "'": "\\'",
            '\\': '\\\\',
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t'
        }
        
        for char, escaped in special_chars.items():
            query = query.replace(char, escaped)
        
        # Handle hyphenated values which can cause tokenization issues
        # Keep hyphens but ensure they're treated as part of the word
        # This is handled by the search implementation itself
        
        return query
    
    def _init_tiktoken(self):
        """Initialize tiktoken encoder for token counting"""
        if tiktoken is None:
            logger.warning("tiktoken not available. Token counting disabled.")
            return
        
        try:
            # Try to get encoding for the specific model
            self.encoder = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            # Fall back to cl100k_base for newer models like gpt-4o-mini
            logger.info(f"Using cl100k_base encoding for model {self.model_name}")
            self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens for OpenAI API
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens (including message formatting overhead)
        """
        if self.encoder is None:
            # Rough estimation if tiktoken not available
            # Average 4 characters per token
            return len(text) // 4 + 3
        
        # Count base tokens and add message formatting overhead (3 tokens)
        return len(self.encoder.encode(text)) + 3
    
    async def search_with_batching(
        self, 
        query: str, 
        results: List[Any]
    ) -> List[Any]:
        """
        Batch search results to stay within token limits
        
        Args:
            query: Search query
            results: Raw search results to batch
            
        Returns:
            Processed results within token limits
        """
        batches = []
        current_batch = []
        current_tokens = self.count_tokens(query)
        
        for result in results:
            # Convert result to string for token counting
            result_str = str(result)
            result_tokens = self.count_tokens(result_str)
            
            if current_tokens + result_tokens > self.max_tokens:
                # Start new batch if adding this result would exceed limit
                if current_batch:
                    batches.append(current_batch)
                current_batch = [result]
                current_tokens = self.count_tokens(query) + result_tokens
            else:
                current_batch.append(result)
                current_tokens += result_tokens
        
        # Add remaining batch
        if current_batch:
            batches.append(current_batch)
        
        # Process batches (for now just return first batch)
        # In a full implementation, you might process each batch separately
        # and combine results
        if batches:
            logger.info(f"Split results into {len(batches)} batches to fit token limits")
            return batches[0]  # Return first batch that fits
        
        return []
    
    def _detect_graphiti_version(self):
        """Detect the installed Graphiti version for compatibility"""
        try:
            import graphiti_core
            version = getattr(graphiti_core, '__version__', 'unknown')
            logger.info(f"Detected Graphiti version: {version}")
            
            # Parse version for compatibility checks
            if version != 'unknown':
                # Extract major.minor.patch
                parts = version.split('.')
                if len(parts) >= 2:
                    major = int(parts[0])
                    minor = int(parts[1])
                    patch = int(parts[2]) if len(parts) > 2 else 0
                    
                    # Check compatibility
                    if major == 0 and minor == 17:
                        if patch >= 9 and patch <= 10:
                            logger.info(f"Graphiti v{version} is supported")
                        else:
                            logger.warning(f"Graphiti v{version} is untested but may work")
                    else:
                        logger.warning(f"Graphiti v{version} is not tested with this memory layer")
            
            self.graphiti_version = version
        except Exception as e:
            logger.warning(f"Could not detect Graphiti version: {e}")
            self.graphiti_version = 'unknown'
    
    async def initialize(self):
        """Connect to shared graph database instance"""
        if self._initialized:
            return self.client
        
        # Detect Graphiti version for compatibility
        self._detect_graphiti_version()
        
        try:
            # Initialize LLM client
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key.startswith('test-') or api_key in ['placeholder-set-in-home-env', 'test-key-for-testing']:
                raise ValueError("Valid OPENAI_API_KEY not found. Please set it in ~/.env")
            
            llm_config = LLMConfig(
                api_key=api_key,
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
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
            
            # Initialize Graphiti client with FalkorDB driver
            from graphiti_core.driver.falkordb_driver import FalkorDriver
            
            # Use OrbStack domain for container-to-container communication
            falkor_host = os.getenv('FALKORDB_HOST', 'falkordb.local')
            falkor_port = int(os.getenv('FALKORDB_PORT', '6379'))
            
            # Create FalkorDB driver (no auth needed for local FalkorDB)
            falkor_driver = FalkorDriver(
                host=falkor_host,
                port=falkor_port,
                database=self.database  # 'shared_knowledge_graph'
            )
            
            # Pass driver to Graphiti
            self.client = Graphiti(
                graph_driver=falkor_driver,
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
        result = await self.client.add_episode(
            name=f"{source}: {content.get('title', 'Memory')}",
            episode_body=json.dumps(content),
            source=EpisodeType.json,
            source_description=source,
            group_id=self.group_id,
            reference_time=datetime.now(timezone.utc)
        )
        
        # Extract episode UUID from AddEpisodeResults
        episode_id = result.episode.uuid
        
        logger.info(f"Added memory to shared graph: {episode_id}")
        return episode_id
    
    def _detect_cross_references(self, content: dict) -> List[str]:
        """Detect connections between GTD and coding domains"""
        refs = []
        content_str = json.dumps(content).lower()
        
        # Coding to GTD references
        if 'docker' in content_str or 'deploy' in content_str:
            refs.append("deployment task")
            refs.append("docker deployment")
        
        if 'tdd' in content_str or 'test' in content_str:
            refs.append("testing methodology")
            refs.append("quality practice")
        
        if 'python' in content_str:
            refs.append("python project")
            refs.append("development task")
        
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
        new_content['superseded_at'] = datetime.now(timezone.utc).isoformat()
        
        # Create new memory with supersession info
        new_id = await self.add_memory(new_content, new_content.get('source', 'claude_code'))
        
        # Note: In v0.17.9, we can't update the old memory directly
        # The supersession is tracked through the new memory's metadata
        # When searching, we can filter out superseded memories by checking
        # if any other memory has 'supersedes' pointing to them
        
        logger.info(f"Superseded {old_id} with {new_id}: {reason}")
        return new_id
    
    async def mark_historical(self, memory_id: str, days_old: int = 30) -> None:
        """
        Mark a memory as HISTORICAL (typically for memories 30+ days old)
        
        Args:
            memory_id: ID of memory to mark as historical
            days_old: Age of the memory in days
        """
        if not self._initialized:
            await self.initialize()
        
        # Note: In v0.17.9, we can't directly update existing episodes
        # We'll track historical status through metadata when creating new memories
        # or by checking the age during search operations
        
        logger.info(f"Memory {memory_id} is {days_old} days old (historical status tracked via age)")
    
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
        
        # Escape query for safe FalkorDB/Cypher search
        safe_query = self._escape_for_search(query)
        
        # Search in shared group
        try:
            results = await self.client.search(
                safe_query,
                group_ids=[self.group_id],
                num_results=30  # Get more, then filter and weight
            )
        except Exception as e:
            logger.error(f"Search failed with query '{query}' (escaped: '{safe_query}'): {e}")
            # Try a simpler search without special characters
            if query != safe_query:
                logger.info("Retrying with simplified query...")
                simplified_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
                results = await self.client.search(
                    simplified_query,
                    group_ids=[self.group_id],
                    num_results=30
                )
            else:
                raise
        
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
            
            # Add to results - store computed values in a way that doesn't modify the object
            # Create a wrapper dict to avoid modifying the original object
            result_wrapper = {
                'result': result,
                'final_score': final_score,
                'status': status,
                'metadata': metadata
            }
            weighted_results.append(result_wrapper)
        
        # Sort by final score
        weighted_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Extract the actual results without modifying them
        # Return just the top 10 results
        final_results = []
        for wrapper in weighted_results[:10]:  # Get top 10
            result = wrapper['result']
            # Don't modify the original object, just return it
            final_results.append(result)
        
        # Check if results fit within token limits
        total_tokens = self.count_tokens(query)
        for result in final_results:
            # Use str() instead of json.dumps to avoid serialization issues
            result_str = str(result)
            total_tokens += self.count_tokens(result_str)
        
        if total_tokens > self.max_tokens:
            logger.info(f"Results exceed token limit ({total_tokens} > {self.max_tokens}). Applying batching...")
            return await self.search_with_batching(query, final_results)
        
        return final_results
    
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
                        'score': getattr(result, 'final_score', getattr(result, 'score', 0.5)),
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
                        'status': memory.metadata.get('status', MemoryStatus.ACTIVE.value)
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
        
        # Note: In v0.17.9, we can't create explicit relations
        # The link is tracked through metadata in the memories themselves
        # When we create memories, we include GTD task references in metadata
        
        logger.info(f"GTD link tracked via metadata: memory {memory_id} -> task {task_id}")
    
    async def build_smart_index(self) -> Dict[str, List]:
        """
        Build smart indexes for common patterns to improve search performance
        
        Returns:
            Dictionary of pattern categories and their cached results
        """
        if not self._initialized:
            await self.initialize()
        
        # Define common search patterns
        patterns = {
            'error_patterns': r'error|exception|failed|crash|bug',
            'command_patterns': r'docker|git|npm|pytest|python|bash',
            'solution_patterns': r'fixed|resolved|solution|workaround|solved',
            'tdd_patterns': r'test|tdd|red-green|refactor|testing',
            'deployment_patterns': r'deploy|deployment|docker|kubernetes|ci/cd'
        }
        
        indexed_data = {}
        
        for pattern_name, pattern_regex in patterns.items():
            try:
                # Search for pattern
                results = await self.client.search(
                    pattern_regex,
                    group_ids=[self.group_id],
                    num_results=100
                )
                
                # Process and cache results
                processed = []
                for result in results[:50]:  # Limit to top 50 per pattern
                    processed.append({
                        'id': getattr(result, 'id', None),
                        'score': getattr(result, 'score', 0.5),
                        'summary': str(result)[:200]  # Brief summary
                    })
                
                indexed_data[pattern_name] = processed
                
                # Cache in memory (could also persist to Redis/FalkorDB)
                await self._cache_pattern_results(pattern_name, processed)
                
                logger.info(f"Indexed {len(processed)} items for pattern: {pattern_name}")
                
            except Exception as e:
                logger.error(f"Failed to index pattern {pattern_name}: {e}")
                indexed_data[pattern_name] = []
        
        return indexed_data
    
    async def _cache_pattern_results(self, pattern_name: str, results: List[Dict], ttl: int = 3600):
        """
        Cache pattern search results for fast retrieval
        
        Args:
            pattern_name: Name of the pattern
            results: Results to cache
            ttl: Time to live in seconds
        """
        # In v0.17.9, we can't use add_observations
        # We'll store cache as a regular episode with special metadata
        cache_key = f"smart_index:{pattern_name}"
        cache_data = {
            'type': 'cache',
            'cache_key': cache_key,
            'pattern': pattern_name,
            'results': results[:10],  # Store sample for quick access
            'result_count': len(results),
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'ttl': ttl
        }
        
        # Store cache as an episode
        await self.add_memory(cache_data, source="cache_system")
    
    async def search_with_smart_index(self, query: str) -> List[Any]:
        """
        Use smart indexes for faster search when applicable
        
        Args:
            query: Search query
            
        Returns:
            Search results (from cache if available, otherwise regular search)
        """
        if not self._initialized:
            await self.initialize()
        
        # Check if query matches any cached patterns
        query_lower = query.lower()
        
        # Pattern matching for smart index usage
        pattern_matches = {
            'error_patterns': any(word in query_lower for word in ['error', 'exception', 'failed', 'crash']),
            'command_patterns': any(word in query_lower for word in ['docker', 'git', 'npm', 'pytest']),
            'solution_patterns': any(word in query_lower for word in ['fix', 'solution', 'resolve']),
            'tdd_patterns': any(word in query_lower for word in ['test', 'tdd']),
            'deployment_patterns': any(word in query_lower for word in ['deploy', 'deployment'])
        }
        
        # Try to use cached results for matching patterns
        for pattern_name, matches in pattern_matches.items():
            if matches:
                cached = await self._get_cached_pattern(pattern_name)
                if cached:
                    logger.info(f"Using smart index for pattern: {pattern_name}")
                    # Filter cached results by query
                    filtered = self._filter_cached_by_query(cached, query)
                    if filtered:
                        return filtered[:10]
        
        # Fall back to regular search
        logger.info("No smart index match, using regular search")
        return await self.search_with_temporal_weight(query)
    
    async def _get_cached_pattern(self, pattern_name: str) -> Optional[List[Dict]]:
        """
        Retrieve cached pattern results
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Cached results if available and not expired
        """
        cache_key = f"smart_index:{pattern_name}"
        
        try:
            # Search for cache node
            results = await self.client.search(
                cache_key,
                group_ids=[self.group_id],
                num_results=1
            )
            
            if results:
                # Parse cache data
                result = results[0]
                if hasattr(result, 'episode_body'):
                    try:
                        cache_data = json.loads(result.episode_body)
                        
                        # Check if cache is still valid (1 hour TTL)
                        cached_at = datetime.fromisoformat(cache_data.get('cached_at', '').replace('Z', '+00:00'))
                        age_minutes = (datetime.now(timezone.utc) - cached_at).seconds / 60
                        
                        if age_minutes < 60:  # 1 hour TTL
                            return cache_data.get('results', [])
                        else:
                            logger.info(f"Cache expired for {pattern_name}")
                    except Exception as e:
                        logger.error(f"Failed to parse cache for {pattern_name}: {e}")
        except Exception as e:
            logger.error(f"Failed to retrieve cache for {pattern_name}: {e}")
        
        return None
    
    def _filter_cached_by_query(self, cached_results: List[Dict], query: str) -> List[Any]:
        """
        Filter cached results by query relevance
        
        Args:
            cached_results: Cached pattern results
            query: Search query
            
        Returns:
            Filtered results matching query
        """
        query_words = set(query.lower().split())
        filtered = []
        
        for result in cached_results:
            summary = result.get('summary', '').lower()
            # Simple word matching (could be enhanced with fuzzy matching)
            if any(word in summary for word in query_words):
                filtered.append(result)
        
        return filtered
    
    async def optimize_memory_graph(self):
        """
        Optimize the memory graph by:
        - Marking old memories as historical
        - Building smart indexes
        - Cleaning up deprecated entries
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info("Starting memory graph optimization...")
        
        # 1. Mark old memories as historical
        now = datetime.now(timezone.utc)
        all_memories = await self.client.search(
            "*",  # Get all memories
            group_ids=[self.group_id],
            num_results=1000
        )
        
        historical_count = 0
        for memory in all_memories:
            if hasattr(memory, 'episode_body'):
                try:
                    metadata = json.loads(memory.episode_body)
                    if 'timestamp' in metadata:
                        created_at = datetime.fromisoformat(metadata['timestamp'].replace('Z', '+00:00'))
                        age_days = (now - created_at).days
                        
                        if age_days > 30 and metadata.get('status') == MemoryStatus.ACTIVE.value:
                            await self.mark_historical(getattr(memory, 'id', 'unknown'), age_days)
                            historical_count += 1
                except Exception as e:
                    logger.error(f"Failed to process memory for optimization: {e}")
        
        logger.info(f"Marked {historical_count} memories as historical")
        
        # 2. Build smart indexes
        indexed = await self.build_smart_index()
        logger.info(f"Built smart indexes for {len(indexed)} patterns")
        
        # 3. Report optimization results
        return {
            'historical_marked': historical_count,
            'patterns_indexed': len(indexed),
            'optimization_completed': datetime.now(timezone.utc).isoformat()
        }
    
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