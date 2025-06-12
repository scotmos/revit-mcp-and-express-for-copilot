#!/usr/bin/env python3
"""
Universal HTTP wrapper for MCP servers using Flask
Converts any stdio-based MCP server to HTTP REST API
"""

import asyncio
import json
import subprocess
import threading
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify, Response
import logging
from threading import Lock, Event
import queue
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Changed to DEBUG for more verbose output
logger = logging.getLogger(__name__)


@dataclass
class MCPMessage:
    """MCP protocol message structure"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPServerProcess:
    """Manages communication with an MCP server subprocess"""
    
    def __init__(self, command: List[str]):
        self.command = command
        self.process = None
        self.message_id = 0
        self.pending_requests = {}
        self.response_events = {}  # Events to signal when responses arrive
        self.lock = Lock()  # Thread synchronization
        self.server_info = None
        self.tools = []
        self.prompts = []
        self.resources = []
        self.running = False
        
    def start(self):
        """Start the MCP server process"""
        try:
            logger.info(f"Starting MCP server with command: {self.command}")
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            self.running = True
            
            # Check if process started successfully
            time.sleep(0.1)  # Give it a moment
            if self.process.poll() is not None:
                stderr_output = "No stderr"
                stdout_output = "No stdout"
                try:
                    if self.process.stderr:
                        stderr_output = self.process.stderr.read()
                    if self.process.stdout:
                        stdout_output = self.process.stdout.read()
                except Exception:
                    pass  # Pipes might be closed
                raise Exception(f"Process exited immediately. Exit code: {self.process.returncode}\nSTDOUT: {stdout_output}\nSTDERR: {stderr_output}")
            
            # Start background thread to read responses
            self.reader_thread = threading.Thread(target=self._read_responses, daemon=True)
            self.reader_thread.start()
            
            # Initialize the server
            self._initialize_server()
            logger.info(f"MCP server started: {' '.join(self.command)}")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    def stop(self):
        """Stop the MCP server process"""
        self.running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Process didn't terminate gracefully, forcing kill")
                self.process.kill()
                self.process.wait()  # Wait for kill to complete
            
    def _get_next_id(self) -> str:
        """Generate next message ID"""
        self.message_id += 1
        return str(self.message_id)
    
    def _send_message(self, message: MCPMessage) -> Optional[str]:
        """Send message to MCP server and return message ID"""
        if not self.process or not self.running:
            raise Exception("MCP server not running")
            
        # Check if process is still alive
        if self.process.poll() is not None:
            raise Exception("MCP server process has terminated")
            
        message_dict = {k: v for k, v in asdict(message).items() if v is not None}
        message_json = json.dumps(message_dict) + '\n'
        
        try:
            self.process.stdin.write(message_json)
            self.process.stdin.flush()
            return message.id
        except BrokenPipeError:
            raise Exception("MCP server process closed stdin pipe")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            # Check if process died while we were writing
            if self.process.poll() is not None:
                raise Exception("MCP server process terminated during message send")
            raise
    
    def _read_responses(self):
        """Background thread to read responses from MCP server"""
        while self.running and self.process:
            try:
                # Check if process has terminated
                if self.process.poll() is not None:
                    logger.warning("MCP server process has terminated")
                    break
                    
                line = self.process.stdout.readline()
                if not line:
                    logger.warning("No more output from MCP server")
                    break
                
                line = line.strip()
                if not line:
                    continue
                    
                logger.debug(f"Received from MCP server: {line}")
                response = json.loads(line)
                msg_id = response.get('id')
                
                if msg_id:
                    with self.lock:
                        if msg_id in self.pending_requests:
                            # Store response for pending request
                            self.pending_requests[msg_id] = response
                            # Signal that response is available
                            if msg_id in self.response_events:
                                self.response_events[msg_id].set()
                        else:
                            logger.debug(f"Received response for unknown message ID: {msg_id}")
                else:
                    logger.debug(f"Received message without ID: {response}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {line} - Error: {e}")
            except Exception as e:
                logger.error(f"Error reading response: {e}")
                break
        
        # Clean up when reader thread exits - signal all waiting events
        with self.lock:
            for event in self.response_events.values():
                event.set()  # Wake up any waiting threads
        
        self.running = False
        logger.info("Response reader thread exited")
    
    def _wait_for_response(self, message_id: str, timeout: int = 30) -> Dict[str, Any]:
        """Wait for response to a specific message"""
        # Create event for this message
        event = Event()
        with self.lock:
            self.response_events[message_id] = event
        
        try:
            # Wait for the event to be set (response received or process died)
            if not event.wait(timeout):
                raise TimeoutError(f"No response received for message {message_id}")
            
            # Get the response
            with self.lock:
                response = self.pending_requests.pop(message_id, None)
                if message_id in self.response_events:
                    del self.response_events[message_id]
            
            if response is None:
                # Check if process is still running
                if not self.running or (self.process and self.process.poll() is not None):
                    raise Exception("MCP server process terminated before response received")
                else:
                    raise Exception(f"Response for message {message_id} was None or missing")
                
            return response
            
        except Exception:
            # Clean up on error
            with self.lock:
                self.pending_requests.pop(message_id, None)
                if message_id in self.response_events:
                    del self.response_events[message_id]
            raise
    
    def _initialize_server(self):
        """Initialize the MCP server and get capabilities"""
        try:
            # Send initialize request
            init_msg = MCPMessage(
                id=self._get_next_id(),
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "prompts": {},
                        "resources": {}
                    },
                    "clientInfo": {
                        "name": "mcp-http-wrapper",
                        "version": "1.0.0"
                    }
                }
            )
            
            logger.info("Sending initialize message to MCP server")
            msg_id = self._send_message(init_msg)
            if msg_id:
                with self.lock:
                    self.pending_requests[msg_id] = None
            
            logger.info("Waiting for initialize response...")
            if not msg_id:
                raise Exception("Failed to get message ID for initialize request")
            response = self._wait_for_response(msg_id)
            
            if response is None:
                raise Exception("No response received from MCP server")
                
            if 'error' in response:
                raise Exception(f"Failed to initialize: {response['error']}")
                
            self.server_info = response.get('result', {})
            logger.info(f"Server initialized successfully: {self.server_info}")
            
            # Send initialized notification (no ID needed for notifications)
            notif_msg = MCPMessage(method="notifications/initialized")
            notif_msg_dict = {k: v for k, v in asdict(notif_msg).items() if v is not None}
            notif_json = json.dumps(notif_msg_dict) + '\n'
            self.process.stdin.write(notif_json)
            self.process.stdin.flush()
            
            # Get available tools, prompts, and resources
            self._load_tools()
            self._load_prompts()
            self._load_resources()
            
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            # Try to get stderr output for debugging
            if self.process and self.process.stderr:
                try:
                    stderr_output = self.process.stderr.read()
                    if stderr_output:
                        logger.error(f"MCP server stderr: {stderr_output}")
                except Exception:
                    logger.debug("Could not read stderr - pipe may be closed")
            raise
    
    def _load_tools(self):
        """Load available tools from the server"""
        tools_msg = MCPMessage(
            id=self._get_next_id(),
            method="tools/list"
        )
        
        msg_id = self._send_message(tools_msg)
        if msg_id:
            with self.lock:
                self.pending_requests[msg_id] = None
        
        if not msg_id:
            return  # Skip if no message ID
        response = self._wait_for_response(msg_id)
        if 'error' not in response:
            self.tools = response.get('result', {}).get('tools', [])
            
    def _load_prompts(self):
        """Load available prompts from the server"""
        prompts_msg = MCPMessage(
            id=self._get_next_id(),
            method="prompts/list"
        )
        
        msg_id = self._send_message(prompts_msg)
        if msg_id:
            with self.lock:
                self.pending_requests[msg_id] = None
        
        if not msg_id:
            return  # Skip if no message ID
        response = self._wait_for_response(msg_id)
        if 'error' not in response:
            self.prompts = response.get('result', {}).get('prompts', [])
            
    def _load_resources(self):
        """Load available resources from the server"""
        resources_msg = MCPMessage(
            id=self._get_next_id(),
            method="resources/list"
        )
        
        msg_id = self._send_message(resources_msg)
        if msg_id:
            with self.lock:
                self.pending_requests[msg_id] = None
        
        if not msg_id:
            return  # Skip if no message ID
        response = self._wait_for_response(msg_id)
        if 'error' not in response:
            self.resources = response.get('result', {}).get('resources', [])
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        call_msg = MCPMessage(
            id=self._get_next_id(),
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments
            }
        )
        
        msg_id = self._send_message(call_msg)
        if msg_id:
            with self.lock:
                self.pending_requests[msg_id] = None
        
        if not msg_id:
            raise Exception("Failed to get message ID for tool call")
        response = self._wait_for_response(msg_id)
        return response
    
    def get_prompt(self, prompt_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get a prompt from the MCP server"""
        params = {"name": prompt_name}
        if arguments:
            params["arguments"] = arguments
            
        prompt_msg = MCPMessage(
            id=self._get_next_id(),
            method="prompts/get",
            params=params
        )
        
        msg_id = self._send_message(prompt_msg)
        if msg_id:
            with self.lock:
                self.pending_requests[msg_id] = None
        
        if not msg_id:
            raise Exception("Failed to get message ID for prompt request")
        response = self._wait_for_response(msg_id)
        return response
    
    def read_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        resource_msg = MCPMessage(
            id=self._get_next_id(),
            method="resources/read",
            params={"uri": resource_uri}
        )
        
        msg_id = self._send_message(resource_msg)
        if msg_id:
            with self.lock:
                self.pending_requests[msg_id] = None
        
        if not msg_id:
            raise Exception("Failed to get message ID for resource request")
        response = self._wait_for_response(msg_id)
        return response


