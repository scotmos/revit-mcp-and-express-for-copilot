from flask import Flask, request, jsonify
import subprocess
import json
import sys
import time

app = Flask(__name__)

# Start MCP server process
mcp_process = subprocess.Popen(
    ['node', r'C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding='utf-8',
    errors='ignore',
    bufsize=1
)

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    try:
                # Add these debug lines
        print(f"==== RAW REQUEST ====", file=sys.stderr)
        print(f"Content-Type: {request.content_type}", file=sys.stderr)
        print(f"Raw data: {request.data}", file=sys.stderr)
        
        request_data = request.json
        print(f"Received: {request_data['method']}", file=sys.stderr)
        
        # Send to MCP server
        mcp_process.stdin.write(json.dumps(request_data) + '\n')
        mcp_process.stdin.flush()
        
        # Read complete response
        response = ""
        brace_count = 0
        while True:
            char = mcp_process.stdout.read(1)
            if not char:
                break
            response += char
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    break
        
        print(f"Response length: {len(response)}", file=sys.stderr)
        return jsonify(json.loads(response))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'running'})

if __name__ == '__main__':
    print("Starting wrapper on port 5000...")
    app.run(host='0.0.0.0', port=5000)