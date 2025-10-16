# Revit MCP Express Server - Version 2.0

## Overview

The Express Server version provides a persistent HTTP API for grading Revit families. It's more scalable and robust than the batch script approach, while keeping backward compatibility.

**Date**: October 16, 2025  
**Status**: ✅ Ready for testing  
**Author**: Moses Scott (scotmos)

## Architecture

```
Power Automate / Copilot Actions
    ↓ (HTTP POST)
Express Server (port 3000)
    ↓ (spawns subprocess per request)
Node MCP Server (stdio)
    ↓ (WebSocket port 8080)
Revit Plugin C#
    ↓ (Revit API)
Revit Document
```

## Key Improvements Over v1.0 Batch Script

| Feature | v1.0 Batch | v2.0 Express | Benefit |
|---------|------------|--------------|---------|
| **Server Type** | Per-request process | Persistent HTTP server | Better performance |
| **Timeout** | 120 seconds (hardcoded) | 600 seconds (configurable) | Large models supported |
| **Protocol** | DOS command | Standard HTTP REST API | Universal compatibility |
| **Error Handling** | Basic | Comprehensive with logging | Easier debugging |
| **Parameters** | Fixed in JSON file | Dynamic via HTTP body | Flexible grading |
| **CORS** | N/A | Enabled | Browser/web app support |
| **Monitoring** | None | Health endpoint + logs | Production ready |

## Installation

### Prerequisites

✅ Node.js 16+ installed  
✅ Revit 2024 running with document open  
✅ MCP plugin loaded and switch ON  

### Step 1: Install Dependencies

```cmd
cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http
npm install
```

This installs:
- `express` - HTTP server framework
- `cors` - Cross-origin resource sharing

### Step 2: Start the Server

**Option A: Using batch file (Recommended)**
```cmd
start_express.bat
```

**Option B: Direct command**
```cmd
node express-server.js
```

The server will start on **http://localhost:3000**

## API Endpoints

### GET /health

Health check endpoint.

**Request:**
```http
GET http://localhost:3000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Revit MCP Express Server",
  "version": "2.0.0",
  "timestamp": "2025-10-16T15:23:45.000Z"
}
```

### POST /api/grade-families

Grade all families by category and export to CSV.