# Global MCP server instance
mcp_server = None
app = Flask(__name__)

# Session management
sessions = {}
# SSE message queues for each session
sse_queues = {}


def create_jsonrpc_response(result=None, error=None, request_id=None):
    """Create a JSON-RPC 2.0 response"""
    response = {"jsonrpc": "2.0"}
    
    if error:
        response["error"] = error
    else:
        response["result"] = result
        
    if request_id is not None:
        response["id"] = request_id
        
    return response


def create_jsonrpc_error(code, message, data=None, request_id=None):
    """Create a JSON-RPC 2.0 error response"""
    error = {"code": code, "message": message}
    if data:
        error["data"] = data
    return create_jsonrpc_response(error=error, request_id=request_id)


def validate_origin(origin):
    """Validate Origin header for security"""
    if not origin:
        return True  # Allow requests without Origin header
    
    # Allow localhost and 127.0.0.1
    allowed_origins = ['http://localhost', 'https://localhost', 'http://127.0.0.1', 'https://127.0.0.1']
    
    for allowed in allowed_origins:
        if origin.startswith(allowed):
            return True
    
    return False


def handle_mcp_request(data, session_id=None):
    """Handle MCP JSON-RPC request"""
    if not mcp_server or not mcp_server.running:
        return create_jsonrpc_error(-32603, "MCP server not running")
    
    # Validate JSON-RPC format
    if not isinstance(data, dict):
        return create_jsonrpc_error(-32600, "Invalid Request", "Request must be JSON object")
    
    if data.get("jsonrpc") != "2.0":
        return create_jsonrpc_error(-32600, "Invalid Request", "Missing or invalid jsonrpc version")
    
    method = data.get("method")
    if not method or not isinstance(method, str):
        return create_jsonrpc_error(-32600, "Invalid Request", "Missing or invalid method")
    
    params = data.get("params", {})
    request_id = data.get("id")
    
    try:
        # Handle MCP methods
        if method == "initialize":
            # MCP initialization
            if not isinstance(params, dict):
                return create_jsonrpc_error(-32602, "Invalid params", "Params must be object", request_id)
            
            protocol_version = params.get("protocolVersion")
            capabilities = params.get("capabilities", {})
            client_info = params.get("clientInfo", {})
            
            # Store session info if session_id provided
            if session_id:
                sessions[session_id] = {
                    "initialized": True,
                    "client_info": client_info,
                    "capabilities": capabilities
                }
            
            # Return server capabilities
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "prompts": {},
                    "resources": {}
                },
                "serverInfo": {
                    "name": "mcp-http-wrapper",
                    "version": "1.0.0"
                }
            }
            
        elif method == "tools/list":
            result = {"tools": mcp_server.tools}
            
        elif method == "tools/call":
            if not isinstance(params, dict) or "name" not in params:
                return create_jsonrpc_error(-32602, "Invalid params", "Missing 'name' parameter", request_id)
            
            tool_name = params["name"]
            arguments = params.get("arguments", {})
            
            response = mcp_server.call_tool(tool_name, arguments)
            if 'error' in response:
                return create_jsonrpc_error(-32603, "Internal error", response['error'], request_id)
            result = response.get('result', {})
            
        elif method == "prompts/list":
            result = {"prompts": mcp_server.prompts}
            
        elif method == "prompts/get":
            if not isinstance(params, dict) or "name" not in params:
                return create_jsonrpc_error(-32602, "Invalid params", "Missing 'name' parameter", request_id)
            
            prompt_name = params["name"]
            arguments = params.get("arguments")
            
            response = mcp_server.get_prompt(prompt_name, arguments)
            if 'error' in response:
                return create_jsonrpc_error(-32603, "Internal error", response['error'], request_id)
            result = response.get('result', {})
            
        elif method == "resources/list":
            result = {"resources": mcp_server.resources}
            
        elif method == "resources/read":
            if not isinstance(params, dict) or "uri" not in params:
                return create_jsonrpc_error(-32602, "Invalid params", "Missing 'uri' parameter", request_id)
            
            resource_uri = params["uri"]
            
            response = mcp_server.read_resource(resource_uri)
            if 'error' in response:
                return create_jsonrpc_error(-32603, "Internal error", response['error'], request_id)
            result = response.get('result', {})
            
        else:
            return create_jsonrpc_error(-32601, "Method not found", f"Unknown method: {method}", request_id)
        
        return create_jsonrpc_response(result=result, request_id=request_id)
        
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return create_jsonrpc_error(-32603, "Internal error", str(e), request_id)


