# Revit MCP Server - Deployment Guide

## Current Working Setup (October 15, 2025)

This guide documents the **proven, working configuration** for running the Revit MCP server with Copilot Studio integration.

---

## Architecture Overview

### Decoupled Approach (What Works!)

We use a **per-request subprocess model** that avoids the persistent subprocess issues:

```
Copilot Studio
    ↓ (HTTPS)
Azure API Management
    ↓ (HTTPS)
ngrok (Public Tunnel)
    ↓ (HTTP)
simple_rest_api.py (Flask Server on localhost:5000)
    ↓ (subprocess per request)
node build/index.js (MCP Server via stdin/stdout)
    ↓ (Socket on port 8080)
Revit Plugin (revit-mcp-plugin)
    ↓
Revit 2024
```

**Key Insight**: Each HTTP request spawns a fresh Node.js process that communicates via stdin/stdout piping, then terminates. This is the same approach that worked in our successful standalone tests.

---

## Components

### 1. Revit MCP Plugin
- **Location**: `C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\`
- **Port**: 8080 (Socket service)
- **Status**: Must be running with MCP switch ON
- **Commands Loaded**: 17 tools including `grade_all_families_by_category`

### 2. Node MCP Server
- **Location**: `C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js`
- **Invocation**: Run per-request via subprocess, NOT as persistent process
- **Input**: JSON-RPC via stdin
- **Output**: JSON-RPC via stdout

### 3. Flask REST API (simple_rest_api.py)
- **Location**: `C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http\simple_rest_api.py`
- **Port**: 5000 (HTTP)
- **Status**: Must run in dedicated PowerShell window
- **Endpoints**:
  - `GET /health` - Health check
  - `GET /api/tools/list` - List available tools
  - `POST /api/tools/grade_all_families_by_category` - Grade families

### 4. ngrok Tunnel
- **Purpose**: Exposes localhost:5000 to public internet
- **Free tier**: URL changes on restart (e.g., `https://94df9b778471.ngrok-free.app`)
- **Port**: Forwards to localhost:5000
- **Session**: 2-hour limit on free tier

### 5. Copilot Studio Custom Connector
- **Platform**: Microsoft Azure API Management
- **Timeout**: ~30 seconds (causes issues with detailed grading)
- **Workaround**: Use Power Automate for long-running operations

---

## Prerequisites

### Software Requirements
- **Autodesk Revit 2024** (with active document open)
- **Python 3.12+** (with pip)
- **Node.js** (any recent version)
- **ngrok** account (free tier OK for testing)
- **Copilot Studio** access (Microsoft 365 subscription)

### Python Packages
```powershell
cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http
pip install flask flask-cors
```

### ngrok Setup
1. Download: https://ngrok.com/download
2. Sign up: https://dashboard.ngrok.com/signup
3. Get auth token from dashboard
4. Authenticate:
```powershell
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

---

## Installation Steps

### Step 1: Verify Revit Plugin

```powershell
# Check if plugin DLL is deployed
Test-Path "C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\RevitMCPCommandSet.dll"

# Should return: True (and file size should be 259,584 bytes)
```

**Verify in Revit**:
1. Open Revit 2024
2. Load a project (e.g., SnowdonTowers.rvt)
3. Check if MCP switch shows "ON" (port 8080 listening)

### Step 2: Start ngrok Tunnel

```powershell
# Start ngrok in a dedicated PowerShell window
ngrok http 5000
```

**Note the public URL** (e.g., `https://94df9b778471.ngrok-free.app`). You'll need this for Copilot Studio configuration.

**Free tier limitations**:
- URL changes every time ngrok restarts
- 2-hour session limit
- Requires reconnecting after timeout

**Paid tier benefits** ($8/month):
- Static domain (no URL changes)
- No session limits
- Better for production

### Step 3: Start Flask REST API Server

**CRITICAL**: Must use dedicated PowerShell window (background processes exit immediately).

