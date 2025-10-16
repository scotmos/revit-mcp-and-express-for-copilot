# MCP HTTP Wrapper for Revit

HTTP REST API wrapper for the Revit MCP (Model Context Protocol) server, enabling integration with Microsoft Copilot Studio and Power Automate.

## 🎯 Status: Production Ready (with Limitations)

**Current Setup**: Proven decoupled architecture using per-request subprocess execution

### ✅ Working Features
- Bulk family grading by category
- CSV export with 17-column detailed format or 5-column quick format
- Copilot Studio integration (via ngrok tunnel)
- REST API endpoints for all 17 MCP tools
- Health checks and monitoring

### ⚠️ Known Limitations
- **Detailed mode timeout** in Copilot Studio (30-60 sec vs ~30 sec Azure limit) → **Use Power Automate instead**
- **ngrok free tier** URL changes on restart → Requires connector update
- **Dedicated PowerShell window** required for Flask server

### 🏗️ Architecture

```
Copilot Studio / Power Automate
    ↓ (HTTPS)
Azure API Management
    ↓ (HTTPS)
ngrok Tunnel (Public)
    ↓ (HTTP localhost:5000)
simple_rest_api.py (Flask)
    ↓ (subprocess.run per request)
Node MCP Server (build/index.js)
    ↓ (Socket port 8080)
Revit MCP Plugin
    ↓
Revit 2024
```

**Key Design**: Each HTTP request spawns a fresh Node.js process via stdin/stdout piping. This avoids persistent subprocess crashes while maintaining reliability.

---

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete setup instructions with troubleshooting
- **[POWER_AUTOMATE_INTEGRATION.md](POWER_AUTOMATE_INTEGRATION.md)** - Timeout workaround for long operations
- **[ADDING_BULK_GRADING_TO_COPILOT.md](ADDING_BULK_GRADING_TO_COPILOT.md)** - Copilot Studio connector setup
- **[COPILOT_STUDIO_QUICKSTART.md](COPILOT_STUDIO_QUICKSTART.md)** - Quick reference for all 17 tools

---

## 🚀 Quick Start

### Prerequisites

- Autodesk Revit 2024 (running with document open)
- Python 3.12+ with `flask` and `flask-cors`
- Node.js (any recent version)
- ngrok account (free tier OK for testing)
- Copilot Studio access

### Installation

```powershell
# 1. Install Python dependencies
cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http
pip install flask flask-cors

# 2. Install ngrok
# Download from https://ngrok.com/download
# Authenticate: ngrok config add-authtoken YOUR_TOKEN

# 3. Verify Revit plugin is installed (already done if you're here)
```

### Starting the Server

**Option 1: Use Startup Scripts** (Recommended)

```powershell
# Terminal 1: Start Flask server
.\start_server.ps1

# Terminal 2: Start ngrok tunnel
.\start_ngrok.ps1
```

**Option 2: Manual Start**

```powershell
# Terminal 1: Start Flask server in dedicated window
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http; python simple_rest_api.py"

# Terminal 2: Start ngrok
ngrok http 5000
```

### Testing

```powershell
# Health check (local)
Invoke-RestMethod -Uri "http://localhost:5000/health"

# Health check (via ngrok)
Invoke-RestMethod -Uri "https://YOUR_NGROK_URL/health"

# Grade families (detailed mode)
$body = @{
    category = "Doors"
    gradeType = "detailed"
    includeTypes = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/tools/grade_all_families_by_category" `
  -Method POST -Body $body -ContentType "application/json" -TimeoutSec 120
```

**Expected Result**:
```json
{
  "success": true,
  "totalElements": 142,
  "avgScore": 96.4,
  "csvFilePath": "C:\\...\\RevitFamilyGrades_....csv",
  "gradeDistribution": {"A": 132, "D": 10, "F": 0},
  "categories": ["Doors"]
}
```

---

## 🎛️ API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/tools/list` | List available tools |
| POST | `/api/tools/grade_all_families_by_category` | Grade families by category |

### Example Request

