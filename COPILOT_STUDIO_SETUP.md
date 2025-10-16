# Copilot Studio Configuration Guide

## Your Public Endpoint
**ngrok URL**: https://6c701ec65166.ngrok-free.app

✅ Health check works: https://6c701ec65166.ngrok-free.app/health

## Copilot Studio Setup Instructions

### Step 1: Create Custom Connector

1. Go to **https://make.powerautomate.com**
2. Click **More** → **Discover all** → **Custom Connectors**
3. Click **+ New custom connector** → **Create from blank**

### Step 2: General Settings

- **Connector name**: `Revit MCP Server`
- **Description**: `Connect to Revit via MCP protocol to create elements, query data, and execute commands`
- **Host**: `6c701ec65166.ngrok-free.app`
- **Base URL**: `/`
- **Scheme**: `HTTPS` (ngrok provides HTTPS)

Click **Security** →

### Step 3: Security (Optional)

For now, select **No authentication**

(Later you can add API key authentication)

Click **Definition** →

### Step 4: Add Actions

#### Action 1: Get Current View Info

- **Summary**: `Get Current View Info`
- **Description**: `Get information about the currently active Revit view`
- **Operation ID**: `get_current_view_info`
- **Visibility**: `important`

**Request**:
- Click **+ Import from sample**
- **Verb**: `POST`
- **URL**: `https://6c701ec65166.ngrok-free.app/mcp`
- **Headers**: 
  ```
  Content-Type: application/json
  ```
- **Body**:
  ```json
  {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_current_view_info",
      "arguments": {}
    },
    "id": "1"
  }
  ```
- Click **Import**

**Response**:
- Use default schema

---

#### Action 2: Get Elements in Current View

- **Summary**: `Get Current View Elements`
- **Description**: `Get elements from the current Revit view, optionally filtered by category`
- **Operation ID**: `get_current_view_elements`

**Request**:
- **Verb**: `POST`
- **URL**: `https://6c701ec65166.ngrok-free.app/mcp`
- **Headers**: 
  ```
  Content-Type: application/json
  ```
- **Body**:
  ```json
  {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_current_view_elements",
      "arguments": {
        "modelCategoryList": [],
        "limit": 50
      }
    },
    "id": "2"
  }
  ```

Add **Parameters**:
- Name: `categoryList`, Type: `array`, Required: `No`, Description: `Categories to filter (e.g., ["OST_Walls"])`
- Name: `limit`, Type: `integer`, Default: `50`, Description: `Maximum elements to return`

---

#### Action 3: Check Geometry Type (NEW!)

- **Summary**: `Check Geometry Type`
- **Description**: `Check if a family instance's geometry is mesh or solid`
- **Operation ID**: `check_geometry_type`

**Request**:
- **Verb**: `POST`
- **URL**: `https://6c701ec65166.ngrok-free.app/mcp`
- **Body**:
  ```json
  {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "check_geometry_type",
      "arguments": {
        "elementId": "12345"
      }
    },
    "id": "3"
  }
  ```

Add **Parameter**:
- Name: `elementId`, Type: `string`, Required: `Yes`, Description: `The ElementId to check`

---

#### Action 4: Create Wall (Advanced)

- **Summary**: `Create Line Based Element`
- **Description**: `Create walls, beams, or other line-based elements`
- **Operation ID**: `create_line_based_element`

**Request**:
- **Verb**: `POST`
- **URL**: `https://6c701ec65166.ngrok-free.app/mcp`
- **Body**: (This is complex, you can build it in Copilot Studio using dynamic parameters)

---

### Step 5: Test the Connector

1. Click **Test** tab
2. Click **+ New connection**
3. Click **Create connection**
4. Test each action:
   - Select `Get Current View Info`
   - Click **Test operation**
   - Should return view information if Revit is open

### Step 6: Create Copilot Studio Agent

1. Go to **https://copilotstudio.microsoft.com**
2. Create a new **Agent**
3. Click **Actions** → **+ Add an action**
4. Search for your **Revit MCP Server** connector
5. Add the actions you want to use

### Step 7: Configure Agent Topics

Create topics like:

**Topic: Get Current View**
- **Trigger phrases**: 
  - "What's the current view?"
  - "Show me the current view info"
  - "Get view details"
  
- **Action**: Call `Get Current View Info`
- **Message**: Show the returned information

**Topic: Check Element Geometry**
- **Trigger phrases**:
  - "Is this element a mesh?"
  - "Check geometry type"
  - "Is element {elementId} solid or mesh?"

- **Variables**: Ask for `elementId` if not provided
- **Action**: Call `Check Geometry Type` with `elementId`
- **Message**: Parse and display the results (hasSolids, hasMeshes, details)

**Topic: List Walls**
- **Trigger phrases**:
  - "Show me walls"
  - "List walls in view"
  
- **Action**: Call `Get Current View Elements` with `categoryList = ["OST_Walls"]`
- **Message**: Format and display the wall list

## Testing Your Setup

### Test 1: Direct API Call

```powershell
$body = @{
    jsonrpc = "2.0"
    method = "tools/call"
    params = @{
        name = "get_current_view_info"
        arguments = @{}
    }
    id = "test1"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://6c701ec65166.ngrok-free.app/mcp" -Method POST -ContentType "application/json" -Body $body
```

### Test 2: Check Geometry (requires element ID from Revit)

```powershell
$body = @{
    jsonrpc = "2.0"
    method = "tools/call"
    params = @{
        name = "check_geometry_type"
        arguments = @{
            elementId = "REPLACE_WITH_ACTUAL_ID"
        }
    }
    id = "test2"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://6c701ec65166.ngrok-free.app/mcp" -Method POST -ContentType "application/json" -Body $body
```

## Important Notes

1. **Keep ngrok running**: Don't close the ngrok terminal
2. **Revit must be open**: With a document loaded and MCP plugin connected
3. **HTTP wrapper must be running**: Keep the Python server running
4. **Free ngrok URL changes**: Every time you restart ngrok, the URL changes. For production, get a paid ngrok account or deploy to Azure.

## All Available Tools

You can create actions for any of these 16 tools:

1. ✅ `get_current_view_info` - Get current view details
2. ✅ `get_current_view_elements` - Get elements in view
3. ✅ `check_geometry_type` - Check if element is mesh/solid (NEW!)
4. `get_available_family_types` - List family types
5. `get_selected_elements` - Get selected elements
6. `create_line_based_element` - Create walls, beams, pipes
7. `create_point_based_element` - Create doors, windows, furniture
8. `create_surface_based_element` - Create floors, ceilings
9. `delete_element` - Delete elements
10. `operate_element` - Select, hide, color elements
11. `ai_element_filter` - AI-powered element filtering
12. `color_elements` - Color elements by parameter
13. `tag_all_walls` - Tag all walls in view
14. `send_code_to_revit` - Execute C# code
15. `createWall` - Simple wall creation
16. `use_module` - Use search modules

## Next Steps

1. ✅ ngrok is running
2. ✅ HTTP wrapper is running  
3. ⬜ Create Custom Connector in Power Platform
4. ⬜ Test connector actions
5. ⬜ Create Copilot Studio agent
6. ⬜ Add topics and test conversations

Good luck! 🚀
