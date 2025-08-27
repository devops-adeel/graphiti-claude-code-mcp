#!/usr/bin/env ./venv/bin/python
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
from langfuse.langfuse_analyzer import get_langfuse_analyzer

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Langfuse for trace tagging (only if configured)
try:
    from langfuse import Langfuse
    from langfuse.decorators import observe
    # Initialize Langfuse client if API keys are available
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        langfuse_client = Langfuse()
        LANGFUSE_ENABLED = True
        logger.info("Langfuse tracing enabled for MCP server")
    else:
        langfuse_client = None
        LANGFUSE_ENABLED = False
        logger.info("Langfuse tracing disabled - no API keys configured")
except ImportError:
    langfuse_client = None
    LANGFUSE_ENABLED = False
    logger.info("Langfuse not installed - tracing disabled")


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
• analyze_langfuse_traces: Analyze recent Langfuse traces
• analyze_phase_transitions: Analyze GTD phase transitions
• validate_state_continuity: Validate state continuity across traces
• analyze_test_failure: Analyze test failures from traces
• detect_interrupt_patterns: Detect interrupt patterns in traces
• predict_trace_issues: Predict potential issues in traces
• debug_langfuse_session: Debug a specific Langfuse session
• monitor_active_traces: Monitor active traces in real-time