```powershell
# Navigate to project directory
cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http

# Start server in dedicated window
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http; python simple_rest_api.py"
```

**Verify server started**:
```powershell
# Should show server output in the new window
# Wait 5 seconds, then test health endpoint

Invoke-RestMethod -Uri "http://localhost:5000/health"
# Expected: {"status":"healthy","service":"Revit MCP REST API"}
```

### Step 4: Test via ngrok

```powershell
# Replace with your actual ngrok URL
Invoke-RestMethod -Uri "https://YOUR_NGROK_URL/health"
# Expected: Same health response
```

---

## Copilot Studio Configuration

### Create Custom Connector

1. Navigate to: https://copilotstudio.microsoft.com
2. Go to **Settings** → **Connectors** → **+ Add a connector**
3. Select **Create from blank**

**General Settings**:
- **Name**: `Revit MCP Tools`
- **Host**: `YOUR_NGROK_URL` (without `https://`, e.g., `94df9b778471.ngrok-free.app`)
- **Base URL**: `/`
- **Scheme**: `HTTPS`

### Add Action: GradeAllFamiliesByCategory

**Action Configuration**:
- **Summary**: `Grade All Families By Category`
- **Description**: Bulk grade family instances and export CSV report
- **Operation ID**: `grade_all_families_by_category`
- **URL**: `/api/tools/grade_all_families_by_category`
- **Method**: `POST`

**Request Body Schema**:
```json
{
  "type": "object",
  "properties": {
    "category": {
      "type": "string",
      "description": "Category to filter (Doors, Windows, Furniture, All)",
      "default": "All"
    },
    "gradeType": {
      "type": "string",
      "enum": ["quick", "detailed"],
      "description": "Quick (5 columns) or Detailed (17 columns)",
      "default": "detailed"
    },
    "includeTypes": {
      "type": "boolean",
      "description": "Include all type instances (true) or unique families only (false)",
      "default": true
    },
    "outputPath": {
      "type": "string",
      "description": "Optional custom CSV output path"
    }
  }
}
```

**Response Schema** (see `ADDING_BULK_GRADING_TO_COPILOT.md` for full schema)

---

## Testing

### Quick Test (Local)

```powershell
# Test health
curl http://localhost:5000/health

# Test grading (quick mode, 5-10 seconds)
$body = @{
    category = "Furniture"
    gradeType = "quick"
    includeTypes = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/tools/grade_all_families_by_category" `
  -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30
