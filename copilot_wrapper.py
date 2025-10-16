"""
Simple pre-initialized MCP HTTP wrapper
Initializes the MCP server once at startup, keeps it ready for Copilot Studio
"""
from flask import Flask, request, jsonify
import subprocess
import json
import sys
import threading
import queue
import time

app = Flask(__name__)

# Global state
mcp_process = None
response_queue = queue.Queue()
tools_cache = None

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
                        print(f"[RESPONSE] ID={data.get('id', 'N/A')} method={data.get('method', 'N/A')}", file=sys.stderr, flush=True)
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] Invalid JSON: {line[:100]}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[ERROR] Reader thread: {e}", file=sys.stderr, flush=True)
            time.sleep(0.1)

def send_and_wait(message, timeout=10):
    """Send message and wait for response"""
    global mcp_process
    
    msg_id = message.get('id')
    print(f"[REQUEST] ID={msg_id} method={message.get('method')}", file=sys.stderr, flush=True)
    
    # Send message
    mcp_process.stdin.write(json.dumps(message) + '\n')
    mcp_process.stdin.flush()
    
    # Wait for response with matching ID
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = response_queue.get(timeout=0.1)
            if response.get('id') == msg_id:
                return response
            else:
                # Put it back for another handler
                response_queue.put(response)
        except queue.Empty:
            continue
    
    raise Exception(f"Timeout waiting for response to message {msg_id}")

def initialize_server():
    """Initialize the MCP server and cache tools list"""
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
    
    time.sleep(1)  # Let it start
    
    print("[INIT] Sending initialize...", file=sys.stderr, flush=True)
    
    # Send initialize
    init_msg = {
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "copilot-studio", "version": "1.0.0"}
        }
    }
    
    init_response = send_and_wait(init_msg)
    print(f"[INIT] Initialize response received", file=sys.stderr, flush=True)
    
    # Send initialized notification
    mcp_process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + '\n')
    mcp_process.stdin.flush()
    
    print("[INIT] Fetching tools list...", file=sys.stderr, flush=True)
    
    # Get tools list and cache it
    tools_msg = {
        "jsonrpc": "2.0",
        "id": "tools",
        "method": "tools/list",
        "params": {}
    }
    
    tools_response = send_and_wait(tools_msg, timeout=15)
    tools_cache = tools_response.get('result', {}).get('tools', [])
    
    print(f"[INIT] ✓ Server ready with {len(tools_cache)} tools!", file=sys.stderr, flush=True)

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    global tools_cache
    
    try:
        data = request.json
        method = data.get('method')
        msg_id = data.get('id')
        
        print(f"[REQUEST] {method} (id={msg_id})", file=sys.stderr, flush=True)
        print(f"[PARAMS] {data.get('params', {})}", file=sys.stderr, flush=True)
        
        # Handle initialize
        if method == 'initialize':
            return jsonify({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "revit-mcp",
                        "version": "1.0.0"
                    },
                    "instructions": "Revit MCP Server with 15 tools for BIM automation"
                }
            })
        
        # Handle notifications (no response expected)
        elif method and method.startswith('notifications/'):
            print(f"[NOTIFICATION] {method} - acknowledged", file=sys.stderr, flush=True)
            # After initialized notification, Copilot Studio should call tools/list next
            # But if it doesn't, we need to investigate why
            return '', 204
        
        # Handle tools/list from cache
        elif method == 'tools/list':
            print(f"[TOOLS/LIST] Returning {len(tools_cache)} tools", file=sys.stderr, flush=True)
            return jsonify({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools_cache}
            })
        
        # Forward other requests to MCP server
        else:
            print(f"[FORWARD] Forwarding to MCP server: {method}", file=sys.stderr, flush=True)
            response = send_and_wait(data)
            return jsonify(response)
            
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr, flush=True)
        return jsonify({
            'jsonrpc': '2.0',
            'id': data.get('id') if 'data' in locals() else None,
            'error': {'code': -32603, 'message': str(e)}
        }), 500

@app.route('/mcp', methods=['GET'])
def mcp_get():
    """Handle GET requests - might be used for discovery"""
    print(f"[GET] /mcp endpoint called", file=sys.stderr, flush=True)
    return jsonify({
        "name": "revit-mcp",
        "version": "1.0.0",
        "protocol": "mcp/2024-11-05",
        "tools_count": len(tools_cache) if tools_cache else 0,
        "tools": [{"name": t["name"], "description": t.get("description", "")[:100]} for t in (tools_cache or [])]
    })

@app.route('/mcp/tools', methods=['GET'])  
def mcp_tools_get():
    """Alternative endpoint for tool discovery"""
    print(f"[GET] /mcp/tools endpoint called", file=sys.stderr, flush=True)
    return jsonify({
        "tools": tools_cache
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'running',
        'tools_count': len(tools_cache) if tools_cache else 0
    })

if __name__ == '__main__':
    try:
        initialize_server()
        print("[SERVER] Starting Flask on 0.0.0.0:5000...", file=sys.stderr, flush=True)
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("[SERVER] Shutting down...", file=sys.stderr, flush=True)
        if mcp_process:
            mcp_process.terminate()
