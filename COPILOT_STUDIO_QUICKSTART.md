# Copilot Studio Setup - Quick Start

## Your Revit MCP HTTP Wrapper is Running!

**Local Access**: http://127.0.0.1:5000
**Network Access**: http://10.1.55.178:5000

## Available Tools (17 total):
1. `ai_element_filter` - Filter elements using AI criteria
2. `check_geometry_type` - Check if family geometry is mesh or solid
3. `check_geometry_type_detailed` - Detailed geometry analysis with grading
4. `color_elements` - Apply colors to elements by parameter values
5. `createWall` - Simple wall creation
6. `create_line_based_element` - Create walls, beams, pipes (advanced)
7. `create_point_based_element` - Create doors, windows, furniture
8. `create_surface_based_element` - Create floors, ceilings, roofs
9. `delete_element` - Delete elements by ID
10. `get_available_family_types` - List available family types
11. `get_current_view_elements` - Get elements in current view
12. `get_current_view_info` - Get current view information
13. `get_selected_elements` - Get currently selected elements
14. **`grade_all_families_by_category`** - **🆕 NEW!** Bulk family grading with CSV export
15. `operate_element` - Select, hide, color, isolate elements
16. `send_code_to_revit` - Execute C# code in Revit
17. `tag_all_walls` - Tag all walls in view

## For Copilot Studio (Cloud Access Required):

Since Copilot Studio runs in the cloud, it needs to access your server. Here are your options:

### Option A: ngrok (Easiest for testing)

1. Install ngrok: https://ngrok.com/download
2. Run:  `ngrok http 5000`
3. Use the https://xxxxx.ngrok.io URL in Copilot Studio

### Option B: Azure VM

1. Deploy server to Azure VM with public IP
2. Open port 5000 in NSG (Network Security Group)
3. Use the public IP in Copilot Studio

### Option C: Local Network Only

If Copilot Studio can access your local network:
- Use: http://10.1.55.178:5000

## Copilot Studio Configuration

### Create Custom Connector:

1. Go to **Power Platform** → **Custom Connectors**
2. **Create from blank**
3. **General**:
   - Name: `Revit MCP Server`
   - Host: `YOUR_NGROK_OR_IP:5000` or just `YOUR_NGROK_DOMAIN` (no port if using ngrok)
   - Base URL: `/`

4. **Security**: None (or add API key later)

5. **Definition** → Add **Action**:
   - **Summary**: List Revit Tools
   - **Description**: Get all available Revit MCP tools
   - **Operation ID**: list_tools
   - **Visibility**: important
   
   **Request**:
   - URL: `/mcp`
   - Method: `POST`
   - Headers:
     - `Content-Type`: `application/json`
   - Body:
     ```json
     {
       "jsonrpc": "2.0",
       "method": "tools/list",
       "id": "1"
     }
     ```

6. Add another **Action** for calling tools:
   - **Summary**: Call Revit Tool
   - **Operation ID**: call_tool
   
   **Request**:
   - URL: `/mcp`
   - Method: `POST`
   - Body (with parameters):
     ```json
     {
       "jsonrpc": "2.0",
       "method": "tools/call",
       "params": {
         "name": "@{parameters('toolName')}",
         "arguments": @{parameters('arguments')}
       },
       "id": "2"
     }
     ```
   
   **Parameters**:
   - `toolName` (string, required): Name of the tool to call
   - `arguments` (object, optional): Tool arguments as JSON

## Test from Copilot Studio

Once configured, you can call Revit tools like:

**Example 1: Get current view info**
```
Call tool: get_current_view_info
Arguments: {}
```

**Example 2: Check if element is mesh**
```
Call tool: check_geometry_type
Arguments: { "elementId": "12345" }
```

**Example 3: Get walls in view**
```
Call tool: get_current_view_elements
Arguments: { 
  "modelCategoryList": ["OST_Walls"],
  "limit": 10
}
```

**Example 4: Bulk grade all doors** 🆕
```
Call tool: grade_all_families_by_category
Arguments: {
  "category": "Doors",
  "gradeType": "detailed",
  "includeTypes": true
}
Returns: CSV report with 142 instances, avg score 96.4, grade distribution
```

## 🆕 New Feature: Bulk Family Grading

See detailed setup guide: **[ADDING_BULK_GRADING_TO_COPILOT.md](ADDING_BULK_GRADING_TO_COPILOT.md)**

Quick test:
- Analyzes ALL family instances by category
- Grades performance (A-F) using Autodesk criteria  
- Exports detailed CSV with 17 columns
- Provides statistics and recommendations
- Tested: 142 doors graded in SnowdonTowers, avg 96.4/100

## Important Notes:

1. **Revit must be running** with a document open
2. **MCP plugin must be loaded** and connected
3. **One request at a time** (stdio limitation)
4. **Check logs** at: `C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Logs\`

## Production Considerations:

For production use:
- [ ] Add API key authentication
- [ ] Use HTTPS (ngrok provides this)
- [ ] Add rate limiting
- [ ] Deploy to dedicated server
- [ ] Add error handling in Copilot Studio
- [ ] Monitor server health