RESOURCES:
• memory://shared-knowledge: Overview of the shared knowledge graph
• memory://gtd-context: Current GTD tasks and projects
• memory://patterns: Captured coding patterns and solutions
• memory://commands: Generated Claude Code commands
• langfuse://traces: Recent trace data from the last 24 hours
• langfuse://patterns: Detected patterns from traces stored in Graphiti
• langfuse://sessions: Active session information
• langfuse://predictions: Current predictions and confidence scores"""

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
        ),
        # Langfuse trace analysis resources
        Resource(
            uri="langfuse://traces",
            name="Recent Traces",
            description="Recent Langfuse trace data from the last 24 hours",
            mimeType="application/json"
        ),
        Resource(
            uri="langfuse://patterns",
            name="Detected Patterns",
            description="Patterns detected from Langfuse traces stored in Graphiti",
            mimeType="application/json"
        ),
        Resource(
            uri="langfuse://sessions",
            name="Active Sessions",
            description="Active Langfuse session information",
            mimeType="application/json"
        ),
        Resource(
            uri="langfuse://predictions",
            name="Trace Predictions",
            description="Current predictions and confidence scores for trace issues",
            mimeType="application/json"
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
    
    # Langfuse trace analysis resources
    elif uri == "langfuse://traces":
        # Get recent traces from last 24 hours
        analyzer = await get_langfuse_analyzer()
        result = await analyzer.analyze_recent_traces(hours_back=24)
        return json.dumps({
            "traces_analyzed": result.get("traces_analyzed", 0),
            "errors": result.get("errors", []),
            "interrupts": result.get("interrupts", []),
            "patterns": result.get("patterns", []),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    
    elif uri == "langfuse://patterns":
        # Get patterns detected from Langfuse traces stored in Graphiti
        memory = await get_shared_memory()
        patterns = await memory.search_with_temporal_weight(
            "langfuse pattern detected",
            filter_source="claude_code"
        )
        return json.dumps({
            "detected_patterns": [_format_memory(p) for p in patterns[:20]],
            "total_patterns": len(patterns),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    
    elif uri == "langfuse://sessions":
        # Get active session information
        analyzer = await get_langfuse_analyzer()
        # Get traces from last hour to find active sessions
        result = await analyzer.analyze_recent_traces(hours_back=1)
        sessions = {}
        for trace in result.get("traces", []):
            session_id = trace.get("session_id", "unknown")
            if session_id not in sessions:
                sessions[session_id] = {
                    "trace_count": 0,
                    "error_count": 0,
                    "latest_timestamp": None
                }
            sessions[session_id]["trace_count"] += 1
            if trace.get("has_errors"):
                sessions[session_id]["error_count"] += 1
            timestamp = trace.get("timestamp")
            if timestamp and (not sessions[session_id]["latest_timestamp"] or 
                             timestamp > sessions[session_id]["latest_timestamp"]):
                sessions[session_id]["latest_timestamp"] = timestamp
        
        return json.dumps({
            "active_sessions": sessions,
            "total_sessions": len(sessions),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    
    elif uri == "langfuse://predictions":
        # Get current predictions and confidence scores
        analyzer = await get_langfuse_analyzer()
        # Analyze recent traces for predictions
        result = await analyzer.analyze_recent_traces(hours_back=1)
        predictions = []
        
        for pattern in result.get("patterns", []):
            if pattern.get("confidence", 0) > 0.5:
                predictions.append({
                    "pattern": pattern.get("signature"),
                    "confidence": pattern.get("confidence"),
                    "resolution": pattern.get("resolution"),
                    "trace_id": pattern.get("trace_id")
                })
        
        return json.dumps({
            "predictions": sorted(predictions, key=lambda x: x["confidence"], reverse=True),
            "high_confidence_count": len([p for p in predictions if p["confidence"] > 0.8]),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    
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
        ),
        
        # Langfuse Trace Analysis Tools
        Tool(
            name="analyze_langfuse_traces",
            description="Analyze recent Langfuse traces and detect patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours_back": {"type": "integer", "description": "Hours to look back (default: 1)"},
                    "session_id": {"type": "string", "description": "Optional specific session to analyze"},
                    "project": {"type": "string", "description": "Optional project name for filtering"}
                },
                "required": []
            }
        ),
        Tool(
            name="analyze_phase_transitions",
            description="Analyze phase transitions for state loss detection",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string", "description": "Specific trace to analyze"},
                    "session_id": {"type": "string", "description": "Session to analyze all traces"}
                },
                "required": []
            }
        ),
        Tool(
            name="validate_state_continuity",
            description="Validate state continuity across observations",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string", "description": "Specific trace to validate"},
                    "session_id": {"type": "string", "description": "Session to validate all traces"}
                },
                "required": []
            }
        ),
        Tool(
            name="analyze_test_failure",
            description="Analyze test failure session with AI-optimized output",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Test session ID to analyze"},
                    "return_patterns": {"type": "boolean", "description": "Whether to detect patterns (default: true)"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="detect_interrupt_patterns",
            description="Detect interrupt patterns in traces",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours_back": {"type": "integer", "description": "Hours to look back (default: 1)"},
                    "session_id": {"type": "string", "description": "Optional specific session"}
                },
                "required": []
            }
        ),
        Tool(
            name="predict_trace_issues",
            description="Predict potential issues based on historical patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string", "description": "Trace to analyze"},
                    "threshold": {"type": "number", "description": "Confidence threshold (default: 0.7)"}
                },
                "required": ["trace_id"]
            }
        ),
        Tool(
            name="debug_langfuse_session",
            description="Comprehensive debug mode for a session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID to debug"},
                    "focus": {"type": "string", "description": "Focus area: transitions, prompts, conversation, state, or all (default: all)"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="monitor_active_traces",
            description="Monitor active traces in real-time",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Optional project to monitor"},
                    "interval_seconds": {"type": "integer", "description": "Monitoring interval (default: 30)"}
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a memory tool"""
    # Initialize trace context
    trace = None
    span = None
    
    # Tag this operation as MCP-internal if Langfuse is enabled
    if LANGFUSE_ENABLED and langfuse_client:
        # Create a trace with MCP tags to prevent analysis loops
        trace = langfuse_client.trace(
            name=f"mcp_tool_{name}",
            tags=[
                os.getenv("MCP_TRACE_TAG", "mcp-internal"),
                os.getenv("MCP_ANALYZER_TAG", "mcp-analyzer"),
                f"tool:{name}"
            ],
            metadata={
                "source": os.getenv("MCP_SOURCE_IDENTIFIER", "mcp-server"),
                "component": "tool-handler",
                "tool": name,
                "version": os.getenv("MCP_COMPONENT_VERSION", "1.0.0"),
                "arguments": arguments  # Include arguments for debugging
            }
        )
        
        # Start a span for the specific tool execution
        span = trace.span(
            name=f"execute_{name}",
            metadata={"tool": name}
        )
    
    try:
        memory = await get_shared_memory()
        capture = await get_pattern_capture()
        
        result = None
        
        # Create sub-spans for Graphiti operations if tracing is enabled
        if name == "capture_solution":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_capture_solution",
                    metadata={"error": arguments["error"][:100] if "error" in arguments else None}
                )
            
            # Capture deployment/coding solution
            memory_id = await capture.capture_deployment_solution(
                error=arguments["error"],
                solution=arguments["solution"],
                context=arguments.get("context", {})
            )
            
            # Link to GTD if provided
            if arguments.get("gtd_task_id"):
                await memory.link_to_gtd_task(memory_id, arguments["gtd_task_id"])
            
            if span:
                graphiti_span.end()
            
            result = {
                "status": "success",
                "memory_id": memory_id,
                "message": f"Captured solution: {memory_id}"
            }
        
        elif name == "capture_tdd_pattern":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_capture_tdd",
                    metadata={"feature": arguments["feature_name"]}
                )
            
            # Capture TDD pattern
            memory_id = await capture.capture_tdd_cycle(
                test_code=arguments["test_code"],
                implementation=arguments.get("implementation"),
                refactored=arguments.get("refactored"),
                feature_name=arguments["feature_name"]
            )
            
            if span:
                graphiti_span.end()
            
            result = {
                "status": "success",
                "memory_id": memory_id,
                "message": f"Captured TDD pattern for {arguments['feature_name']}"
            }
        
        elif name == "search_memory":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_search",
                    metadata={"query": arguments["query"]}
                )
            
            # Search shared knowledge
            results = await memory.search_with_temporal_weight(
                query=arguments["query"],
                include_historical=arguments.get("include_historical", False),
                filter_source=arguments.get("filter_source")
            )
            
            if span:
                graphiti_span.update(metadata={"results_count": len(results)})
                graphiti_span.end()
            
            result = {
                "status": "success",
                "count": len(results),
                "results": [_format_memory(r) for r in results]
            }
        
        elif name == "find_cross_insights":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_cross_insights",
                    metadata={"topic": arguments["topic"]}
                )
            
            # Find cross-domain insights
            insights = await memory.find_cross_domain_insights(arguments["topic"])
            
            if span:
                graphiti_span.update(metadata={"insights_count": len(insights)})
                graphiti_span.end()
            
            result = {
                "status": "success",
                "insights": insights,
                "message": f"Found {len(insights)} cross-domain insights"
            }
        
        elif name == "get_gtd_context":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_gtd_context",
                    metadata={"operation": "multi_search"}
                )
            
            # Get GTD context with multiple searches
            tasks = await memory.search_with_temporal_weight(
                "computer task active",
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
            
            if span:
                graphiti_span.update(metadata={
                    "tasks_count": len(tasks),
                    "projects_count": len(projects),
                    "reviews_count": len(reviews)
                })
                graphiti_span.end()
            
            result = {
                "status": "success",
                "context": {
                    "active_tasks": [_format_memory(t) for t in tasks[:5]],
                    "active_projects": [_format_memory(p) for p in projects[:3]],
                    "recent_insights": [_format_memory(r) for r in reviews[:3]]
                }
            }
        
        elif name == "supersede_memory":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_supersede",
                    metadata={"old_id": arguments["old_id"], "reason": arguments["reason"]}
                )
            
            # Supersede old memory
            new_id = await memory.supersede_memory(
            old_id=arguments["old_id"],
            new_content=arguments["new_content"],
            reason=arguments["reason"]
        )
            
            if span:
                graphiti_span.end()
        
            result = {
                "status": "success",
                "new_id": new_id,
                "message": f"Superseded {arguments['old_id']} with {new_id}"
            }
        
        elif name == "capture_command":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_capture_command",
                    metadata={"command": arguments["command"], "context": arguments["context"]}
                )
            
            # Capture command pattern
            memory_id = await capture.capture_command_pattern(
            command=arguments["command"],
            context=arguments["context"],
            success=arguments["success"],
            output=arguments.get("output")
        )
            
            if span:
                graphiti_span.end()
        
            result = {
                "status": "success",
                "memory_id": memory_id,
                "message": f"Captured command pattern: {memory_id}"
            }
        
        elif name == "get_memory_evolution":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_evolution",
                    metadata={"topic": arguments["topic"]}
                )
            
            # Get evolution history
            evolution = await memory.get_memory_evolution(arguments["topic"])
            
            if span:
                graphiti_span.update(metadata={"chains_count": len(evolution)})
                graphiti_span.end()
        
            result = {
                "status": "success",
                "evolution": evolution,
                "chains": len(evolution)
            }
        
        elif name == "generate_commands":
            # Create sub-span for Graphiti operation
            if span:
                graphiti_span = trace.span(
                    name="graphiti_generate_commands",
                    metadata={"operation": "command_generation"}
                )
            
            # Generate Claude commands
            generator = await get_command_generator()
            await generator.generate_all_commands()
            
            if span:
                graphiti_span.end()
        
            result = {
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
        
        # Langfuse Trace Analysis Tools
        elif name == "analyze_langfuse_traces":
            analyzer = await get_langfuse_analyzer()
            result = await analyzer.analyze_recent_traces(
            hours_back=arguments.get("hours_back", 1),
            session_id=arguments.get("session_id"),
            project=arguments.get("project")
        )
        
        elif name == "analyze_phase_transitions":
            analyzer = await get_langfuse_analyzer()
            result = await analyzer.analyze_phase_transitions(
            trace_id=arguments.get("trace_id"),
            session_id=arguments.get("session_id")
        )
        
        elif name == "validate_state_continuity":
            analyzer = await get_langfuse_analyzer()
            result = await analyzer.validate_state_continuity(
            trace_id=arguments.get("trace_id"),
            session_id=arguments.get("session_id")
        )
        
        elif name == "analyze_test_failure":
            analyzer = await get_langfuse_analyzer()
            result = await analyzer.analyze_test_failure(
            session_id=arguments["session_id"],
            return_patterns=arguments.get("return_patterns", True)
        )
        
        elif name == "detect_interrupt_patterns":
            analyzer = await get_langfuse_analyzer()
            result = await analyzer.detect_interrupt_patterns(
            hours_back=arguments.get("hours_back", 1),
            session_id=arguments.get("session_id")
        )
        
        elif name == "predict_trace_issues":
            analyzer = await get_langfuse_analyzer()
            result = await analyzer.predict_trace_issues(
            trace_id=arguments["trace_id"],
            threshold=arguments.get("threshold", 0.7)
        )
        
        elif name == "debug_langfuse_session":
            analyzer = await get_langfuse_analyzer()
            # Call the original debug_session function if available
            try:
                from analyze_langfuse_traces import debug_session
                # Run in executor since it's sync
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                None,
                debug_session,
                arguments["session_id"],
                arguments.get("focus", "all")
            )
            except ImportError:
                result = {
                    "status": "error",
                    "message": "debug_session not available - analyze_langfuse_traces module not found"
                }
        
        elif name == "monitor_active_traces":
            # Simple monitoring status for now
            analyzer = await get_langfuse_analyzer()
            result = {
            "status": "success",
            "message": "Real-time monitoring would check traces every {} seconds".format(
                arguments.get("interval_seconds", 30)
            ),
            "project": arguments.get("project", "all"),
            "note": "Full real-time monitoring requires a background task"
        }
    
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        # Return the result
        return result
        
    except Exception as e:
        # Log error to trace if enabled
        if span:
            span.update(
                level="ERROR",
                status_message=str(e)
            )
        raise
    finally:
        # Always close the span if it was created
        if span:
            span.end()
        # Update the trace with final status
        if trace:
            trace.update(
                output={"status": "completed", "tool": name}
            )


def _format_memory(memory: Any) -> Dict[str, Any]:
    """Format memory for output"""
    # Handle both dict-like metadata and object attributes
    if hasattr(memory, 'metadata'):
        metadata = memory.metadata
    elif isinstance(memory, dict):
        metadata = memory
    else:
        metadata = {}
    
    # Safely extract fields with fallbacks
    memory_id = getattr(memory, 'id', getattr(memory, 'uuid', None))
    
    # Handle score - it might be 'final_score', 'score', or not exist at all
    score = getattr(memory, 'final_score', getattr(memory, 'score', 0))
    
    return {
        "id": memory_id,
        "title": metadata.get("title", "Untitled"),
        "source": metadata.get("source", "unknown"),
        "status": getattr(memory, "status", metadata.get("status", "unknown")),
        "score": score,
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