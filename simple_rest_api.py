#!/usr/bin/env python3
"""
Simple REST API wrapper for Revit MCP Server
Uses decoupled approach - pipes JSON-RPC to Node server via stdin
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Copilot Studio

# Path to the Node MCP server
NODE_SERVER_PATH = r"C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js"

def call_mcp_tool(tool_name, arguments):
    """
    Call an MCP tool by piping JSON-RPC to the Node server
    Returns the result from the tool call
    """
    # Create JSON-RPC messages (same as our successful tests)
    initialize_msg = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "copilot-studio-client", "version": "1.0.0"}
        },
        "id": 1
    }
    
    tool_call_msg = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 2
    }
    
    # Combine messages with newlines (stdin format)
    input_data = json.dumps(initialize_msg) + "\n" + json.dumps(tool_call_msg) + "\n"
    
    logger.info(f"Calling MCP tool: {tool_name}")
    logger.debug(f"Arguments: {arguments}")
    
    try:
        # Run Node server with piped input (same as our tests)
        # Use UTF-8 encoding to handle Node.js output properly
        result = subprocess.run(
            ["node", NODE_SERVER_PATH],
            input=input_data,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace invalid characters instead of crashing
            timeout=300  # 5 minute timeout for large projects
        )
        
        # Parse the output - look for the tool response
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            logger.info(f"MCP server stdout lines: {len(lines)}")
            # Log first few lines for debugging
            for i, line in enumerate(lines[:5]):
                logger.debug(f"Line {i}: {line[:200]}")
        else:
            logger.error(f"No stdout from MCP server. stderr: {result.stderr}")
            return {"success": False, "error": "No output from MCP server"}
        
        for line in lines:
            try:
                response = json.loads(line)
                # Find the response with id=2 (our tool call)
                if isinstance(response, dict) and response.get('id') == 2:
                    logger.info(f"Found response with id=2: {json.dumps(response)[:500]}")
                    if 'result' in response:
                        result_data = response['result']
                        # Check if result contains nested content structure
                        if isinstance(result_data, dict) and 'content' in result_data:
                            # Extract from content array
                            if isinstance(result_data['content'], list) and len(result_data['content']) > 0:
                                content_item = result_data['content'][0]
                                if 'text' in content_item:
                                    # Try to parse the text as JSON (it contains the actual grading data)
                                    try:
                                        actual_data = json.loads(content_item['text'])
                                        if actual_data.get('success'):
                                            return {"success": True, "data": actual_data}
                                        else:
                                            return {"success": False, "error": content_item.get('text', 'Unknown error')}
                                    except json.JSONDecodeError:
                                        # Text is not JSON, return as error message
                                        return {"success": False, "error": content_item.get('text', 'Unknown error')}
                        else:
                            # Direct result structure
                            return {"success": True, "data": result_data}
                    elif 'error' in response:
                        return {"success": False, "error": response['error']}
            except json.JSONDecodeError:
                continue
        
        # If we get here, no valid response found
        logger.error(f"No valid response found. stdout: {result.stdout[:500]}")
        return {"success": False, "error": "No valid response from MCP server"}
        
    except subprocess.TimeoutExpired:
        logger.error("MCP server timeout")
        return {"success": False, "error": "Request timeout (5 minutes)"}
    except Exception as e:
        logger.error(f"Error calling MCP server: {str(e)}")
        return {"success": False, "error": str(e)}


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Revit MCP REST API"})


@app.route('/api/tools/grade_all_families_by_category', methods=['POST'])
def grade_all_families_by_category():
    """
    Grade all families by category
    Expected JSON body:
    {
        "category": "Doors",
        "gradeType": "detailed",
        "includeTypes": true,
        "outputPath": ""  // optional
    }
    """
    try:
        data = request.get_json()
        logger.info(f"Received request data: {data}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Extract parameters with defaults
        category = data.get('category', 'All') if data else 'All'
        grade_type = data.get('gradeType', 'detailed') if data else 'detailed'
        include_types = data.get('includeTypes', True) if data else True
        output_path = data.get('outputPath', '') if data else ''
        
        logger.info(f"Extracted: category={category}, gradeType={grade_type}, includeTypes={include_types}")
        
        # Build arguments
        arguments = {
            "category": category,
            "gradeType": grade_type,
            "includeTypes": include_types
        }
        
        if output_path:
            arguments["outputPath"] = output_path
        
        # Call the MCP tool
        result = call_mcp_tool("grade_all_families_by_category", arguments)
        
        if result.get('success'):
            # Extract data from MCP response
            mcp_data = result.get('data', {})
            
            # Format response for Copilot Studio
            response_data = {
                "success": True,
                "totalElements": mcp_data.get('totalElements', 0),
                "avgScore": mcp_data.get('avgScore', 0),
                "csvFilePath": mcp_data.get('csvFilePath', ''),
                "gradeDistribution": mcp_data.get('gradeDistribution', {}),
                "categories": mcp_data.get('categories', []),
                "timestamp": mcp_data.get('timestamp', ''),
                "revitFileName": mcp_data.get('revitFileName', '')
            }
            
            logger.info(f"Successfully graded {response_data['totalElements']} elements")
            return jsonify(response_data)
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"MCP tool failed: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 500
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tools/list', methods=['GET'])
def list_tools():
    """List available MCP tools"""
    return jsonify({
        "tools": [
            {
                "name": "grade_all_families_by_category",
                "description": "Grade all family instances by category and export to CSV",
                "endpoint": "/api/tools/grade_all_families_by_category"
            }
        ]
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("       Revit MCP Simple REST API")
    print("="*60)
    print(f"\nEndpoints:")
    print(f"  GET  /health - Health check")
    print(f"  GET  /api/tools/list - List available tools")
    print(f"  POST /api/tools/grade_all_families_by_category - Grade families")
    print(f"\nExample request:")
    print(f'  POST http://localhost:5000/api/tools/grade_all_families_by_category')
    print(f'  Body: {{"category":"Doors","gradeType":"detailed","includeTypes":true}}')
    print(f"\nServer starting on http://0.0.0.0:5000")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
