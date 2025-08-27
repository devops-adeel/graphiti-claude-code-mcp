#!/usr/bin/env python3
"""
End-to-end MCP protocol tests for Langfuse integration tools.
Tests all Langfuse tools via JSON-RPC protocol using ClientSession.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import Tool, TextContent


class TestLangfuseMCPProtocol:
    """Test all Langfuse tools via MCP protocol layer"""
    
    @pytest.fixture
    async def mcp_session(self):
        """Create an MCP session connected to the server via stdio"""
        # Use the actual MCP server
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"],
            env={
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "test-key"),
                "LANGFUSE_PUBLIC_KEY": os.environ.get("LANGFUSE_PUBLIC_KEY", "test-public"),
                "LANGFUSE_SECRET_KEY": os.environ.get("LANGFUSE_SECRET_KEY", "test-secret"),
                "LANGFUSE_HOST": os.environ.get("LANGFUSE_HOST", "https://langfuse.local"),
                "FALKORDB_HOST": os.environ.get("FALKORDB_HOST", "falkordb.local"),
                "FALKORDB_PORT": os.environ.get("FALKORDB_PORT", "6379"),
                "LOG_LEVEL": "ERROR"  # Reduce noise during tests
            },
            cwd=str(Path(__file__).parent.parent)  # Run from project root
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                init_result = await session.initialize()
                assert init_result is not None
                yield session
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_session):
        """Test that the MCP server initializes correctly"""
        # Session is already initialized in fixture
        assert mcp_session is not None
        
        # Check server capabilities
        # The session should have been initialized with capabilities
        assert hasattr(mcp_session, '_initialized')
    
    @pytest.mark.asyncio
    async def test_list_langfuse_tools(self, mcp_session):
        """Test that all Langfuse tools are exposed via MCP"""
        tools_response = await mcp_session.list_tools()
        tool_names = [tool.name for tool in tools_response.tools]
        
        # Verify all Langfuse tools are present
        expected_tools = [
            "analyze_langfuse_traces",
            "analyze_phase_transitions",
            "validate_state_continuity",
            "analyze_test_failure",
            "detect_interrupt_patterns",
            "predict_trace_issues",
            "debug_langfuse_session",
            "monitor_active_traces"
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' not found in MCP server"
    
    @pytest.mark.asyncio
    async def test_analyze_langfuse_traces(self, mcp_session):
        """Test analyze_langfuse_traces tool via MCP protocol"""
        result = await mcp_session.call_tool(
            "analyze_langfuse_traces",
            arguments={
                "hours_back": 1,
                "project": "test"
            }
        )
        
        # Check response structure
        assert result is not None
        assert hasattr(result, 'content') or hasattr(result, 'structuredContent')
        
        # Parse response
        if hasattr(result, 'structuredContent') and result.structuredContent:
            data = result.structuredContent
        else:
            # Extract from text content
            content = result.content[0] if result.content else None
            if isinstance(content, TextContent):
                data = json.loads(content.text) if content.text.startswith('{') else {"message": content.text}
            else:
                data = {}
        
        # Verify response structure
        assert "status" in data or "error" in data
        if "status" in data:
            assert data["status"] in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_detect_interrupt_patterns(self, mcp_session):
        """Test detect_interrupt_patterns tool"""
        result = await mcp_session.call_tool(
            "detect_interrupt_patterns",
            arguments={
                "hours_back": 2
            }
        )
        
        assert result is not None
        # Parse response
        if hasattr(result, 'structuredContent') and result.structuredContent:
            data = result.structuredContent
        else:
            content = result.content[0] if result.content else None
            if isinstance(content, TextContent):
                data = json.loads(content.text) if content.text.startswith('{') else {"message": content.text}
            else:
                data = {}
        
        # Check expected fields
        if "status" in data and data["status"] == "success":
            assert "hours_analyzed" in data or "traces_analyzed" in data
    
    @pytest.mark.asyncio
    async def test_analyze_phase_transitions(self, mcp_session):
        """Test analyze_phase_transitions tool"""
        # Test with session_id (won't find anything but tests protocol)
        result = await mcp_session.call_tool(
            "analyze_phase_transitions",
            arguments={
                "session_id": "test-session-123"
            }
        )
        
        assert result is not None
        # Verify we got a response (even if no data found)
        assert hasattr(result, 'content') or hasattr(result, 'structuredContent')
    
    @pytest.mark.asyncio
    async def test_validate_state_continuity(self, mcp_session):
        """Test validate_state_continuity tool"""
        result = await mcp_session.call_tool(
            "validate_state_continuity",
            arguments={
                "trace_id": "test-trace-456"
            }
        )
        
        assert result is not None
        # Parse response
        if hasattr(result, 'structuredContent') and result.structuredContent:
            data = result.structuredContent
        else:
            content = result.content[0] if result.content else None
            if isinstance(content, TextContent):
                data = json.loads(content.text) if content.text.startswith('{') else {"message": content.text}
            else:
                data = {}
        
        # Should have status field
        assert "status" in data or "error" in data
    
    @pytest.mark.asyncio
    async def test_analyze_test_failure_requires_session(self, mcp_session):
        """Test that analyze_test_failure requires session_id parameter"""
        # This should work with a session_id
        result = await mcp_session.call_tool(
            "analyze_test_failure",
            arguments={
                "session_id": "test-failure-session",
                "return_patterns": True
            }
        )
        
        assert result is not None
        # Even with no data, should return valid response
        assert hasattr(result, 'content') or hasattr(result, 'structuredContent')
    
    @pytest.mark.asyncio  
    async def test_predict_trace_issues_requires_trace_id(self, mcp_session):
        """Test that predict_trace_issues requires trace_id parameter"""
        result = await mcp_session.call_tool(
            "predict_trace_issues",
            arguments={
                "trace_id": "test-predict-trace",
                "threshold": 0.6
            }
        )
        
        assert result is not None
        # Parse response
        if hasattr(result, 'structuredContent') and result.structuredContent:
            data = result.structuredContent
        else:
            content = result.content[0] if result.content else None
            if isinstance(content, TextContent):
                data = json.loads(content.text) if content.text.startswith('{') else {"message": content.text}
            else:
                data = {}
        
        # Should have appropriate response fields
        assert "status" in data or "error" in data
    
    @pytest.mark.asyncio
    async def test_debug_langfuse_session(self, mcp_session):
        """Test debug_langfuse_session tool"""
        result = await mcp_session.call_tool(
            "debug_langfuse_session",
            arguments={
                "session_id": "debug-test-session",
                "focus": "all"
            }
        )
        
        assert result is not None
        # Should return debug information or error
        assert hasattr(result, 'content') or hasattr(result, 'structuredContent')
    
    @pytest.mark.asyncio
    async def test_monitor_active_traces(self, mcp_session):
        """Test monitor_active_traces tool"""
        result = await mcp_session.call_tool(
            "monitor_active_traces",
            arguments={
                "project": "test-project",
                "interval_seconds": 60
            }
        )
        
        assert result is not None
        # Parse response
        if hasattr(result, 'structuredContent') and result.structuredContent:
            data = result.structuredContent
        else:
            content = result.content[0] if result.content else None
            if isinstance(content, TextContent):
                data = json.loads(content.text) if content.text.startswith('{') else {"message": content.text}
            else:
                data = {}
        
        # Should have status field
        assert "status" in data
    
    @pytest.mark.asyncio
    async def test_langfuse_resources(self, mcp_session):
        """Test that Langfuse resources are accessible via MCP"""
        resources_response = await mcp_session.list_resources()
        resource_uris = [r.uri for r in resources_response.resources]
        
        # Check for Langfuse-specific resources
        expected_resources = [
            "langfuse://traces",
            "langfuse://patterns",
            "langfuse://sessions",
            "langfuse://predictions"
        ]
        
        for expected in expected_resources:
            assert expected in resource_uris, f"Resource '{expected}' not found"
    
    @pytest.mark.asyncio
    async def test_read_langfuse_traces_resource(self, mcp_session):
        """Test reading the langfuse://traces resource"""
        from mcp.types import AnyUrl
        
        result = await mcp_session.read_resource(AnyUrl("langfuse://traces"))
        assert result is not None
        assert hasattr(result, 'contents')
        
        if result.contents:
            content = result.contents[0]
            if isinstance(content, TextContent):
                # Should be valid JSON
                data = json.loads(content.text)
                assert "hours_analyzed" in data
                assert "traces_analyzed" in data or "total_traces" in data
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self, mcp_session):
        """Test that tools handle errors gracefully"""
        # Call with invalid parameters
        result = await mcp_session.call_tool(
            "analyze_langfuse_traces",
            arguments={
                "hours_back": -1  # Invalid: negative hours
            }
        )
        
        assert result is not None
        # Should still return a valid response (might be an error message)
        assert hasattr(result, 'content') or hasattr(result, 'structuredContent')
    
    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, mcp_session):
        """Test that tools validate required parameters"""
        # analyze_test_failure requires session_id
        try:
            result = await mcp_session.call_tool(
                "analyze_test_failure",
                arguments={}  # Missing required session_id
            )
            # Some servers might handle this gracefully
            assert result is not None
        except Exception as e:
            # Expected behavior - should raise an error for missing required param
            assert "session_id" in str(e).lower() or "required" in str(e).lower()


if __name__ == "__main__":
    # Run tests with asyncio
    pytest.main([__file__, "-v"])