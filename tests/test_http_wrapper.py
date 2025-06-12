#!/usr/bin/env python3
"""
Tests for MCP HTTP Wrapper
"""

import json
import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import queue

from http_wrapper import (
    app,
    create_jsonrpc_response,
    create_jsonrpc_error,
    validate_origin,
    handle_mcp_request,
    MCPServerProcess,
    sse_queues,
    sessions
)


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Clear global state
        sse_queues.clear()
        sessions.clear()
        yield client


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server process with test data"""
    with patch('http_wrapper.mcp_server') as mock_server:
        mock_server.running = True
        mock_server.tools = [
            {
                "name": "read_file",
                "description": "Read a file from the filesystem",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            },
            {
                "name": "write_file", 
                "description": "Write content to a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            }
        ]
        mock_server.prompts = [
            {
                "name": "code_review",
                "description": "Review code for quality and issues",
                "arguments": [
                    {"name": "language", "description": "Programming language", "required": True}
                ]
            },
            {
                "name": "git_commit",
                "description": "Generate a git commit message",
                "arguments": [
                    {"name": "diff", "description": "Git diff content", "required": True}
                ]
            }
        ]
        mock_server.resources = [
            {
                "uri": "file:///home/user/project/README.md",
                "name": "Project README",
                "description": "Main project documentation"
            },
            {
                "uri": "file:///home/user/project/src/main.py", 
                "name": "Main source file",
                "description": "Primary application entry point"
            }
        ]
        mock_server.server_info = {"name": "test-server", "version": "1.0"}
        yield mock_server


class TestJSONRPCHelpers:
    """Test JSON-RPC helper functions"""
    
    def test_create_jsonrpc_response_success(self):
        """Test creating successful JSON-RPC response"""
        result = {"data": "test"}
        response = create_jsonrpc_response(result=result, request_id=1)
        
        assert response["jsonrpc"] == "2.0"
        assert response["result"] == result
        assert response["id"] == 1
        assert "error" not in response
    
    def test_create_jsonrpc_response_error(self):
        """Test creating error JSON-RPC response"""
        error = {"code": -32601, "message": "Method not found"}
        response = create_jsonrpc_response(error=error, request_id=1)
        
        assert response["jsonrpc"] == "2.0"
        assert response["error"] == error
        assert response["id"] == 1
        assert "result" not in response
    
    def test_create_jsonrpc_error(self):
        """Test creating JSON-RPC error response"""
        error = create_jsonrpc_error(-32601, "Method not found", "test data", 1)
        
        assert error["jsonrpc"] == "2.0"
        assert error["error"]["code"] == -32601
        assert error["error"]["message"] == "Method not found"
        assert error["error"]["data"] == "test data"
        assert error["id"] == 1


class TestOriginValidation:
    """Test origin header validation"""
    
    def test_validate_origin_none(self):
        """Test validation with no origin header"""
        assert validate_origin(None) is True
    
    def test_validate_origin_localhost(self):
        """Test validation with localhost origins"""
        assert validate_origin("http://localhost:3000") is True
        assert validate_origin("https://localhost") is True
        assert validate_origin("http://127.0.0.1:8080") is True
        assert validate_origin("https://127.0.0.1") is True
    
    def test_validate_origin_invalid(self):
        """Test validation with invalid origins"""
        assert validate_origin("http://evil.com") is False
        assert validate_origin("https://malicious.site") is False


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_no_server(self, client):
        """Test health check when no MCP server is running"""
        with patch('http_wrapper.mcp_server', None):
            response = client.get('/health')
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data["status"] == "unhealthy"
    
    def test_health_check_with_server(self, client, mock_mcp_server):
        """Test health check with running MCP server"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["server"] == mock_mcp_server.server_info