```http
POST /api/tools/grade_all_families_by_category
Content-Type: application/json

{
  "category": "Doors",
  "gradeType": "detailed",
  "includeTypes": true,
  "outputPath": ""
}
```

### Example Response

```json
{
  "success": true,
  "totalElements": 142,
  "avgScore": 96.4,
  "csvFilePath": "C:\\Users\\...\\RevitFamilyGrades_....csv",
  "gradeDistribution": {
    "A": 132,
    "B": 0,
    "C": 0,
    "D": 10,
    "F": 0,
    "ERROR": 0
  },
  "categories": ["Doors"],
  "timestamp": "2025-10-15 12:23:51",
  "revitFileName": "Snowdon Towers Sample Architectural"
}
```

---

## 🔧 Troubleshooting

### Server won't start / exits immediately
**Solution**: Must use dedicated PowerShell window (see `start_server.ps1`)

### 404 Not Found
**Check**: 
- Flask server running on port 5000
- ngrok forwarding correctly
- Copilot connector Base URL is `/`

### 500 Timeout in Copilot Studio
**Cause**: Detailed mode exceeds Azure timeout (~30 sec)  
**Solution**: Use **Power Automate** instead (see `POWER_AUTOMATE_INTEGRATION.md`)

### ngrok URL changed
**Solution**: Update Copilot Studio connector host with new ngrok URL

**See full troubleshooting guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#troubleshooting)

---

## 📊 Test Results

**SnowdonTowers Sample Project**:
- ✅ 142 door instances graded
- ✅ Average score: 96.4/100
- ✅ Grade distribution: 132 A, 10 D, 0 F
- ✅ CSV export successful with 17 columns
- ✅ Grading time: 30-60 seconds (detailed mode)

**Categories Tested**:
- Doors: 142 instances
- Windows: 106 instances
- Furniture: Various counts

---

## 🏭 Production Deployment

### Pre-Production Checklist

- [ ] Replace ngrok with permanent solution (Azure VM or paid ngrok plan)
- [ ] Add API key authentication
- [ ] Add rate limiting (Flask-Limiter)
- [ ] Set up monitoring (Application Insights)
- [ ] Configure Power Automate flows for long operations
- [ ] Create automated health checks
- [ ] Document URL update procedure
- [ ] Set up backup/failover strategy
- [ ] Test error handling and retry logic

### Deployment Options

1. **Azure VM** (Recommended for production)
   - Permanent public IP
   - No session limits
   - Full control over infrastructure

2. **ngrok Paid Plan** ($8/month)
   - Static domains
   - No session timeouts
   - Quick to set up

3. **Cloudflare Tunnel** (Free alternative)
   - Better persistence than ngrok free
   - No session limits
   - Requires Cloudflare account

---

## 🤝 Contributing

This is a working production setup for Revit MCP integration. Improvements welcome!

### Key Files

**Working Files** (Use these):
- `simple_rest_api.py` - Flask server with per-request subprocess
- `start_server.ps1` - Server startup script
- `start_ngrok.ps1` - ngrok startup script
- `DEPLOYMENT_GUIDE.md` - Complete setup documentation