def handle_sse_request(initial_response, session_id, origin):
    """Handle MCP request with SSE response"""
    # Create a queue for this session if it doesn't exist
    if session_id not in sse_queues:
        sse_queues[session_id] = queue.Queue()
    
    def event_stream():
        # Send the initial response
        yield f"data: {json.dumps(initial_response)}\n\n"
        
        # Keep connection alive and handle any additional messages
        while True:
            try:
                # Check for messages in the queue (with timeout)
                message = sse_queues[session_id].get(timeout=30)
                yield f"data: {json.dumps(message)}\n\n"
            except queue.Empty:
                # Send heartbeat if no messages
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
            except Exception:
                # Connection closed
                break
        
        # Clean up when connection closes
        if session_id in sse_queues:
            del sse_queues[session_id]
    
    response_obj = Response(event_stream(), mimetype='text/event-stream')
    response_obj.headers['Cache-Control'] = 'no-cache'
    response_obj.headers['Connection'] = 'keep-alive'
    response_obj.headers['Access-Control-Allow-Origin'] = origin or '*'
    response_obj.headers['Access-Control-Allow-Headers'] = 'Content-Type, Mcp-Session-Id'
    response_obj.headers['Mcp-Session-Id'] = session_id
    
    return response_obj


@app.route('/mcp', methods=['POST'])
def mcp_post():
    """MCP Streamable HTTP POST endpoint"""
    # Validate Origin header
    origin = request.headers.get('Origin')
    if not validate_origin(origin):
        return jsonify(create_jsonrpc_error(-32603, "Invalid Origin header")), 403
    
    # Get or create session ID
    session_id = request.headers.get('Mcp-Session-Id')
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Check if client wants SSE response
    accept_header = request.headers.get('Accept', '')
    wants_sse = 'text/event-stream' in accept_header
    
    try:
        data = request.get_json()
    except Exception as e:
        error_response = create_jsonrpc_error(-32700, "Parse error", str(e))
        if wants_sse:
            return handle_sse_request(error_response, session_id, origin)
        return jsonify(error_response), 400
    
    if not data:
        error_response = create_jsonrpc_error(-32600, "Invalid Request", "Empty request body")
        if wants_sse:
            return handle_sse_request(error_response, session_id, origin)
        return jsonify(error_response), 400
    
    # Handle the request
    response_data = handle_mcp_request(data, session_id)
    
    if wants_sse:
        # Return response via SSE
        return handle_sse_request(response_data, session_id, origin)
    else:
        # Check if there's an active SSE connection for this session
        if session_id in sse_queues:
            # Send response via existing SSE connection
            try:
                sse_queues[session_id].put(response_data, timeout=1)
                return jsonify({"status": "sent_via_sse"}), 200
            except queue.Full:
                pass  # Fall back to JSON response
        
        # Return JSON response
        response = jsonify(response_data)
        response.headers['Mcp-Session-Id'] = session_id
        return response


