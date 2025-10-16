"""
Better HTTP wrapper that restarts MCP server for each session
This avoids the stdio one-connection limitation
"""
from flask import Flask, request, jsonify
import subprocess
import json
import sys
import threading
import time
from queue import Queue, Empty

app = Flask(__name__)

class MCPServerPool:
    def __init__(self, command):
        self.command = command
        self.lock = threading.Lock()
        
    def create_process(self):
        """Create a new MCP server process"""
        return subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
    
    def call_tool(self, method, params=None):
        """Call MCP server with a fresh process for each request"""
        process = None
        try:
            process = self.create_process()
            
            # First, send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "revit-mcp-http-wrapper",
                        "version": "1.0.0"
                    }
                },
                "id": "init"
            }
            
            process.stdin.write(json.dumps(init_request) + '\n')
            process.stdin.flush()
            
            # Read init response
            init_response = None
            for _ in range(10):  # Try up to 10 lines
                line = process.stdout.readline()
                if line:
                    try:
                        data = json.loads(line.strip())
                        if data.get('id') == 'init':
                            init_response = data
                            break
                    except json.JSONDecodeError:
                        continue
            
            if not init_response:
                raise Exception("Failed to initialize MCP server")
            
            # Send initialized notification
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            process.stdin.write(json.dumps(initialized_notif) + '\n')
            process.stdin.flush()
            
            # Now send the actual request
            request_data = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": str(int(time.time() * 1000))
            }
            
            request_json = json.dumps(request_data) + '\n'
            process.stdin.write(request_json)
            process.stdin.flush()
            
            # Read response with timeout
            start_time = time.time()
            timeout = 30  # 30 second timeout
            
            while time.time() - start_time < timeout:
                line = process.stdout.readline()
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                    # Check if this is the response to our request
                    if data.get('id') == request_data['id']:
                        return data
                except json.JSONDecodeError:
                    continue
            
            # If we get here, no valid response received
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "No response from MCP server"
                },
                "id": request_data["id"]
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Server error: {str(e)}"
                },
                "id": "error"
            }
        finally:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    try:
                        process.kill()
                    except:
                        pass

# Initialize MCP server pool
mcp_pool = MCPServerPool(['node', r'C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js'])

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    try:
        request_data = request.json
        print(f"Received: {request_data.get('method', 'unknown')}", file=sys.stderr)
        
        method = request_data.get('method')
        params = request_data.get('params', {})
        
        # Call MCP server
        response = mcp_pool.call_tool(method, params)
        
        print(f"Response: {json.dumps(response)[:200]}...", file=sys.stderr)
        return jsonify(response)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return jsonify({
            'jsonrpc': '2.0',
            'error': {
                'code': -32603,
                'message': str(e)
            },
            'id': request_data.get('id', 'error')
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'running'})

if __name__ == '__main__':
    print("Starting Revit MCP HTTP Wrapper (Process Pool Mode)...", file=sys.stderr)
    print("Each request creates a fresh MCP server process", file=sys.stderr)
    app.run(host='0.0.0.0', port=5000, debug=False)
