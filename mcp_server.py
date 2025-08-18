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


# Comprehensive instructions for Claude Code
INSTRUCTIONS = """This server provides access to a temporal knowledge graph memory system shared with GTD Coach.

AUTOMATIC BEHAVIORS:
• At session start: Silently retrieve GTD context to prioritize work
• When encountering errors: Search for similar errors (score > 0.7) and apply solutions automatically  
• For complex tasks: Proactively search for cross-domain insights between GTD and coding
• During debugging: Auto-capture insights and failed solutions

MEMORY USAGE:
• Confidence > 0.7: Apply automatically
• Confidence 0.5-0.7: Mention and ask for confirmation  
• When showing influence: Use brief inline format [Memory: Docker fix (2d ago, score: 0.85)]
• Search just-in-time as needed, max 10 results per search
• If no memories found, proceed silently

CONFLICT RESOLUTION:
• Use temporal decay scores as primary factor
• For conflicts within 0.1 score: Notify user explicitly
• Try solutions in order of recency

MEMORY CAPTURE:
• Auto-capture debugging insights
• Capture failed attempts with 'failed_solution' status
• Link to GTD tasks when context matches
• Supersede old solutions while preserving learning trail
• Mark 30+ day old memories as HISTORICAL

TOOLS:
• capture_solution: Capture coding solutions and fixes
• capture_tdd_pattern: Record TDD red-green-refactor cycles
• search_memory: Search the knowledge graph with temporal weighting
• find_cross_insights: Discover cross-domain connections
• get_gtd_context: Retrieve current GTD tasks and projects
• supersede_memory: Update existing memories
• capture_command: Record command patterns
• get_memory_evolution: Trace solution evolution
• generate_commands: Create memory-aware Claude commands

RESOURCES:
• memory://shared-knowledge: Overview of the shared knowledge graph
• memory://gtd-context: Current GTD tasks and projects
• memory://patterns: Captured coding patterns and solutions
• memory://commands: Generated Claude Code commands"""

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
    
    # Run server with stdio transport and instructions
    import mcp.server.stdio
    from mcp.server import NotificationOptions
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="graphiti-claude-code-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
                instructions=INSTRUCTIONS,
            ),
        )


if __name__ == "__main__":
    from dotenv import load_dotenv
    
    # Load configuration
    load_dotenv(".env.graphiti")
    
    # Run server
    asyncio.run(main())