```

### Full Test (via ngrok)

```powershell
# Test detailed grading on Doors (30-60 seconds)
$body = @{
    category = "Doors"
    gradeType = "detailed"
    includeTypes = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://YOUR_NGROK_URL/api/tools/grade_all_families_by_category" `
  -Method POST -Body $body -ContentType "application/json" -TimeoutSec 120
```

**Expected Result**:
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

### Copilot Studio Test

1. In Copilot Studio, go to **Test** tab
2. Select your connector
3. Choose action: `GradeAllFamiliesByCategory`
4. Set parameters:
   - category: `"Doors"`
   - gradeType: `"quick"` (use quick first to avoid timeout)
   - includeTypes: `true`
5. Click **Test operation**

**Known Issue**: Detailed mode (30-60 sec) may timeout in Copilot Studio. See **Power Automate Integration** below.

---

## Troubleshooting

### Server Won't Start / Exits Immediately

**Symptom**: `python simple_rest_api.py` exits right away

**Cause**: PowerShell background process behavior

**Fix**: Use `Start-Process` with `-NoExit` (see Installation Step 3)

### 404 Not Found

**Check**:
1. Flask server running on port 5000: `netstat -ano | Select-String ":5000"`
2. ngrok forwarding to localhost:5000: Check ngrok dashboard (http://localhost:4040)
3. Copilot connector Base URL is `/` (not `/api/tools`)
4. Action URL is `/api/tools/grade_all_families_by_category`

### 500 Timeout in Copilot Studio

**Symptom**: Detailed grading returns "Request to the backend service timed out"

**Cause**: Detailed mode (30-60 sec) exceeds Azure API Management timeout (~30 sec)

**Solutions**:
1. **Use Power Automate** (RECOMMENDED) - See `POWER_AUTOMATE_INTEGRATION.md`
2. Use `gradeType: "quick"` - Completes in 5-10 seconds
3. Grade smaller categories - Furniture vs All

### ngrok URL Changed

**Symptom**: Copilot returns "endpoint offline" error

**Cause**: Free ngrok URLs change on restart

**Fix**:
1. Check new URL in ngrok dashboard or terminal
2. Update Copilot Studio connector **Host** field
3. Save and retest

**Prevention**: Upgrade to ngrok paid plan for static domains

### Port 5000 Already in Use

**Check**: `netstat -ano | Select-String ":5000"`

**Fix**: Kill process: `Stop-Process -Id [PID]`

**Alternative**: Change port in `simple_rest_api.py` (line ~189: `app.run(port=5001)`)

### "No valid response from MCP server"

**Check**:
1. Revit is running with document open
2. MCP switch is ON (port 8080 listening)
3. Category name is correct (case-insensitive but must match)
4. Check Revit logs: `C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Logs\`

---

## Known Limitations

### 1. Timeout on Detailed Mode
- **Issue**: Detailed grading takes 30-60 seconds for 100+ elements
- **Azure limit**: ~30 seconds
- **Impact**: Copilot Studio calls timeout with 500 error
- **Solution**: **Use Power Automate** (5+ minute timeouts, async processing)

### 2. ngrok Free Tier
- **Issue**: URL changes every time ngrok restarts
- **Impact**: Must update Copilot Studio connector after ngrok restart
- **Workaround**: Document URL in connector description, update as needed
- **Solution**: Upgrade to ngrok paid plan ($8/mo) for static domains

### 3. Dedicated PowerShell Window Required
- **Issue**: Background processes (`-isBackground:true`) exit in PowerShell
- **Impact**: Server stops if started as background task
- **Workaround**: Use `Start-Process -NoExit` to create dedicated window
- **Alternative**: Deploy to Azure VM or use Windows Service

### 4. Per-Request Process Overhead
- **Issue**: Each request spawns new Node.js process
- **Impact**: Adds ~500ms startup time per request
- **Benefit**: Avoids persistent subprocess crashes (reliable vs fast)
- **Mitigation**: Acceptable for Copilot Studio use case (human interaction)

---

## Power Automate Integration (Timeout Workaround)

For detailed grading (30-60 seconds), use Power Automate instead of direct Copilot Studio calls.

**See**: `POWER_AUTOMATE_INTEGRATION.md` for complete setup

**Benefits**:
- No timeout limits (configure up to 5+ minutes)
- Async processing (trigger and check later)
- Scheduled runs (daily quality reports)
- Better error handling and retry logic
- Email/Teams notifications on completion

**Quick Setup**:
1. Create Manual Trigger flow in Power Automate
2. Add action: Call your Revit MCP custom connector
3. Set timeout to 300 seconds (5 minutes)
4. Add condition to check success
5. Send email with CSV path and statistics

---

## Startup Scripts

### start_ngrok.ps1

```powershell
# Start ngrok tunnel on port 5000
Write-Host "Starting ngrok tunnel..." -ForegroundColor Green

if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "ngrok not found! Install from https://ngrok.com/download" -ForegroundColor Red
    exit 1
}

ngrok http 5000
```

### start_server.ps1

```powershell
# Start Revit MCP REST API Server
Write-Host "Starting Revit MCP REST API..." -ForegroundColor Green

