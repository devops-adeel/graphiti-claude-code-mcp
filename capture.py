#!/usr/bin/env python3
"""
Pattern Capture Logic for Claude Code Memory
Captures coding patterns, solutions, and links to GTD tasks
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum

from graphiti_memory import get_shared_memory, MemoryStatus

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of patterns to capture"""
    TDD_CYCLE = "tdd_cycle"
    DEPLOYMENT_SOLUTION = "deployment_solution"
    DOCKER_FIX = "docker_fix"
    TEST_PATTERN = "test_pattern"
    PROJECT_STRUCTURE = "project_structure"
    COMMAND_PATTERN = "command_pattern"
    DEBUG_SOLUTION = "debug_solution"


class PatternCapture:
    """Captures and stores coding patterns in shared knowledge graph"""
    
    def __init__(self):
        self.memory = None
        self.active_tdd_cycle = {}
        self.solution_history = {}
    
    async def initialize(self):
        """Initialize connection to shared memory"""
        self.memory = await get_shared_memory()
        logger.info("PatternCapture initialized with shared memory")
    
    async def capture_tdd_cycle(
        self,
        test_code: str,
        implementation: str = None,
        refactored: str = None,
        feature_name: str = None
    ) -> str:
        """
        Capture complete TDD red-green-refactor cycle
        
        Args:
            test_code: Failing test code (red phase)
            implementation: Minimal passing code (green phase)
            refactored: Refactored code (refactor phase)
            feature_name: Name of feature being developed
        
        Returns:
            Memory ID
        """
        cycle_data = {
            'type': PatternType.TDD_CYCLE.value,
            'title': f"TDD Pattern: {feature_name or 'Feature'}",
            'red_phase': test_code,
            'green_phase': implementation,
            'refactor_phase': refactored,
            'feature': feature_name,
            'methodology': 'TDD',
            'language': 'python',
            'test_framework': 'pytest',
            'gtd_link': f"@computer TDD {feature_name}" if feature_name else None
        }
        
        # Store in active cycles for potential updates
        if feature_name:
            self.active_tdd_cycle[feature_name] = cycle_data
        
        memory_id = await self.memory.add_memory(cycle_data, source="claude_code")
        logger.info(f"Captured TDD cycle for {feature_name}: {memory_id}")
        
        return memory_id
    
    async def capture_deployment_solution(
        self,
        error: str,
        solution: str,
        context: Dict[str, Any],
        docker_compose: str = None
    ) -> str:
        """
        Capture deployment solutions, especially Docker/OrbStack fixes
        
        Args:
            error: Error message or description
            solution: Solution that worked
            context: Additional context (env vars, config, etc.)
            docker_compose: Docker compose configuration if relevant
        
        Returns:
            Memory ID
        """
        # Check for existing solutions to this error
        existing = await self._find_similar_solution(error)
        
        solution_data = {
            'type': PatternType.DEPLOYMENT_SOLUTION.value,
            'title': f"Fix: {error[:50]}...",
            'error': error,
            'solution': solution,
            'context': {
                'orbstack': True,
                'docker_compose': docker_compose,
                'falkordb_port': 6380,
                'environment': context
            },
            'success_count': 1,
            'gtd_link': '@computer deployment fix'
        }
        
        if existing and existing[0].final_score > 0.8:
            # Supersede existing solution
            old_id = existing[0].metadata.get('id') or getattr(existing[0], 'id', None)
            if old_id:
                memory_id = await self.memory.supersede_memory(
                    old_id,
                    solution_data,
                    f"Improved solution: {solution[:100]}"
                )
                logger.info(f"Superseded deployment solution {old_id} with {memory_id}")
            else:
                memory_id = await self.memory.add_memory(solution_data, source="claude_code")
        else:
            # New solution
            memory_id = await self.memory.add_memory(solution_data, source="claude_code")
            logger.info(f"Captured new deployment solution: {memory_id}")
        
        # Track in history
        self.solution_history[error[:50]] = memory_id
        
        return memory_id
    
    async def capture_docker_fix(
        self,
        build_error: str,
        fix: str,
        dockerfile_snippet: str = None,
        compose_snippet: str = None
    ) -> str:
        """
        Capture Docker-specific fixes
        
        Args:
            build_error: Docker build error
            fix: Fix that resolved the issue
            dockerfile_snippet: Relevant Dockerfile snippet
            compose_snippet: Relevant docker-compose snippet
        
        Returns:
            Memory ID
        """
        docker_data = {
            'type': PatternType.DOCKER_FIX.value,
            'title': f"Docker Fix: {build_error[:40]}...",
            'error': build_error,
            'fix': fix,
            'dockerfile': dockerfile_snippet,
            'docker_compose': compose_snippet,
            'orbstack_compatible': True,
            'port_configuration': '6380',  # Your FalkorDB port
            'gtd_link': '@computer docker troubleshooting'
        }
        
        memory_id = await self.memory.add_memory(docker_data, source="claude_code")
        logger.info(f"Captured Docker fix: {memory_id}")
        
        return memory_id
    
    async def capture_test_pattern(
        self,
        pattern_name: str,
        test_code: str,
        fixtures: List[str] = None,
        assertions: List[str] = None
    ) -> str:
        """
        Capture reusable test patterns and assertions
        
        Args:
            pattern_name: Name of the test pattern
            test_code: Test code example
            fixtures: List of pytest fixtures used
            assertions: Common assertion patterns
        
        Returns:
            Memory ID
        """
        test_data = {
            'type': PatternType.TEST_PATTERN.value,
            'title': f"Test Pattern: {pattern_name}",
            'pattern': pattern_name,
            'code': test_code,
            'fixtures': fixtures or [],
            'assertions': assertions or [],
            'framework': 'pytest',
            'methodology': 'TDD',
            'gtd_link': 'testing best practices'
        }
        
        memory_id = await self.memory.add_memory(test_data, source="claude_code")
        logger.info(f"Captured test pattern {pattern_name}: {memory_id}")
        
        return memory_id
    
    async def capture_project_structure(
        self,
        structure: Dict[str, Any],
        description: str = None
    ) -> str:
        """
        Capture preferred project structure patterns
        
        Args:
            structure: Dictionary representing folder structure
            description: Description of the structure
        
        Returns:
            Memory ID
        """
        structure_data = {
            'type': PatternType.PROJECT_STRUCTURE.value,
            'title': 'Project Structure Pattern',
            'structure': structure,
            'description': description or 'Minimal, clean root-level structure',
            'preferences': {
                'root_level': 'minimal',
                'tests': 'separate tests/ directory',
                'monorepo': 'start with monorepo',
                'clean': True
            },
            'gtd_link': 'project organization'
        }
        
        memory_id = await self.memory.add_memory(structure_data, source="claude_code")
        logger.info(f"Captured project structure: {memory_id}")
        
        return memory_id
    
    async def capture_command_pattern(
        self,
        command: str,
        context: str,
        success: bool,
        output: str = None
    ) -> str:
        """
        Capture frequently used commands and their contexts
        
        Args:
            command: Command that was run
            context: Context where command is useful
            success: Whether command succeeded
            output: Command output if relevant
        
        Returns:
            Memory ID
        """
        command_data = {
            'type': PatternType.COMMAND_PATTERN.value,
            'title': f"Command: {command[:30]}...",
            'command': command,
            'context': context,
            'success': success,
            'output': output[:500] if output else None,
            'frequency': 1,
            'gtd_link': '@computer command reference'
        }
        
        # Check for existing command pattern
        existing = await self.memory.search_with_temporal_weight(
            f"command: {command}",
            filter_source="claude_code"
        )
        
        if existing and existing[0].final_score > 0.9:
            # Update frequency count
            old_data = existing[0].metadata
            old_data['frequency'] = old_data.get('frequency', 1) + 1
            old_data['last_used'] = datetime.now(timezone.utc).isoformat()
            
            memory_id = await self.memory.supersede_memory(
                getattr(existing[0], 'id', None),
                old_data,
                f"Updated frequency: {old_data['frequency']}"
            )
        else:
            memory_id = await self.memory.add_memory(command_data, source="claude_code")
        
        logger.info(f"Captured command pattern: {memory_id}")
        return memory_id
    
    async def link_to_gtd_task(self, memory_id: str, task_description: str) -> Optional[str]:
        """
        Link a captured pattern to a GTD task
        
        Args:
            memory_id: Memory ID to link
            task_description: Description to find GTD task
        
        Returns:
            GTD task ID if found and linked
        """
        # Search for GTD task
        gtd_tasks = await self.memory.search_with_temporal_weight(
            task_description,
            filter_source="gtd_coach"
        )
        
        if gtd_tasks:
            task_id = getattr(gtd_tasks[0], 'id', None)
            if task_id:
                await self.memory.link_to_gtd_task(memory_id, task_id)
                logger.info(f"Linked memory {memory_id} to GTD task {task_id}")
                return task_id
        
        return None
    
    async def _find_similar_solution(self, error: str) -> List[Any]:
        """Find similar solutions to an error"""
        return await self.memory.search_with_temporal_weight(
            f"error: {error[:50]}",
            filter_source="claude_code"
        )
    
    async def get_pattern_evolution(self, pattern_type: PatternType) -> Dict[str, Any]:
        """
        Get evolution history of a pattern type
        
        Args:
            pattern_type: Type of pattern to trace
        
        Returns:
            Evolution history
        """
        evolution = await self.memory.get_memory_evolution(pattern_type.value)
        
        # Add statistics
        stats = {
            'total_iterations': len(evolution),
            'active_patterns': 0,
            'superseded_patterns': 0,
            'evolution_tree': evolution
        }
        
        # Count statuses
        all_patterns = await self.memory.search_with_temporal_weight(
            f"type: {pattern_type.value}",
            include_historical=True
        )
        
        for pattern in all_patterns:
            if pattern.status == MemoryStatus.ACTIVE.value:
                stats['active_patterns'] += 1
            elif pattern.status == MemoryStatus.SUPERSEDED.value:
                stats['superseded_patterns'] += 1
        
        return stats


# Singleton instance
_capture_instance = None


async def get_pattern_capture() -> PatternCapture:
    """Get or create singleton PatternCapture instance"""
    global _capture_instance
    
    if _capture_instance is None:
        _capture_instance = PatternCapture()
        await _capture_instance.initialize()
    
    return _capture_instance