#!/usr/bin/env python3
"""
MCP Server for Claude Code Memory
Provides endpoints for memory operations with GTD integration
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource

from graphiti_memory import get_shared_memory, MemoryStatus
from capture import get_pattern_capture, PatternType
from commands import get_command_generator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize MCP server
server = Server("graphiti-claude-code-mcp")


@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available memory resources"""
    return [
        Resource(
            uri="memory://shared-knowledge",
            name="Shared Knowledge Graph",
            description=f"Access to shared knowledge graph: {os.getenv('GRAPHITI_GROUP_ID', 'shared_gtd_knowledge')}",
            mimeType="application/json"
        ),
        Resource(
            uri="memory://gtd-context", 
            name="GTD Context",
            description="Current GTD tasks and projects",
            mimeType="application/json"
        ),
        Resource(
            uri="memory://patterns",
            name="Captured Patterns",
            description="Coding patterns and solutions",
            mimeType="application/json"
        ),
        Resource(
            uri="memory://commands",
            name="Generated Commands",
            description="Claude Code commands with memory",
            mimeType="text/markdown"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a memory resource"""
    memory = await get_shared_memory()
    
    if uri == "memory://shared-knowledge":
        # Return overview of shared knowledge
        stats = {
            "group_id": memory.group_id,
            "database": memory.database,
            "total_memories": await _count_memories(memory),
            "sources": ["claude_code", "gtd_coach"],
            "features": {
                "temporal_weighting": True,
                "supersession_tracking": True,
                "cross_domain_search": memory.enable_cross_ref,
                "gtd_integration": memory.enable_gtd
            }
        }
        return json.dumps(stats, indent=2)
    
    elif uri == "memory://gtd-context":
        # Get current GTD context
        tasks = await memory.search_with_temporal_weight(
            "task @computer active",
            filter_source="gtd_coach"
        )
        projects = await memory.search_with_temporal_weight(
            "project active",
            filter_source="gtd_coach"
        )
        
        context = {
            "active_tasks": [_format_memory(t) for t in tasks[:5]],
            "active_projects": [_format_memory(p) for p in projects[:3]]
        }
        return json.dumps(context, indent=2)
    
    elif uri == "memory://patterns":
        # Get captured patterns
        capture = await get_pattern_capture()
        patterns = {}
        
        for pattern_type in PatternType:
            evolution = await capture.get_pattern_evolution(pattern_type)
            patterns[pattern_type.value] = {
                "active": evolution.get("active_patterns", 0),
                "superseded": evolution.get("superseded_patterns", 0),
                "total": evolution.get("total_iterations", 0)
            }
        
        return json.dumps(patterns, indent=2)
    
    elif uri == "memory://commands":
        # Return generated commands index
        generator = await get_command_generator()
        index = await generator.generate_all_commands()
        return index
    
    else:
        raise ValueError(f"Unknown resource: {uri}")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available memory tools"""
    return [
        Tool(
            name="capture_solution",
            description="Capture a coding solution or fix",
            inputSchema={
                "type": "object",
                "properties": {
                    "error": {"type": "string", "description": "Error or problem description"},
                    "solution": {"type": "string", "description": "Solution that worked"},
                    "context": {"type": "object", "description": "Additional context"},
                    "gtd_task_id": {"type": "string", "description": "Optional GTD task ID to link"}
                },
                "required": ["error", "solution"]
            }
        ),
        Tool(
            name="capture_tdd_pattern",
            description="Capture TDD red-green-refactor pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_code": {"type": "string", "description": "Test code (red phase)"},
                    "implementation": {"type": "string", "description": "Implementation (green phase)"},
                    "refactored": {"type": "string", "description": "Refactored code (optional)"},
                    "feature_name": {"type": "string", "description": "Feature name"}
                },
                "required": ["test_code", "feature_name"]
            }
        ),
        Tool(
            name="search_memory",
            description="Search shared knowledge graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "include_historical": {"type": "boolean", "description": "Include historical memories"},
                    "filter_source": {"type": "string", "description": "Filter by source (claude_code, gtd_coach)"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="find_cross_insights",
            description="Find cross-domain insights between GTD and coding",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic to explore"}
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="get_gtd_context",
            description="Get current GTD context for coding session",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="supersede_memory",
            description="Mark old memory as superseded by new one",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_id": {"type": "string", "description": "ID of memory to supersede"},
                    "new_content": {"type": "object", "description": "New memory content"},
                    "reason": {"type": "string", "description": "Reason for supersession"}
                },
                "required": ["old_id", "new_content", "reason"]
            }
        ),
        Tool(
            name="capture_command",
            description="Capture frequently used command pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command that was run"},
                    "context": {"type": "string", "description": "Context where useful"},
                    "success": {"type": "boolean", "description": "Whether it succeeded"},
                    "output": {"type": "string", "description": "Command output (optional)"}
                },
                "required": ["command", "context", "success"]
            }
        ),
        Tool(
            name="get_memory_evolution",
            description="Get evolution history of a topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic to trace evolution"}
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="generate_commands",
            description="Generate Claude Code commands with memory",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a memory tool"""
    memory = await get_shared_memory()
    capture = await get_pattern_capture()
    
    if name == "capture_solution":
        # Capture deployment/coding solution
        memory_id = await capture.capture_deployment_solution(
            error=arguments["error"],
            solution=arguments["solution"],
            context=arguments.get("context", {})
        )
        
        # Link to GTD if provided
        if arguments.get("gtd_task_id"):
            await memory.link_to_gtd_task(memory_id, arguments["gtd_task_id"])
        
        return {
            "status": "success",
            "memory_id": memory_id,
            "message": f"Captured solution: {memory_id}"
        }
    
    elif name == "capture_tdd_pattern":
        # Capture TDD pattern
        memory_id = await capture.capture_tdd_cycle(
            test_code=arguments["test_code"],
            implementation=arguments.get("implementation"),
            refactored=arguments.get("refactored"),
            feature_name=arguments["feature_name"]
        )
        
        return {
            "status": "success",
            "memory_id": memory_id,
            "message": f"Captured TDD pattern for {arguments['feature_name']}"
        }
    
    elif name == "search_memory":
        # Search shared knowledge
        results = await memory.search_with_temporal_weight(
            query=arguments["query"],
            include_historical=arguments.get("include_historical", False),
            filter_source=arguments.get("filter_source")
        )
        
        return {
            "status": "success",
            "count": len(results),
            "results": [_format_memory(r) for r in results]
        }
    
    elif name == "find_cross_insights":
        # Find cross-domain insights
        insights = await memory.find_cross_domain_insights(arguments["topic"])
        
        return {
            "status": "success",
            "insights": insights,
            "message": f"Found {len(insights)} cross-domain insights"
        }
    
    elif name == "get_gtd_context":
        # Get GTD context
        tasks = await memory.search_with_temporal_weight(
            "@computer task active",
            filter_source="gtd_coach"
        )
        projects = await memory.search_with_temporal_weight(
            "project active",
            filter_source="gtd_coach"
        )
        reviews = await memory.search_with_temporal_weight(
            "review insight",
            filter_source="gtd_coach"
        )
        
        return {
            "status": "success",
            "context": {
                "active_tasks": [_format_memory(t) for t in tasks[:5]],
                "active_projects": [_format_memory(p) for p in projects[:3]],
                "recent_insights": [_format_memory(r) for r in reviews[:3]]
            }
        }
    
    elif name == "supersede_memory":
        # Supersede old memory
        new_id = await memory.supersede_memory(
            old_id=arguments["old_id"],
            new_content=arguments["new_content"],
            reason=arguments["reason"]
        )
        
        return {
            "status": "success",
            "new_id": new_id,
            "message": f"Superseded {arguments['old_id']} with {new_id}"
        }
    
    elif name == "capture_command":
        # Capture command pattern
        memory_id = await capture.capture_command_pattern(
            command=arguments["command"],
            context=arguments["context"],
            success=arguments["success"],
            output=arguments.get("output")
        )
        
        return {
            "status": "success",
            "memory_id": memory_id,
            "message": f"Captured command pattern: {memory_id}"
        }
    
    elif name == "get_memory_evolution":
        # Get evolution history
        evolution = await memory.get_memory_evolution(arguments["topic"])
        
        return {
            "status": "success",
            "evolution": evolution,
            "chains": len(evolution)
        }
    
    elif name == "generate_commands":
        # Generate Claude commands
        generator = await get_command_generator()
        await generator.generate_all_commands()
        
        return {
            "status": "success",
            "message": f"Generated commands in ~/.claude/commands/",
            "commands": [
                "/tdd-feature",
                "/check-deployment",
                "/fix-docker",
                "/project-structure",
                "/search-memory"
            ]
        }
    
    else:
        raise ValueError(f"Unknown tool: {name}")


def _format_memory(memory: Any) -> Dict[str, Any]:
    """Format memory for output"""
    metadata = getattr(memory, 'metadata', {})
    
    return {
        "id": getattr(memory, 'id', None),
        "title": metadata.get("title", "Untitled"),
        "source": metadata.get("source", "unknown"),
        "status": getattr(memory, "status", "unknown"),
        "score": getattr(memory, "final_score", 0),
        "timestamp": metadata.get("timestamp", None),
        "cross_references": metadata.get("cross_references", []),
        "content_preview": str(metadata)[:200] + "..." if len(str(metadata)) > 200 else str(metadata)
    }


async def _count_memories(memory) -> int:
    """Estimate total memories in group"""
    try:
        # Do a broad search to estimate count
        results = await memory.search_with_temporal_weight(
            "*",  # Broad search
            include_historical=True
        )
        return len(results)
    except:
        return 0


async def main():
    """Run the MCP server"""
    logger.info("Starting Graphiti Claude Code MCP Server")
    logger.info(f"Shared group_id: {os.getenv('GRAPHITI_GROUP_ID', 'shared_gtd_knowledge')}")
    
    # Initialize components
    memory = await get_shared_memory()
    capture = await get_pattern_capture()
    generator = await get_command_generator()
    
    logger.info("✅ All components initialized")
    logger.info("MCP Server ready for connections")
    
    # Run server
    await server.run()


if __name__ == "__main__":
    from dotenv import load_dotenv
    
    # Load configuration
    load_dotenv(".env.graphiti")
    
    # Run server
    asyncio.run(main())