# Check if port 5000 is already in use
$port5000 = netstat -ano | Select-String ":5000.*LISTENING"
if ($port5000) {
    Write-Host "Port 5000 already in use!" -ForegroundColor Red
    Write-Host "Kill existing process? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq 'Y') {
        $pid = ($port5000 -split '\s+')[-1]
        Stop-Process -Id $pid -Force
        Start-Sleep -Seconds 2
    } else {
        exit 1
    }
}

# Start server in dedicated window
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd $PSScriptRoot; python simple_rest_api.py"

Write-Host "Server starting in new window..." -ForegroundColor Green
Write-Host "Check http://localhost:5000/health after 5 seconds" -ForegroundColor Yellow

# Wait and test
Start-Sleep -Seconds 6
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/health"
    Write-Host "✓ Server is healthy: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "✗ Health check failed!" -ForegroundColor Red
}
```

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Replace ngrok with permanent solution (Azure VM, static ngrok domain)
- [ ] Add API key authentication to Flask server
- [ ] Add rate limiting (Flask-Limiter)
- [ ] Set up monitoring and logging (Application Insights)
- [ ] Configure Power Automate flows for long operations
- [ ] Create automated health checks
- [ ] Document URL update procedure for team
- [ ] Set up backup/failover strategy
- [ ] Test error handling and retry logic
- [ ] Create runbook for common issues

---

## Summary

This deployment uses a **proven decoupled architecture** where:
1. ✅ Each request spawns a fresh Node.js subprocess
2. ✅ JSON-RPC is piped via stdin/stdout
3. ✅ No persistent subprocess issues
4. ✅ Validated with successful tests (142 doors @ 96.4 avg)

**Key Files**:
- `simple_rest_api.py` - Flask server (WORKING)
- `grade_test.json` - Test file reference
- `POWER_AUTOMATE_INTEGRATION.md` - Timeout workaround

**Avoid**:
- `http_wrapper.py` - Persistent subprocess crashes
- `simple_wrapper.py` - Same crashes
- Background Python processes - Exit immediately

**For Help**:
- Revit logs: `C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Logs\`
- ngrok dashboard: http://localhost:4040
- This guide: `DEPLOYMENT_GUIDE.md`
- **Port**: 5000
- **Host**: 0.0.0.0 (listens on all interfaces for ngrok)
- **Approach**: Spawns `node build/index.js` per request using `subprocess.run()`

### 4. ngrok Tunnel
- **Purpose**: Exposes localhost:5000 to public internet for Copilot Studio
- **URL**: Changes on restart (free tier limitation)
- **Current**: `https://94df9b778471.ngrok-free.app` (example - will change)

---

## Step-by-Step Setup

### Prerequisites
- Revit 2024 running with MCP plugin installed
- Node.js installed
- Python 3.x installed
- Flask and flask-cors installed: `pip install flask flask-cors`
- ngrok installed and authenticated

### Step 1: Start Revit and Enable MCP
1. Open Revit 2024
2. Turn MCP switch **ON** in the plugin UI
3. Verify port 8080 is listening:
   ```powershell
   netstat -ano | Select-String ":8080"
   ```
4. Load the sample project (e.g., Snowdon Towers Sample Architectural)

### Step 2: Start Flask REST API
Open a **new PowerShell window** and run:
```powershell
cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python simple_rest_api.py"
```

This opens a dedicated window that stays open. You should see:
```
====================================
   Revit MCP Simple REST API
====================================

Endpoints:
  GET  /health
  GET  /api/tools/list
  POST /api/tools/grade_all_families_by_category

Server starting on http://0.0.0.0:5000
====================================
 * Running on http://127.0.0.1:5000
 * Running on http://10.1.55.178:5000
```

### Step 3: Start ngrok
In another PowerShell window:
```powershell
ngrok http 5000
```

**Important**: Copy the HTTPS forwarding URL (e.g., `https://abc123.ngrok-free.app`)

You should see:
```
Forwarding  https://94df9b778471.ngrok-free.app -> http://localhost:5000
```

