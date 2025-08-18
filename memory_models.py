#!/usr/bin/env python3
"""
Pydantic models for memory metadata validation
Ensures consistent structure across all memory operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class MemoryType(str, Enum):
    """Types of memories stored in the knowledge graph"""
    TDD_CYCLE = "tdd_cycle"
    DEPLOYMENT_SOLUTION = "deployment_solution"
    DOCKER_FIX = "docker_fix"
    TEST_PATTERN = "test_pattern"
    PROJECT_STRUCTURE = "project_structure"
    COMMAND_PATTERN = "command_pattern"
    DEBUG_SOLUTION = "debug_solution"
    GTD_TASK = "gtd_task"
    GTD_PROJECT = "gtd_project"
    GENERAL = "general"


class MemoryStatus(str, Enum):
    """Memory lifecycle status"""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    HISTORICAL = "historical"
    DEPRECATED = "deprecated"


class BaseMemoryMetadata(BaseModel):
    """Base model for all memory metadata"""
    model_config = ConfigDict(use_enum_values=True)
    
    type: MemoryType = Field(default=MemoryType.GENERAL)
    title: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    source: str = Field(default="claude_code")
    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    gtd_link: Optional[str] = None
    cross_references: List[str] = Field(default_factory=list)


class TDDCycleMetadata(BaseMemoryMetadata):
    """Metadata for TDD cycle patterns"""
    type: Literal[MemoryType.TDD_CYCLE] = Field(default=MemoryType.TDD_CYCLE)
    red_phase: str = Field(..., description="Failing test code")
    green_phase: Optional[str] = Field(None, description="Minimal passing code")
    refactor_phase: Optional[str] = Field(None, description="Refactored code")
    feature: str = Field(..., description="Feature name")
    language: str = Field(default="python")
    test_framework: str = Field(default="pytest")


class DeploymentSolutionMetadata(BaseMemoryMetadata):
    """Metadata for deployment solutions"""
    type: Literal[MemoryType.DEPLOYMENT_SOLUTION] = Field(default=MemoryType.DEPLOYMENT_SOLUTION)
    error: str = Field(..., description="Error encountered")
    solution: str = Field(..., description="Solution that worked")
    context: Dict[str, Any] = Field(default_factory=dict)
    success_count: int = Field(default=1)
    docker_compose: Optional[str] = None
    
    @field_validator('context')
    @classmethod
    def validate_context(cls, v):
        """Ensure context is serializable"""
        import json
        try:
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Context must be JSON serializable: {e}")
        return v


class DockerFixMetadata(BaseMemoryMetadata):
    """Metadata for Docker-specific fixes"""
    type: Literal[MemoryType.DOCKER_FIX] = Field(default=MemoryType.DOCKER_FIX)
    error: str = Field(..., description="Docker error")
    fix: str = Field(..., description="Fix that resolved the issue")
    dockerfile: Optional[str] = None
    docker_compose: Optional[str] = None
    orbstack_compatible: bool = Field(default=True)
    port_configuration: Optional[str] = None


class CommandPatternMetadata(BaseMemoryMetadata):
    """Metadata for command patterns"""
    type: Literal[MemoryType.COMMAND_PATTERN] = Field(default=MemoryType.COMMAND_PATTERN)
    command: str = Field(..., description="Command that was run")
    context: str = Field(..., description="Context where useful")
    success: bool = Field(..., description="Whether it succeeded")
    output: Optional[str] = None
    frequency: int = Field(default=1)


class SupersessionMetadata(BaseMemoryMetadata):
    """Metadata for superseded memories"""
    supersedes: str = Field(..., description="UUID of superseded memory")
    supersession_reason: str = Field(..., description="Reason for supersession")
    superseded_at: datetime = Field(default_factory=datetime.utcnow)
    improvements: List[str] = Field(default_factory=list)


class GTDTaskMetadata(BaseMemoryMetadata):
    """Metadata for GTD tasks"""
    type: Literal[MemoryType.GTD_TASK] = Field(default=MemoryType.GTD_TASK)
    task_id: str = Field(..., description="GTD task identifier")
    context: str = Field(..., description="GTD context (@computer, @home, etc)")
    project: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    completed: bool = Field(default=False)


class MetadataFactory:
    """Factory for creating appropriate metadata models"""
    
    @staticmethod
    def create_metadata(memory_type: str, data: dict) -> BaseMemoryMetadata:
        """Create appropriate metadata model based on type"""
        type_map = {
            MemoryType.TDD_CYCLE: TDDCycleMetadata,
            MemoryType.DEPLOYMENT_SOLUTION: DeploymentSolutionMetadata,
            MemoryType.DOCKER_FIX: DockerFixMetadata,
            MemoryType.COMMAND_PATTERN: CommandPatternMetadata,
            MemoryType.GTD_TASK: GTDTaskMetadata,
        }
        
        model_class = type_map.get(memory_type, BaseMemoryMetadata)
        return model_class(**data)
    
    @staticmethod
    def validate_metadata(data: dict) -> dict:
        """Validate and clean metadata for storage"""
        # Determine type
        memory_type = data.get('type', MemoryType.GENERAL)
        
        # Create model for validation
        metadata = MetadataFactory.create_metadata(memory_type, data)
        
        # Return validated dict
        return metadata.model_dump()