**Deprecated Files** (Don't use):
- `http_wrapper.py` - Persistent subprocess crashes
- `simple_wrapper.py` - Same crashes
- Other experimental wrappers

---

## 📝 License

See [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- Built on Model Context Protocol (MCP) by Anthropic
- Integrates with Microsoft Copilot Studio and Power Automate
- Uses ngrok for public tunneling
- Autodesk Revit 2024 platform

---

## 📞 Support

See documentation:
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete setup
- [POWER_AUTOMATE_INTEGRATION.md](POWER_AUTOMATE_INTEGRATION.md) - Timeout solutions
- [ADDING_BULK_GRADING_TO_COPILOT.md](ADDING_BULK_GRADING_TO_COPILOT.md) - Copilot Studio setup

Check logs:
- Revit: `C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Logs\`
- ngrok: http://localhost:4040
- Flask: Console output in dedicated PowerShell window


# Custom host and port
python http_wrapper.py --host 0.0.0.0 --port 8080 python your-mcp-server.py

python http_wrapper.py --port 3000 npx -y @modelcontextprotocol/server-filesystem .
```

### Command Line Options

```
--host HOST     Host to bind to (default: 127.0.0.1 - localhost only)
                Use 0.0.0.0 to allow network access
--port PORT     Port to bind to (default: 5000)
--debug         Enable Flask debug mode
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/mcp` | Main JSON-RPC endpoint |
| `GET` | `/mcp` | Server-Sent Events streaming |
| `GET` | `/health` | Health check |

### Supported MCP Methods

- `initialize` - MCP handshake and capability negotiation
- `tools/list` - List available tools
- `tools/call` - Execute a tool
- `prompts/list` - List available prompts
- `prompts/get` - Retrieve a prompt
- `resources/list` - List available resources
- `resources/read` - Read a resource

## Usage Examples

### 1. Initialize Connection

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
      "clientInfo": {"name": "my-client", "version": "1.0.0"}
    },
    "id": 1
  }'
```

### 2. List Available Tools

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}'
```

### 3. Call a Tool

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "read_file",
      "arguments": {"path": "/path/to/file.txt"}
    },
    "id": 3
  }'
```

### 4. Get a Prompt

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "prompts/get",
    "params": {
      "name": "code_review",
      "arguments": {"language": "python"}
    },
    "id": 4
  }'
```

### 5. Read a Resource

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "resources/read",
    "params": {
      "uri": "file:///path/to/resource.txt"
    },
    "id": 5
  }'
```

### 6. Server-Sent Events Stream

```bash
curl -H "Accept: text/event-stream" http://127.0.0.1:5000/mcp
```

### 7. Health Check

```bash
curl http://127.0.0.1:5000/health
```

## Session Management

Use the optional `Mcp-Session-Id` header to maintain session state:

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: unique-session-123" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Response Format

All responses follow JSON-RPC 2.0 format:

### Success Response
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [...]
  },
  "id": 1
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": "Unknown method: invalid/method"
  },
  "id": 1
}
```

## Common Error Codes

| Code | Message | Description |
|------|---------|-------------|
| `-32700` | Parse error | Invalid JSON |
| `-32600` | Invalid Request | Malformed JSON-RPC |
| `-32601` | Method not found | Unknown MCP method |
| `-32602` | Invalid params | Missing/invalid parameters |
| `-32603` | Internal error | Server-side error |

## Examples with Popular MCP Servers

### File System Server
```bash
# Install and run
npm install -g @modelcontextprotocol/server-filesystem
python http_wrapper.py -- npx @modelcontextprotocol/server-filesystem /path/to/directory
```

### SQLite Server
```bash
# Install and run
npm install -g @modelcontextprotocol/server-sqlite
python http_wrapper.py -- npx @modelcontextprotocol/server-sqlite /path/to/database.db
```

### Git Server
```bash
# Install and run
npm install -g @modelcontextprotocol/server-git
python http_wrapper.py -- npx @modelcontextprotocol/server-git --repository /path/to/repo
```

## Security Considerations

- **Default localhost binding**: Server binds to `127.0.0.1` by default for security
- **Origin validation**: Validates `Origin` headers when provided
- **Network access**: Use `--host 0.0.0.0` only when network access is needed
- **Input validation**: All JSON-RPC requests are validated
- **Error handling**: Sensitive information is not exposed in error messages

## Troubleshooting

### Port Already in Use
```
❌ Error: Port 5000 is already in use!

Suggestions:
  • Try a different port: --port 5001
  • Check what's using port 5000: netstat -tulpn | grep 5000
  • Kill the conflicting process if it's safe to do so
```

### MCP Server Not Starting
- Check that the MCP server command is correct
- Verify the MCP server executable is in your PATH
- Look at the console output for MCP server error messages

### Connection Issues
- Verify the host and port are correct
- Check firewall settings if accessing from another machine
- Ensure the MCP server is running and responding

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Related

- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)
- [MCP Server Directory](https://github.com/modelcontextprotocol/servers)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

