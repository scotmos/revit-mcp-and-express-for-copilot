# Copilot Studio Integration Guide

## Overview
This guide shows how to expose the Revit MCP server to Microsoft Copilot Studio via HTTP.

## Prerequisites
1. Revit 2024 must be running with the MCP plugin loaded
2. Python with Flask installed
3. Node.js installed

## Step 1: Start the HTTP Wrapper

Run the batch file:
```batch
cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http
start_revit_wrapper.bat
```

Or manually:
```bash
python http_wrapper.py --host 0.0.0.0 --port 5000 node "C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js"
```

The server will start on:
- Local: http://127.0.0.1:5000
- Network: http://YOUR_IP:5000 (e.g., http://10.1.55.178:5000)

## Step 2: Test the Endpoint

### Health Check
```bash
curl http://127.0.0.1:5000/health
```

Expected response:
```json
{"status": "healthy"}
```

### List Available Tools
Using PowerShell:
```powershell
$headers = @{"Content-Type"="application/json"}
$body = '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/mcp" -Method POST -Headers $headers -Body $body
```

Expected response will list all Revit MCP tools including:
- get_current_view_info
- get_current_view_elements  
- get_available_family_types
- create_line_based_element
- check_geometry_type (NEW!)
- And more...

### Call a Revit Tool
Example - Get current view info:
```powershell
$body = @{
    jsonrpc = "2.0"
    id = "2"
    method = "tools/call"
    params = @{
        name = "get_current_view_info"
        arguments = @{}
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://127.0.0.1:5000/mcp" -Method POST -Headers @{"Content-Type"="application/json"} -Body $body
```

### Check Geometry Type
Example - Check if element is mesh or solid:
```powershell
$body = @{
    jsonrpc = "2.0"
    id = "3"
    method = "tools/call"
    params = @{
        name = "check_geometry_type"
        arguments = @{
            elementId = "12345"  # Replace with actual element ID
        }
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://127.0.0.1:5000/mcp" -Method POST -Headers @{"Content-Type"="application/json"} -Body $body
```

## Step 3: Configure Copilot Studio

### Option A: Using Custom Connector

1. **Go to Copilot Studio** → Power Platform → Custom Connectors

2. **Create a new Custom Connector**:
   - **Display Name**: Revit MCP Server
   - **Host**: YOUR_IP:5000 (e.g., 10.1.55.178:5000)
   - **Base URL**: /

3. **Add an Action** for listing tools:
   - **Summary**: List Revit Tools
   - **Operation ID**: list_tools
   - **Visibility**: important
   - **Request**:
     - URL: /mcp
     - Method: POST
     - Body template:
       ```json
       {
         "jsonrpc": "2.0",
         "id": "1",
         "method": "tools/list",
         "params": {}
       }
       ```

4. **Add an Action** for calling tools:
   - **Summary**: Call Revit Tool
   - **Operation ID**: call_tool
   - **Request**:
     - URL: /mcp
     - Method: POST
     - Parameters:
       - toolName (string, required)
       - arguments (object, optional)
     - Body template:
       ```json
       {
         "jsonrpc": "2.0",
         "id": "2",
         "method": "tools/call",
         "params": {
           "name": "@{parameters('toolName')}",
           "arguments": @{parameters('arguments')}
         }
       }
       ```

### Option B: Using Direct HTTP Actions in Copilot

In your Copilot Studio agent, add HTTP actions directly:

1. **Add Action** → **HTTP Request**
2. **URL**: http://YOUR_IP:5000/mcp
3. **Method**: POST
4. **Headers**:
   ```
   Content-Type: application/json
   ```
5. **Body**: Dynamic based on the tool you want to call

## Available Revit MCP Tools

Once connected, these tools will be available in Copilot Studio:

| Tool Name | Description |
|-----------|-------------|
| `get_current_view_info` | Get information about the current Revit view |
| `get_current_view_elements` | Get all elements in the current view |
| `get_available_family_types` | List available family types in the project |
| `create_line_based_element` | Create line-based elements (walls, beams, etc.) |
| `create_point_based_element` | Create point-based elements (doors, windows, etc.) |
| `create_surface_based_element` | Create surface-based elements (floors, ceilings, etc.) |
| `check_geometry_type` | Check if family geometry is mesh or solid |
| `delete_element` | Delete elements by ID |
| `tag_all_walls` | Tag all walls in the model |
| `ai_element_filter` | Filter elements using AI criteria |
| `send_code_to_revit` | Execute C# code in Revit |

## Troubleshooting

### Connection Issues
- Ensure Revit is running with the MCP plugin loaded
- Check firewall allows port 5000
- Verify the Revit MCP plugin shows "Connected" status

### Tool Execution Fails
- Check Revit has an active document open
- Ensure element IDs are valid
- Check Revit plugin logs at: `C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Logs\`

### Network Access
For Copilot Studio to access from the cloud, you need:
- Public IP or ngrok tunnel
- Or Azure VM with public endpoint
- Or VPN connection

Example with ngrok:
```bash
ngrok http 5000
```
Then use the ngrok URL (e.g., https://abc123.ngrok.io) in Copilot Studio.

## Security Considerations

**For Production:**
1. Add API key authentication
2. Use HTTPS (not HTTP)
3. Restrict CORS origins
4. Use ngrok or Azure for secure tunneling
5. Monitor and rate-limit requests

## Example Copilot Studio Conversation Flow

User: "What walls are in the current view?"

Copilot Studio:
1. Calls `get_current_view_elements` tool
2. Filters for walls
3. Responds with wall list

User: "Check if this family is mesh-based"

Copilot Studio:
1. Gets element ID from context or asks user
2. Calls `check_geometry_type` with element ID
3. Analyzes response
4. Reports whether it's mesh or solid with details