### Step 4: Test the Setup Locally
```powershell
# Test health endpoint
Invoke-RestMethod -Uri "http://localhost:5000/health" | ConvertTo-Json

# Test through ngrok
Invoke-RestMethod -Uri "https://YOUR-NGROK-URL.ngrok-free.app/health" | ConvertTo-Json

# Test grading (quick mode)
$body = '{"category":"Doors","gradeType":"quick","includeTypes":true}'
Invoke-RestMethod -Uri "http://localhost:5000/api/tools/grade_all_families_by_category" -Method POST -Body $body -ContentType "application/json" | Select-Object success,totalElements,avgScore
```

---

## Copilot Studio Configuration

### Custom Connector Setup

1. **Create New Custom Connector**
   - Name: `Revit MCP Tools`
   - Description: `Connect to Revit MCP server to execute BIM automation commands`

2. **General Information**
   - Host: `YOUR-NGROK-URL.ngrok-free.app` (WITHOUT https://)
   - Base URL: `/` (just slash, or leave empty)
   - Scheme: HTTPS

3. **Security**
   - Authentication: None (or API Key if you add it later)

4. **Definition - Add Action**
   - **Summary**: `GradeAllFamiliesByCategory`
   - **Description**: `Grade all families by category`
   - **Operation ID**: `GradeAllFamiliesByCategory`
   
   - **Request**:
     - Verb: `POST`
     - URL: `https://YOUR-NGROK-URL.ngrok-free.app/api/tools/grade_all_families_by_category`
     - Headers: 
       - Content-Type: `application/json`
       - Accept: `JSON`
     
     - **Body** (schema):
       ```json
       {
         "type": "object",
         "properties": {
           "category": {
             "type": "string",
             "description": "Category to filter (e.g., Doors, Windows, Furniture) or 'All'"
           },
           "gradeType": {
             "type": "string",
             "enum": ["quick", "detailed"],
             "description": "Grading detail level"
           },
           "includeTypes": {
             "type": "boolean",
             "description": "Include all type instances (true) or unique families only (false)"
           },
           "outputPath": {
             "type": "string",
             "description": "Optional custom output path"
           }
         },
         "required": ["category", "gradeType", "includeTypes"]
       }
       ```
   
   - **Response** (schema):
     ```json
     {
       "type": "object",
       "properties": {
         "success": { "type": "boolean" },
         "totalElements": { "type": "integer" },
         "avgScore": { "type": "number" },
         "csvFilePath": { "type": "string" },
         "gradeDistribution": { "type": "object" },
         "categories": { "type": "array" },
         "timestamp": { "type": "string" },
         "revitFileName": { "type": "string" }
       }
     }
     ```

5. **Test the Connector**
   - Connection: Create new connection
   - Parameters:
     - category: `Furniture` (smaller dataset for testing)
     - gradeType: `quick` (faster)
     - includeTypes: `true`
   - Click "Test operation"

### Expected Test Results
- **Status**: 200 OK
- **Response**: 
  ```json
  {
    "success": true,
    "totalElements": 25,
    "avgScore": 92.5,
    "csvFilePath": "C:\\Users\\...\\RevitFamilyGrades_SnowdonTowers_20251015_123456.csv",
    ...
  }
  ```

---

## Known Issues & Workarounds

### Issue 1: Timeout with Detailed Mode on Large Categories

**Problem**: Azure API Management times out after ~30 seconds, but grading 142 doors in "detailed" mode takes 30-60 seconds.

**Workarounds**:

1. **Use Quick Mode** (5-10 seconds):
   ```json
   {"category":"Doors", "gradeType":"quick", "includeTypes":true}
   ```

2. **Test with Smaller Categories**:
   - Furniture (usually 10-30 elements)
   - Plumbing Fixtures (10-20 elements)
   - Instead of Doors (142 elements)

3. **Use Power Automate** (Recommended for Production):
   - Power Automate supports longer timeouts (5+ minutes)
   - Can schedule daily/weekly grading reports
   - Better error handling and retry logic
   - See "Power Automate Setup" section below

### Issue 2: ngrok URL Changes on Restart

**Problem**: Free ngrok tier generates new URL each restart.

**Workarounds**:

1. **Paid ngrok** ($8/month): Get static subdomain
2. **Azure VM**: Deploy permanently with static IP
3. **Update connector**: Manually update Host in Copilot Studio after each ngrok restart

### Issue 3: Flask Server Exits in Background

**Problem**: Running `python simple_rest_api.py` in background terminals causes it to exit.

**Solution**: Use `Start-Process` with `-NoExit`:
```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http; python simple_rest_api.py"
```

This opens a dedicated window that stays open.

---

## Power Automate Setup (Recommended for Production)

### Why Power Automate?
- **No timeout limits**: Flows can run for hours
- **Scheduled runs**: Daily/weekly grading reports
- **Better error handling**: Automatic retries
- **Integration**: Send emails, save to SharePoint, post to Teams

### Simple Flow Template

1. **Trigger**: Manual trigger or Recurrence (schedule)
2. **Action**: Use custom connector "GradeAllFamiliesByCategory"
   - category: `All` or specific category
   - gradeType: `detailed`
   - includeTypes: `true`
   - Timeout: 5 minutes
3. **Condition**: Check if `success` = true
4. **If Yes**:
   - Send email with avgScore and csvFilePath
   - Or save to SharePoint
   - Or post to Teams channel
5. **If No**:
   - Send error notification

### Example Flow for Daily Grading Report

```
Trigger: Recurrence (Daily at 9 AM)
  ↓
Action: GradeAllFamiliesByCategory
  - category: "All"
  - gradeType: "detailed"
  - includeTypes: true
  ↓
Parse JSON: Parse the response
  ↓
Condition: success = true?
  ↓ (Yes)
Send Email: "Daily Grading Report"
  - Subject: "Revit Quality Report - [revitFileName]"
  - Body: 
    Total Elements: [totalElements]
    Average Score: [avgScore]
    CSV: [csvFilePath]
    
    Grade Distribution:
    A: [gradeDistribution.A]
    B: [gradeDistribution.B]
    C: [gradeDistribution.C]
    D: [gradeDistribution.D]
    F: [gradeDistribution.F]
```

---

## Troubleshooting

### Server Won't Start

**Check Python is installed**:
```powershell
python --version
```

**Check Flask is installed**:
```powershell
pip list | Select-String flask
```

**Check port 5000 is not in use**:
```powershell
netstat -ano | Select-String ":5000"
```

### Revit Not Responding

**Check MCP switch is ON**:
- Look for the MCP toggle in Revit UI

**Check port 8080**:
```powershell
netstat -ano | Select-String ":8080"
```

**Check Revit logs**:
- Location: `C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Logs\`

### ngrok Connection Issues

**Check ngrok is running**:
```powershell
Get-Process ngrok
```

**Test ngrok dashboard**:
- Visit: http://localhost:4040
- Shows active tunnels and recent requests

**Check ngrok authentication**:
```powershell
ngrok config check
```

### API Returns 404

**Verify endpoint path**:
- Correct: `/api/tools/grade_all_families_by_category`
- Wrong: `/api/tools/api/tools/grade_all_families_by_category`

**Check Base URL in connector**:
- Should be `/` or empty
- NOT `/api/tools`

---

## File Locations

### Source Code
```
C:\Users\ScottM\source\repos\MCP\
├── mcp-wrapper-http\
│   ├── simple_rest_api.py          ← Flask REST API (WORKING)
│   ├── simple_wrapper.py           ← Old persistent wrapper (DON'T USE)
│   ├── http_wrapper.py             ← Old complex wrapper (DON'T USE)
│   └── requirements.txt
├── revit-mcp\
│   ├── build\
│   │   └── index.js                ← Compiled MCP server
│   └── src\
│       └── tools\
│           └── grade_all_families_by_category.ts
└── revit-mcp-commandset\
    └── Commands\
        └── GradeAllFamiliesByCategoryCommand.cs
```

### Deployed DLL
```
C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\
├── Commands\
│   └── RevitMCPCommandSet\
│       └── 2024\
│           └── RevitMCPCommandSet.dll  ← 259,584 bytes
└── Commands\
    └── commandRegistry.json           ← Command registration
```

### Generated CSV Files
```
C:\Users\ScottM\AppData\Local\Temp\[GUID]\
└── RevitFamilyGrades_[ProjectName]_[Timestamp].csv
```

---

## API Reference

### Endpoints

#### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "Revit MCP REST API"
}
```

#### GET /api/tools/list
List available tools.

**Response**:
```json
{
  "tools": [
    {
      "name": "grade_all_families_by_category",
      "description": "Grade all family instances by category and export to CSV",
      "endpoint": "/api/tools/grade_all_families_by_category"
    }
  ]
}
```

#### POST /api/tools/grade_all_families_by_category
Grade all families in the open Revit project by category.

**Request Body**:
```json
{
  "category": "Doors",           // Category name or "All"
  "gradeType": "detailed",       // "quick" or "detailed"
  "includeTypes": true,          // Include all type instances
  "outputPath": ""               // Optional custom path
}
```

**Response** (Success):
```json
{
  "success": true,
  "totalElements": 142,
  "avgScore": 96.4,
  "csvFilePath": "C:\\Users\\ScottM\\AppData\\Local\\Temp\\...\\RevitFamilyGrades_SnowdonTowers_20251015_122351.csv",
  "gradeDistribution": {
    "A": 132,
    "B": 0,
    "C": 0,
    "D": 10,
    "F": 0,
    "ERROR": 0,
    "avgScore": 96.4
  },
  "categories": ["Doors"],
  "timestamp": "2025-10-15T12:23:51",
  "revitFileName": "Snowdon Towers Sample Architectural"
}
```

**Response** (Error):
```json
{
  "success": false,
  "error": "Error message here"
}
```

---

## Performance Guidelines

### Quick Mode
- **Speed**: 5-10 seconds for 100 elements
- **CSV Columns**: 5 (ElementId, FamilyName, TypeName, OverallGrade, OverallScore)
- **Use Case**: Fast quality checks, large datasets

### Detailed Mode
- **Speed**: 30-60 seconds for 100 elements
- **CSV Columns**: 17 (includes all criterion grades, face counts, import sources, recommendations)
- **Use Case**: In-depth analysis, optimization planning
- **Recommendation**: Use Power Automate for large datasets to avoid timeouts

### Category Sizes (Snowdon Towers Sample)
- Doors: 142 elements (~60 sec detailed)
- Windows: 106 elements (~45 sec detailed)
- Furniture: 10-30 elements (~10 sec detailed)
- Walls: 500+ elements (use quick mode or Power Automate)

---

## Next Steps

1. **Test with Quick Mode**: Verify Copilot Studio connector works with small datasets
2. **Set up Power Automate Flow**: For production use with detailed mode
3. **Consider Production Deployment**:
   - Azure VM with static IP (no ngrok needed)
   - Or ngrok paid plan ($8/mo) for static subdomain
4. **Add Authentication**: Secure the API with API keys
5. **Add Logging**: Track usage and errors
6. **Create Scheduled Reports**: Daily/weekly quality dashboards

---

## Support & Documentation

- **Main Documentation**: `ADDING_BULK_GRADING_TO_COPILOT.md`
- **Quickstart Guide**: `COPILOT_STUDIO_QUICKSTART.md`
- **This Guide**: `DEPLOYMENT_GUIDE.md`

---

**Last Updated**: October 15, 2025  
**Status**: ✅ Working with decoupled stdin/stdout approach  
**Tested On**: Revit 2024, Windows 11, Snowdon Towers Sample Project
