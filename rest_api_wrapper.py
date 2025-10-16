"""
REST API Wrapper for Revit MCP Tools
Exposes MCP tools as simple REST endpoints for Copilot Studio
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import sys
import threading
import queue
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for Copilot Studio

# Global state
mcp_process = None
response_queue = queue.Queue()
tools_cache = []

def read_responses():
    """Background thread to read MCP responses"""
    global mcp_process
    while True:
        try:
            if mcp_process and mcp_process.stdout:
                line = mcp_process.stdout.readline()
                if line:
                    try:
                        data = json.loads(line.strip())
                        response_queue.put(data)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            time.sleep(0.1)

def send_and_wait(message, timeout=30):
    """Send message to MCP and wait for response"""
    global mcp_process
    
    msg_id = message.get('id')
    
    # Send message
    mcp_process.stdin.write(json.dumps(message) + '\n')
    mcp_process.stdin.flush()
    
    # Wait for response
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = response_queue.get(timeout=0.1)
            if response.get('id') == msg_id:
                return response
            else:
                response_queue.put(response)  # Put it back
        except queue.Empty:
            continue
    
    raise Exception(f"Timeout waiting for response")

def initialize_server():
    """Initialize the MCP server"""
    global mcp_process, tools_cache
    
    print("[INIT] Starting MCP server...", file=sys.stderr, flush=True)
    
    # Start process
    mcp_process = subprocess.Popen(
        ['node', r'C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1
    )
    
    # Start reader thread
    reader = threading.Thread(target=read_responses, daemon=True)
    reader.start()
    
    time.sleep(1)
    
    # Initialize
    init_response = send_and_wait({
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "rest-api", "version": "1.0.0"}
        }
    })
    
    # Send initialized notification
    mcp_process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + '\n')
    mcp_process.stdin.flush()
    
    # Get tools list
    tools_response = send_and_wait({
        "jsonrpc": "2.0",
        "id": "tools",
        "method": "tools/list",
        "params": {}
    }, timeout=15)
    
    tools_cache = tools_response.get('result', {}).get('tools', [])
    
    print(f"[INIT] ✓ Server ready with {len(tools_cache)} tools!", file=sys.stderr, flush=True)
    for tool in tools_cache:
        print(f"  - {tool['name']}", file=sys.stderr, flush=True)

# ============================================================================
# REST API Endpoints - One per tool
# ============================================================================

@app.route('/api/tools', methods=['GET'])
def list_tools():
    """List all available tools"""
    return jsonify({
        "tools": [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "endpoint": f"/api/tools/{t['name']}"
            }
            for t in tools_cache
        ]
    })

@app.route('/api/tools/<tool_name>', methods=['POST'])
def call_tool(tool_name):
    """
    Call any MCP tool by name
    POST body should contain the tool arguments as JSON
    """
    try:
        # Get arguments from request body
        arguments = request.json or {}
        
        # Convert elementId to string if it's a number (Copilot Studio might send as number)
        if 'elementId' in arguments and isinstance(arguments['elementId'], (int, float)):
            arguments['elementId'] = str(int(arguments['elementId']))
        
        print(f"[API] Calling tool: {tool_name}", file=sys.stderr, flush=True)
        print(f"[API] Arguments: {arguments}", file=sys.stderr, flush=True)
        
        # Use longer timeout for bulk operations
        timeout = 300 if tool_name == 'grade_all_families_by_category' else 30
        
        # Call the MCP tool
        response = send_and_wait({
            "jsonrpc": "2.0",
            "id": f"tool_{int(time.time() * 1000)}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }, timeout=timeout)
        
        print(f"[DEBUG] MCP Response: {response}", file=sys.stderr, flush=True)
        
        # Check for errors
        if 'error' in response:
            return jsonify({
                "success": False,
                "error": response['error']
            }), 400
        
        # Return the result
        result = response.get('result', {})
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr, flush=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Convenience endpoints for specific tools
@app.route('/api/check_geometry_type', methods=['POST'])
def check_geometry_type():
    """Check if a family's geometry is mesh or solid"""
    return call_tool('check_geometry_type')

@app.route('/api/create_wall', methods=['POST'])
def create_wall():
    """Create a wall in Revit"""
    return call_tool('createWall')

@app.route('/api/color_elements', methods=['POST'])
def color_elements():
    """Color elements by parameter value"""
    return call_tool('color_elements')

@app.route('/api/get_selected_elements', methods=['POST'])
def get_selected_elements():
    """Get currently selected elements"""
    return call_tool('get_selected_elements')

@app.route('/api/get_current_view_info', methods=['GET', 'POST'])
def get_current_view_info():
    """Get current view information"""
    return call_tool('get_current_view_info')

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'tools_count': len(tools_cache),
        'mcp_process_alive': mcp_process.poll() is None if mcp_process else False
    })

@app.route('/', methods=['GET'])
def root():
    """API documentation"""
    return jsonify({
        "name": "Revit MCP REST API",
        "version": "1.0.0",
        "description": "REST API wrapper for Revit MCP tools - compatible with Copilot Studio",
        "endpoints": {
            "GET /api/tools": "List all available tools",
            "POST /api/tools/{tool_name}": "Call any tool by name",
            "POST /api/check_geometry_type": "Check geometry type (mesh/solid)",
            "POST /api/create_wall": "Create a wall",
            "POST /api/color_elements": "Color elements by parameter",
            "POST /api/get_selected_elements": "Get selected elements",
            "GET /api/get_current_view_info": "Get current view info",
            "GET /health": "Health check"
        },
        "tools_available": len(tools_cache),
        "documentation": "https://6c701ec65166.ngrok-free.app/api/tools"
    })

if __name__ == '__main__':
    try:
        initialize_server()
        print("\n" + "="*70, file=sys.stderr, flush=True)
        print("  Revit MCP REST API Server", file=sys.stderr, flush=True)
        print("="*70, file=sys.stderr, flush=True)
        print(f"\n  Available at: http://0.0.0.0:5000", file=sys.stderr, flush=True)
        print(f"  Via ngrok: https://6c701ec65166.ngrok-free.app", file=sys.stderr, flush=True)
        print(f"\n  Tools: {len(tools_cache)}", file=sys.stderr, flush=True)
        print(f"  Endpoints: /api/tools/<tool_name>", file=sys.stderr, flush=True)
        print("\n" + "="*70 + "\n", file=sys.stderr, flush=True)
        
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("[SERVER] Shutting down...", file=sys.stderr, flush=True)
        if mcp_process:
            mcp_process.terminate()