class TestMCPPostEndpoint:
    """Test MCP POST endpoint"""
    
    def test_post_invalid_origin(self, client):
        """Test POST request with invalid origin"""
        response = client.post('/mcp', 
                             headers={'Origin': 'http://evil.com'},
                             json={"jsonrpc": "2.0", "method": "test", "id": 1})
        assert response.status_code == 403
    
    def test_post_invalid_json(self, client):
        """Test POST request with invalid JSON"""
        response = client.post('/mcp',
                             headers={'Content-Type': 'application/json'},
                             data='invalid json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"]["code"] == -32700
    
    def test_post_empty_body(self, client):
        """Test POST request with empty body"""
        response = client.post('/mcp',
                             headers={'Content-Type': 'application/json'},
                             data='')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"]["code"] == -32700  # Parse error for empty data
    
    def test_post_null_body(self, client):
        """Test POST request with null JSON body"""
        response = client.post('/mcp',
                             headers={'Content-Type': 'application/json'})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"]["code"] == -32700  # Parse error for no data
    
    def test_post_valid_request(self, client, mock_mcp_server):
        """Test valid POST request"""
        with patch('http_wrapper.handle_mcp_request') as mock_handler:
            mock_handler.return_value = {"jsonrpc": "2.0", "result": {"test": "data"}, "id": 1}
            
            response = client.post('/mcp',
                                 json={"jsonrpc": "2.0", "method": "test", "id": 1})
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["jsonrpc"] == "2.0"
            assert data["result"]["test"] == "data"
    
    def test_post_with_sse_accept(self, client, mock_mcp_server):
        """Test POST request with SSE accept header"""
        with patch('http_wrapper.handle_mcp_request') as mock_handler:
            mock_handler.return_value = {"jsonrpc": "2.0", "result": {"test": "data"}, "id": 1}
            
            response = client.post('/mcp',
                                 headers={'Accept': 'text/event-stream'},
                                 json={"jsonrpc": "2.0", "method": "test", "id": 1})
            assert response.status_code == 200
            assert response.content_type == 'text/event-stream; charset=utf-8'


class TestMCPGetEndpoint:
    """Test MCP GET endpoint for SSE"""
    
    def test_get_invalid_origin(self, client):
        """Test GET request with invalid origin"""
        response = client.get('/mcp', headers={'Origin': 'http://evil.com'})
        assert response.status_code == 403
    
    def test_get_sse_stream(self, client):
        """Test GET request creates SSE stream"""
        response = client.get('/mcp')
        assert response.status_code == 200
        assert response.content_type == 'text/event-stream; charset=utf-8'
        assert 'Mcp-Session-Id' in response.headers
    
    def test_get_with_session_id(self, client):
        """Test GET request with provided session ID"""
        session_id = "test-session-123"
        response = client.get('/mcp', headers={'Mcp-Session-Id': session_id})
        assert response.status_code == 200
        assert response.headers['Mcp-Session-Id'] == session_id


class TestMCPRequestHandling:
    """Test MCP request handling logic"""
    
    def test_handle_mcp_request_server_not_running(self):
        """Test handling request when server is not running"""
        with patch('http_wrapper.mcp_server', None):
            result = handle_mcp_request({"jsonrpc": "2.0", "method": "test", "id": 1})
            assert result["error"]["code"] == -32603
            assert "not running" in result["error"]["message"]
    
    def test_handle_mcp_request_invalid_format(self, mock_mcp_server):
        """Test handling request with invalid format"""
        result = handle_mcp_request("not a dict")
        assert result["error"]["code"] == -32600
    
    def test_handle_mcp_request_missing_jsonrpc(self, mock_mcp_server):
        """Test handling request missing jsonrpc field"""
        result = handle_mcp_request({"method": "test", "id": 1})
        assert result["error"]["code"] == -32600
    
    def test_handle_mcp_request_missing_method(self, mock_mcp_server):
        """Test handling request missing method field"""
        result = handle_mcp_request({"jsonrpc": "2.0", "id": 1})
        assert result["error"]["code"] == -32600
    
    def test_handle_mcp_request_initialize(self, mock_mcp_server):
        """Test handling initialize request"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            },
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert "result" in result
        assert result["result"]["protocolVersion"] == "2024-11-05"
    
    def test_handle_mcp_request_tools_list(self, mock_mcp_server):
        """Test handling tools/list request"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert len(result["result"]["tools"]) == 2
        assert result["result"]["tools"][0]["name"] == "read_file"
        assert result["result"]["tools"][1]["name"] == "write_file"
        assert "description" in result["result"]["tools"][0]
        assert "inputSchema" in result["result"]["tools"][0]
    
    def test_handle_mcp_request_tools_call(self, mock_mcp_server):
        """Test handling tools/call request"""
        mock_mcp_server.call_tool.return_value = {
            "jsonrpc": "2.0",
            "result": {"content": "tool output"},
            "id": "1"
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "test_tool",
                "arguments": {"arg1": "value1"}
            },
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert result["result"]["content"] == "tool output"
        mock_mcp_server.call_tool.assert_called_once_with("test_tool", {"arg1": "value1"})
    
    def test_handle_mcp_request_tools_call_missing_name(self, mock_mcp_server):
        """Test handling tools/call request with missing name parameter"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"arguments": {"arg1": "value1"}},
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["error"]["code"] == -32602
        assert "name" in result["error"]["data"]
    
    def test_handle_mcp_request_prompts_list(self, mock_mcp_server):
        """Test handling prompts/list request"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "prompts/list",
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert len(result["result"]["prompts"]) == 2
        assert result["result"]["prompts"][0]["name"] == "code_review"
        assert result["result"]["prompts"][1]["name"] == "git_commit"
        assert "description" in result["result"]["prompts"][0]
        assert "arguments" in result["result"]["prompts"][0]
    
    def test_handle_mcp_request_prompts_get(self, mock_mcp_server):
        """Test handling prompts/get request"""
        mock_mcp_server.get_prompt.return_value = {
            "jsonrpc": "2.0",
            "result": {"messages": [{"role": "user", "content": "test prompt"}]},
            "id": "1"
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "prompts/get",
            "params": {
                "name": "test_prompt",
                "arguments": {"lang": "python"}
            },
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert result["result"]["messages"][0]["content"] == "test prompt"
        mock_mcp_server.get_prompt.assert_called_once_with("test_prompt", {"lang": "python"})
    
    def test_handle_mcp_request_prompts_get_missing_name(self, mock_mcp_server):
        """Test handling prompts/get request with missing name parameter"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "prompts/get",
            "params": {"arguments": {"lang": "python"}},
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["error"]["code"] == -32602
        assert "name" in result["error"]["data"]
    
    def test_handle_mcp_request_resources_list(self, mock_mcp_server):
        """Test handling resources/list request"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "resources/list",
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert len(result["result"]["resources"]) == 2
        assert result["result"]["resources"][0]["uri"] == "file:///home/user/project/README.md"
        assert result["result"]["resources"][1]["uri"] == "file:///home/user/project/src/main.py"
        assert "name" in result["result"]["resources"][0]
        assert "description" in result["result"]["resources"][0]
    
    def test_handle_mcp_request_resources_read(self, mock_mcp_server):
        """Test handling resources/read request"""
        mock_mcp_server.read_resource.return_value = {
            "jsonrpc": "2.0",
            "result": {"contents": [{"uri": "file://test.txt", "text": "file content"}]},
            "id": "1"
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "resources/read",
            "params": {"uri": "file://test.txt"},
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert result["result"]["contents"][0]["text"] == "file content"
        mock_mcp_server.read_resource.assert_called_once_with("file://test.txt")
    
    def test_handle_mcp_request_resources_read_missing_uri(self, mock_mcp_server):
        """Test handling resources/read request with missing uri parameter"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "resources/read",
            "params": {},
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["error"]["code"] == -32602
        assert "uri" in result["error"]["data"]
    
    def test_handle_mcp_request_unknown_method(self, mock_mcp_server):
        """Test handling unknown method"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "unknown/method",
            "id": 1
        }
        
        result = handle_mcp_request(request_data)
        assert result["error"]["code"] == -32601
        assert "unknown/method" in result["error"]["data"]


class TestSSEQueueManagement:
    """Test SSE queue management"""
    
    def test_sse_queue_creation(self, client):
        """Test SSE queue is created for new sessions"""
        session_id = "test-session"
        
        # Simulate GET request that creates queue
        with patch('http_wrapper.sse_queues', {}) as mock_queues:
            response = client.get('/mcp', headers={'Mcp-Session-Id': session_id})
            # Queue should be created (mocked in this case)
    
    def test_post_uses_existing_sse_queue(self, client, mock_mcp_server):
        """Test POST request uses existing SSE queue"""
        session_id = "test-session"
        test_queue = queue.Queue()
        sse_queues[session_id] = test_queue
        
        with patch('http_wrapper.handle_mcp_request') as mock_handler:
            mock_handler.return_value = {"jsonrpc": "2.0", "result": {"test": "data"}, "id": 1}
            
            response = client.post('/mcp',
                                 headers={'Mcp-Session-Id': session_id},
                                 json={"jsonrpc": "2.0", "method": "test", "id": 1})
            
            # Should return SSE acknowledgment instead of JSON
            data = json.loads(response.data)
            assert data["status"] == "sent_via_sse"
            
            # Queue should contain the response
            assert not test_queue.empty()
            queued_response = test_queue.get_nowait()
            assert queued_response["result"]["test"] == "data"


class TestMCPServerProcess:
    """Test MCP server process management"""
    
    def test_mcp_server_init(self):
        """Test MCP server initialization"""
        command = ["python", "test_server.py"]
        server = MCPServerProcess(command)
        
        assert server.command == command
        assert server.message_id == 0
        assert server.pending_requests == {}
        assert server.running is False
    
    def test_get_next_id(self):
        """Test message ID generation"""
        server = MCPServerProcess(["test"])
        
        id1 = server._get_next_id()
        id2 = server._get_next_id()
        
        assert id1 == "1"
        assert id2 == "2"
        assert server.message_id == 2


if __name__ == "__main__":
    pytest.main([__file__])