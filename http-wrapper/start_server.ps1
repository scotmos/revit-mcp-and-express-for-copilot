# Start Revit MCP REST API Server
# Run this script to start the Flask server in a dedicated PowerShell window

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Revit MCP REST API Server Starter" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Navigate to script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
cd $ScriptDir

# Check if port 5000 is already in use
Write-Host "[1/4] Checking port 5000..." -ForegroundColor Yellow
$port5000 = netstat -ano | Select-String ":5000.*LISTENING"

if ($port5000) {
    Write-Host "⚠️  Port 5000 is already in use!" -ForegroundColor Red
    $pidMatch = $port5000 -match '\s+(\d+)$'
    if ($pidMatch) {
        $pid = $Matches[1]
        Write-Host "    Process ID: $pid" -ForegroundColor Gray
        Write-Host "`nKill existing process? (Y/N): " -ForegroundColor Yellow -NoNewline
        $response = Read-Host
        
        if ($response -eq 'Y' -or $response -eq 'y') {
            Stop-Process -Id $pid -Force
            Write-Host "✓ Killed process $pid" -ForegroundColor Green
            Start-Sleep -Seconds 2
        } else {
            Write-Host "Exiting. Please manually stop the process on port 5000." -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "✓ Port 5000 is available" -ForegroundColor Green
}

# Check if Python is installed
Write-Host "`n[2/4] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found! Please install Python 3.12+" -ForegroundColor Red
    exit 1
}

# Check if required packages are installed
Write-Host "`n[3/4] Checking dependencies..." -ForegroundColor Yellow
try {
    $packages = pip list 2>$null | Select-String -Pattern "flask|flask-cors"
    if ($packages.Count -ge 2) {
        Write-Host "✓ Flask and Flask-CORS are installed" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Missing packages. Installing..." -ForegroundColor Yellow
        pip install flask flask-cors
    }
} catch {
    Write-Host "⚠️  Could not verify packages. Attempting to install..." -ForegroundColor Yellow
    pip install flask flask-cors
}

# Start server in dedicated window
Write-Host "`n[4/4] Starting server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd '$ScriptDir'; Write-Host ''; Write-Host '========================================' -ForegroundColor Cyan; Write-Host '  Revit MCP REST API Server' -ForegroundColor Cyan; Write-Host '========================================' -ForegroundColor Cyan; Write-Host ''; python simple_rest_api.py"

Write-Host "✓ Server starting in new window..." -ForegroundColor Green
Write-Host "`n⏳ Waiting 6 seconds for server to initialize..." -ForegroundColor Gray

# Wait for server to start
Start-Sleep -Seconds 6

# Test health endpoint
Write-Host "`n[TEST] Checking server health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/health" -TimeoutSec 5
    Write-Host "✅ Server is healthy!" -ForegroundColor Green
    Write-Host "   Status: $($health.status)" -ForegroundColor Gray
    Write-Host "   Service: $($health.service)" -ForegroundColor Gray
} catch {
    Write-Host "⚠️  Health check failed: $_" -ForegroundColor Yellow
    Write-Host "   Server may still be starting. Check the new PowerShell window." -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Server Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n📍 Endpoints:" -ForegroundColor Yellow
Write-Host "   Local:  http://localhost:5000" -ForegroundColor White
Write-Host "   Health: http://localhost:5000/health" -ForegroundColor White
Write-Host "   Grade:  http://localhost:5000/api/tools/grade_all_families_by_category" -ForegroundColor White
Write-Host "`n📖 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Start ngrok:  .\start_ngrok.ps1" -ForegroundColor White
Write-Host "   2. Configure Copilot Studio with ngrok URL" -ForegroundColor White
Write-Host "   3. See DEPLOYMENT_GUIDE.md for details`n" -ForegroundColor White
