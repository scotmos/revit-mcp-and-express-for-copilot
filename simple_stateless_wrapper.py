"""
Ultra-simple stateless HTTP wrapper for MCP
Creates fresh subprocess for EVERY request
"""
from flask import Flask, request, jsonify
import subprocess
import json
import sys

app = Flask(__name__)

MCP_COMMAND = ['node', r'C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js']

def call_mcp(method, params=None):
    """Start MCP server, send request, get response, terminate"""
    try:
        # Start process
        proc = subprocess.Popen(
            MCP_COMMAND,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Build requests
        requests = []
        
        # 1. Initialize
        requests.append({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "http-wrapper", "version": "1.0.0"}
            },
            "id": "1"
        })
        
        # 2. Initialized notification
        requests.append({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })
        
        # 3. Actual request
        requests.append({
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": "2"
        })
        
        # Send all requests
        for req in requests:
            proc.stdin.write(json.dumps(req) + '\n')
            proc.stdin.flush()
        
        # Read responses until we get our answer (id="2")
        responses = []
        for _ in range(20):  # Read up to 20 lines
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                if data.get('id') == '2':
                    # This is our response!
                    proc.terminate()
                    return data
                responses.append(data)
            except json.JSONDecodeError:
                print(f"Invalid JSON: {line}", file=sys.stderr)
                continue
        
        # Cleanup
        proc.terminate()
        proc.wait(timeout=2)
        
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "No response received"},
            "id": "2"
        }
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": "2"
        }

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    data = request.json
    print(f"Request: {data.get('method')}", file=sys.stderr, flush=True)
    
    method = data.get('method')
    params = data.get('params', {})
    
    response = call_mcp(method, params)
    print(f"Response: {response.get('result', {}).get('tools', ['N/A'])[0] if method == 'tools/list' else 'OK'}", file=sys.stderr, flush=True)
    
    return jsonify(response)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'running'})

if __name__ == '__main__':
    print("Starting simple stateless MCP wrapper...", file=sys.stderr, flush=True)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