@app.route('/mcp', methods=['GET'])
def mcp_get():
    """MCP Streamable HTTP GET endpoint for SSE"""
    # Validate Origin header
    origin = request.headers.get('Origin')
    if not validate_origin(origin):
        return "Invalid Origin header", 403
    
    # Get or create session ID
    session_id = request.headers.get('Mcp-Session-Id')
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Create a queue for this session
    if session_id not in sse_queues:
        sse_queues[session_id] = queue.Queue()
    
    def event_stream():
        """Generate Server-Sent Events"""
        try:
            while True:
                try:
                    # Wait for messages in the queue
                    message = sse_queues[session_id].get(timeout=30)
                    yield f"data: {json.dumps(message)}\n\n"
                except queue.Empty:
                    # Send heartbeat if no messages
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
        except Exception:
            # Connection closed
            pass
        finally:
            # Clean up when connection closes
            if session_id in sse_queues:
                del sse_queues[session_id]
    
    response = Response(event_stream(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = origin or '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Mcp-Session-Id'
    response.headers['Mcp-Session-Id'] = session_id
    
    return response


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint (non-MCP)"""
    if mcp_server and mcp_server.running:
        return jsonify({"status": "healthy", "server": mcp_server.server_info})
    else:
        return jsonify({"status": "unhealthy"}), 503


def create_app(mcp_command: List[str], host: str = "0.0.0.0", port: int = 5000):
    """Create and configure the Flask app with MCP server"""
    global mcp_server
    
    # Start MCP server
    mcp_server = MCPServerProcess(mcp_command)
    mcp_server.start()
    
    # Register cleanup
    import atexit
    atexit.register(lambda: mcp_server.stop() if mcp_server else None)
    
    return app


def main():
    """Main entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='MCP Streamable HTTP wrapper - Expose stdio MCP servers via HTTP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python http_wrapper.py python mcp-filesystem.py
  python http_wrapper.py --host 127.0.0.1 --port 8080 python mcp-time.py
  python http_wrapper.py --host 0.0.0.0 --port 3000 -- npx -y @modelcontextprotocol/server-filesystem .
        '''
    )
    
    parser.add_argument('--host', default='127.0.0.1', 
                       help='Host to bind to (default: 127.0.0.1 - localhost only). Use 0.0.0.0 to allow network access.')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable Flask debug mode')
    parser.add_argument('command', nargs=argparse.REMAINDER, help='MCP server command and arguments (use -- to separate if needed)')
    
    args = parser.parse_args()
    mcp_command = args.command
    
    # Validate that we have a command
    if not mcp_command:
        parser.print_help()
        print("\nError: No MCP server command provided")
        sys.exit(1)
    
    try:
        app = create_app(mcp_command)
        
        # Determine the base URL for examples
        base_url = f"http://{args.host}:{args.port}"
        
        print(f"Starting MCP Streamable HTTP wrapper for: {' '.join(mcp_command)}")
        print()
        print("═══════════════════════════════════════════════════════════════")
        print("               MCP STREAMABLE HTTP TRANSPORT")
        print("═══════════════════════════════════════════════════════════════")
        print()
        print("Endpoints:")
        print("  POST /mcp    - Main JSON-RPC endpoint")
        print("  GET  /mcp    - Server-Sent Events streaming")
        print("  GET  /health - Health check")
        print()
        print("Supported MCP Methods:")
        print("  • initialize      • tools/list      • tools/call")
        print("  • prompts/list    • prompts/get     • resources/list")
        print("  • resources/read")
        print()
        print("═══════════════════════════════════════════════════════════════")
        print("                        USAGE EXAMPLES")
        print("═══════════════════════════════════════════════════════════════")
        print()
        print("1. Initialize MCP connection:")
        print(f'   curl -X POST {base_url}/mcp \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"jsonrpc": "2.0", "method": "initialize", "params": {')
        print('           "protocolVersion": "2024-11-05",')
        print('           "capabilities": {"tools": {}, "prompts": {}, "resources": {}},')
        print('           "clientInfo": {"name": "my-client", "version": "1.0.0"}')
        print('         }, "id": 1}\'')
        print()
        print("2. List available tools:")
        print(f'   curl -X POST {base_url}/mcp \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"jsonrpc": "2.0", "method": "tools/list", "id": 2}\'')
        print()
        print("3. Call a tool:")
        print(f'   curl -X POST {base_url}/mcp \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"jsonrpc": "2.0", "method": "tools/call", "params": {')
        print('           "name": "read_file",')
        print('           "arguments": {"path": "/path/to/file.txt"}')
        print('         }, "id": 3}\'')
        print()
        print("4. List prompts:")
        print(f'   curl -X POST {base_url}/mcp \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"jsonrpc": "2.0", "method": "prompts/list", "id": 4}\'')
        print()
        print("5. Get a prompt:")
        print(f'   curl -X POST {base_url}/mcp \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"jsonrpc": "2.0", "method": "prompts/get", "params": {')
        print('           "name": "code_review",')
        print('           "arguments": {"language": "python"}')
        print('         }, "id": 5}\'')
        print()
        print("6. List resources:")
        print(f'   curl -X POST {base_url}/mcp \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"jsonrpc": "2.0", "method": "resources/list", "id": 6}\'')
        print()
        print("7. Read a resource:")
        print(f'   curl -X POST {base_url}/mcp \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"jsonrpc": "2.0", "method": "resources/read", "params": {')
        print('           "uri": "file:///path/to/resource.txt"')
        print('         }, "id": 7}\'')
        print()
        print("8. Connect to SSE stream:")
        print(f'   curl -H "Accept: text/event-stream" {base_url}/mcp')
        print()
        print("9. Health check:")
        print(f'   curl {base_url}/health')
        print()
        print("Optional headers for all requests:")
        print("   • Mcp-Session-Id: <unique-session-id>")
        print(f"   • Origin: {base_url}")
        print()
        print("═══════════════════════════════════════════════════════════════")
        print(f"Server starting on {base_url}")
        print("═══════════════════════════════════════════════════════════════")
        print()
        
        try:
            app.run(host=args.host, port=args.port, debug=args.debug)
        except OSError as e:
            if "Address already in use" in str(e) or "Only one usage of each socket address" in str(e):
                print(f"\n❌ Error: Port {args.port} is already in use!")
                print()
                print("Suggestions:")
                print(f"  • Try a different port: --port {args.port + 1}")
                print(f"  • Check what's using port {args.port}: netstat -tulpn | grep {args.port}")
                print("  • Kill the conflicting process if it's safe to do so")
                print()
                sys.exit(1)
            else:
                print(f"\n❌ Network Error: {e}")
                sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
