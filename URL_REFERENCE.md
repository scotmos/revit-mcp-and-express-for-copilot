# Copilot Studio URLs - Quick Reference

## Your ngrok Public URL
```
https://6c701ec65166.ngrok-free.app
```

## Endpoints Available

### Health Check (GET)
```
https://6c701ec65166.ngrok-free.app/health
```
Returns: `{"status": "running"}`

### MCP Endpoint (POST)
```
https://6c701ec65166.ngrok-free.app/mcp
```
This is where you send all tool calls

---

## For Power Platform Custom Connector

### General Tab:
```
Host: 6c701ec65166.ngrok-free.app
Base URL: /
Scheme: HTTPS
```

### Definition Tab (Actions):
For each action you create:
```
URL: /mcp
Method: POST
Headers:
  Content-Type: application/json
```

**Example Action - Get Current View Info:**
```json
Body Template:
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

**Example Action - Check Geometry (with parameter):**
```json
Body Template:
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "check_geometry_type",
    "arguments": {
      "elementId": "@{parameters('elementId')}"
    }
  },
  "id": "2"
}

Parameters to add:
- Name: elementId
- Type: string
- Required: Yes
```

---

## For Direct Testing (PowerShell)

```powershell
# Test Health
Invoke-RestMethod -Uri "https://6c701ec65166.ngrok-free.app/health"

# Test MCP Call
$body = @{
    jsonrpc = "2.0"
    method = "tools/call"
    params = @{
        name = "get_current_view_info"
        arguments = @{}
    }
    id = "test"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://6c701ec65166.ngrok-free.app/mcp" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

---

## For Direct Testing (curl)

```bash
# Health check
curl https://6c701ec65166.ngrok-free.app/health

# MCP call
curl -X POST https://6c701ec65166.ngrok-free.app/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_current_view_info",
      "arguments": {}
    },
    "id": "1"
  }'
```

---

## Common Mistakes ❌

### DON'T DO THIS in Custom Connector:
```
❌ Host: https://6c701ec65166.ngrok-free.app
❌ Host: 6c701ec65166.ngrok-free.app/mcp
❌ Base URL: /mcp
```

### DO THIS instead ✅:
```
✅ Host: 6c701ec65166.ngrok-free.app
✅ Base URL: /
✅ Action URL: /mcp
```

---

## Testing Your Setup

1. **Browser Test**: Open `test_page.html`
2. **Health Check**: Visit https://6c701ec65166.ngrok-free.app/health
3. **MCP Call**: Use PowerShell or curl commands above

---

## When URL Changes

⚠️ **Important**: Free ngrok URLs change every time you restart ngrok!

If you restart ngrok, you'll get a new URL like:
```
https://NEW_RANDOM_ID.ngrok-free.app
```

Then you need to:
1. Update your Custom Connector host
2. Update this reference card
3. Update test_page.html

**Solution**: Get ngrok paid plan for static URL, or deploy to Azure.

---

## All Available Tools (16)

Send to `/mcp` endpoint with this format:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "TOOL_NAME_HERE",
    "arguments": { /* tool-specific args */ }
  },
  "id": "unique_id"
}
```

**Available TOOL_NAMES:**
1. get_current_view_info
2. get_current_view_elements
3. check_geometry_type ⭐ NEW
4. get_available_family_types
5. get_selected_elements
6. create_line_based_element
7. create_point_based_element
8. create_surface_based_element
9. delete_element
10. operate_element
11. ai_element_filter
12. color_elements
13. tag_all_walls
14. send_code_to_revit
15. createWall
16. use_module