**Request:**
```http
POST http://localhost:3000/api/grade-families
Content-Type: application/json

{
  "category": "Doors",
  "gradeType": "detailed",
  "includeTypes": true,
  "outputPath": ""
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `category` | string | No | `"All"` | Category name (Doors, Windows, Furniture, etc.) or "All" |
| `gradeType` | string | No | `"detailed"` | "quick" (5 columns) or "detailed" (17 columns) |
| `includeTypes` | boolean | No | `true` | Include all type instances (true) or unique families only (false) |
| `outputPath` | string | No | `""` | Custom CSV output path (empty = Downloads folder) |

**Response (Success):**
```json
{
  "success": true,
  "totalElements": 142,
  "avgScore": 96.4,
  "csvFilePath": "C:\\Users\\ScottM\\Downloads\\RevitFamilyGrades_Project1_20251016_152345.csv",
  "gradeDistribution": {
    "A": 132,
    "B": 0,
    "C": 0,
    "D": 10,
    "F": 0,
    "ERROR": 0
  },
  "categories": ["Doors"],
  "timestamp": "2025-10-16 15:23:45",
  "revitFileName": "SnowdonTowers.rvt",
  "duration": 45230
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Request timeout after 600 seconds",
  "duration": 600000
}
```

### GET /api/info

Get server information and usage examples.

**Request:**
```http
GET http://localhost:3000/api/info
```

**Response:** Server metadata and API documentation.

## Testing

### Test 1: Health Check (PowerShell)

```powershell
Invoke-RestMethod -Uri "http://localhost:3000/health"
```

Expected output:
```
status      : healthy
service     : Revit MCP Express Server
version     : 2.0.0
timestamp   : 2025-10-16T15:23:45.000Z
```

### Test 2: Quick Grading (PowerShell)

```powershell
$body = @{
    category = "Furniture"
    gradeType = "quick"
    includeTypes = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/grade-families" `
    -Method POST `
    -Body $body `
    -ContentType "application/json" `
    -TimeoutSec 120
```

### Test 3: Detailed Grading (curl)

```cmd
curl -X POST http://localhost:3000/api/grade-families ^
     -H "Content-Type: application/json" ^
     -d "{\"category\":\"Doors\",\"gradeType\":\"detailed\",\"includeTypes\":true}"
```

### Test 4: Batch File with Fallback

```cmd
run_grade.bat
```

This will:
1. Try Express server (HTTP) if running
2. Fall back to direct MCP call if not

## Power Automate Integration

### Desktop Flow Setup

**Action**: HTTP Request

| Field | Value |
|-------|-------|
| **Method** | POST |
| **URL** | `http://localhost:3000/api/grade-families` |
| **Headers** | `Content-Type: application/json` |
| **Body** | See below |
| **Timeout** | 600 seconds |

**Body (JSON):**
```json
{
  "category": "Doors",
  "gradeType": "detailed",
  "includeTypes": true
}
```

**Variables Produced:**
- `%StatusCode%` - HTTP status (200 = success)
- `%ResponseHeaders%` - Response headers
- `%ResponseBody%` - JSON response body

### Parse Response

**Action**: Convert JSON to custom object

**Input**: `%ResponseBody%`

**Output**: `%GradingResult%`

**Access values:**
- `%GradingResult['totalElements']%`
- `%GradingResult['avgScore']%`
- `%GradingResult['csvFilePath']%`

### Backup: Run DOS Command

If Express server is not available, the batch file will fall back to direct MCP call:

**Action**: Run DOS command

| Field | Value |
|-------|-------|
| **Command** | `C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http\run_grade.bat` |
| **Working folder** | `C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http` |
| **Timeout** | 600 seconds |

## Copilot Actions Integration

### Create Custom Action

1. Go to **Copilot Studio** → **Actions**
2. Create **HTTP Action**
3. Configure:
   - **URL**: `http://localhost:3000/api/grade-families`
   - **Method**: POST
   - **Authentication**: None (local)
   - **Body**: JSON with dynamic parameters

### Example Action Definition

```yaml
name: Grade Revit Families
description: Grade all family instances by category
inputs:
  - name: category
    type: string
    required: false
    default: "All"
  - name: gradeType
    type: string
    required: false
    default: "detailed"
  - name: includeTypes
    type: boolean
    required: false
    default: true
outputs:
  - name: totalElements
    type: number
  - name: avgScore
    type: number
  - name: csvFilePath
    type: string
  - name: gradeDistribution
    type: object
```

### Using in Copilot

**User**: "Grade all doors in the Revit model"

**Copilot**: Calls action with:
```json
{
  "category": "Doors",
  "gradeType": "detailed",
  "includeTypes": true
}
```

**Copilot Response**: "I've graded 142 doors with an average score of 96.4/100. The CSV report is saved at C:\Users\ScottM\Downloads\..."

## Configuration

### Change Port

Edit `express-server.js`:
```javascript
const PORT = process.env.PORT || 3000; // Change 3000 to your port
```

Or set environment variable:
```cmd
set PORT=5000
node express-server.js
```

### Change Timeout

Edit `express-server.js` line 38:
```javascript
const timeout = 600000; // 10 minutes (in milliseconds)
```

### Change MCP Server Path

Edit `express-server.js` line 23:
```javascript
const MCP_SERVER_PATH = path.join('C:', 'Your', 'Custom', 'Path', 'index.js');
```

## Troubleshooting

### Server Won't Start

**Error**: `Error: listen EADDRINUSE: address already in use :::3000`

**Cause**: Port 3000 is already in use.

**Fix**:
```powershell
# Find process using port 3000
netstat -ano | Select-String ":3000"

# Kill process (replace <PID> with actual process ID)
Stop-Process -Id <PID> -Force
```

### Timeout Error

**Error**: `Request timeout after 600 seconds`

**Cause**: Grading took longer than timeout.

**Solutions**:
1. Increase timeout in `express-server.js`
2. Use `"gradeType": "quick"` for faster grading
3. Grade smaller categories instead of "All"

### CSV Not in Downloads Folder

**Cause**: Revit not restarted after DLL rebuild.

**Fix**: Fully close and restart Revit (not just the document).

### Connection Refused

**Error**: `Failed to connect to localhost port 3000`

**Cause**: Server not running.

**Fix**:
```cmd
start_express.bat
```

## Performance

| Model Size | Families | Quick Mode | Detailed Mode |
|------------|----------|------------|---------------|
| Small | 1-50 | 5-10 sec | 10-30 sec |
| Medium | 50-200 | 10-20 sec | 30-90 sec |
| Large | 200-500 | 20-40 sec | 90-180 sec |
| Huge | 500+ | 40-80 sec | 3-10 min |

**Note**: Times are approximate and depend on hardware and model complexity.

## Comparison with v1.0

### When to Use Express Server (v2.0)

✅ Frequent grading operations (server stays running)  
✅ Need custom parameters per request  
✅ Integration with web apps or Copilot Actions  
✅ Large models requiring longer timeouts  
✅ Need health monitoring and logging  

### When to Use Batch Script (v1.0)

✅ One-off grading tasks  
✅ Simple Power Automate flows with fixed parameters  
✅ No Node.js dependencies allowed  
✅ Minimal setup required  

### Hybrid Approach (Recommended)

Use **run_grade.bat v2.0** which automatically tries:
1. Express server (if running)
2. Direct MCP call (fallback)

Best of both worlds!

## Development

### Run in Development Mode (auto-restart)

```cmd
npm run dev
```

Requires `nodemon` (included in dev dependencies).

### Create Test Script

```javascript
// test-express.js
const axios = require('axios');

async function test() {
  try {
    // Health check
    const health = await axios.get('http://localhost:3000/health');
    console.log('Health:', health.data);

    // Grade families
    const response = await axios.post('http://localhost:3000/api/grade-families', {
      category: 'Doors',
      gradeType: 'quick',
      includeTypes: true
    }, {
      timeout: 120000 // 2 minutes
    });

    console.log('Grading result:', response.data);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

test();
```

Run: `node test-express.js`

## Deployment Options

### Option 1: Local Server (Current)

**Pros**:
- Direct access to Revit on local machine
- No network configuration needed
- Fast response times

**Cons**:
- Only accessible from local machine
- Requires Revit to be running

### Option 2: Network Server

Bind to network interface for remote access:

Edit `express-server.js`:
```javascript
app.listen(PORT, '0.0.0.0', () => { /* ... */ });
```

Then access from other machines: `http://YOUR_IP:3000`

### Option 3: With ngrok (Public Access)

For Copilot Studio cloud access:

```cmd
# Terminal 1: Start Express server
start_express.bat

# Terminal 2: Start ngrok
ngrok http 3000
```

Use ngrok HTTPS URL in Copilot Studio: `https://abc123.ngrok.io`

### Option 4: Windows Service

For production, run as Windows service using `node-windows`:

```cmd
npm install -g node-windows
npm link node-windows

# Create service script and install
```

## Security Considerations

**For Production**:

1. ✅ Add API key authentication
2. ✅ Use HTTPS (not HTTP)
3. ✅ Restrict CORS origins
4. ✅ Add rate limiting
5. ✅ Validate input parameters
6. ✅ Log all requests
7. ✅ Run as non-admin user

**Example API Key Middleware**:
```javascript
app.use((req, res, next) => {
  const apiKey = req.headers['x-api-key'];
  if (apiKey !== process.env.API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
});
```

## Monitoring

### View Server Logs

Logs are printed to console. Redirect to file:

```cmd
node express-server.js > server.log 2>&1
```

### Check Server Status

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:3000/health"
if ($response.status -eq "healthy") {
    Write-Host "✓ Server is healthy" -ForegroundColor Green
} else {
    Write-Host "✗ Server is unhealthy" -ForegroundColor Red
}
```

### Monitor Port

```powershell
netstat -ano | Select-String ":3000.*LISTENING"
```

## Change Log

### v2.0 (October 16, 2025)
- 🆕 Express HTTP server architecture
- 🆕 REST API with POST /api/grade-families
- 🆕 10-minute configurable timeout
- 🆕 Dynamic parameters via HTTP body
- 🆕 Health endpoint for monitoring
- 🆕 Comprehensive error handling and logging
- 🆕 CORS enabled for web clients
- ✅ Backward compatible with v1.0 batch script
- 🔄 Updated run_grade.bat with Express fallback

### v1.0 (October 15, 2025)
- Initial batch script solution
- Direct PowerShell piping to Node MCP
- Fixed parameters in test_grade.json
- 2-minute hardcoded timeout

## Support

- **Documentation**: This file
- **Batch Script Guide**: VERSION_1_BATCH_SCRIPT.md
- **Deployment**: DEPLOYMENT_GUIDE.md
- **Power Automate**: POWER_AUTOMATE_INTEGRATION.md
- **GitHub**: https://github.com/scotmos/revit-mcp-copilot-integration

---

**Status**: ✅ Ready for production use  
**Last Updated**: October 16, 2025  
**Next Version**: WebSocket support for real-time updates
