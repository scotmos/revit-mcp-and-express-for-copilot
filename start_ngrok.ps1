# Start ngrok tunnel for Revit MCP REST API
# Prerequisites: ngrok must be installed and authenticated

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ngrok Tunnel Starter" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if ngrok is installed
Write-Host "[1/3] Checking ngrok installation..." -ForegroundColor Yellow
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "✗ ngrok not found!" -ForegroundColor Red
    Write-Host "`nInstallation steps:" -ForegroundColor Yellow
    Write-Host "1. Download: https://ngrok.com/download" -ForegroundColor White
    Write-Host "2. Extract to a folder in your PATH" -ForegroundColor White
    Write-Host "3. Sign up: https://dashboard.ngrok.com/signup" -ForegroundColor White
    Write-Host "4. Get your auth token from dashboard" -ForegroundColor White
    Write-Host "5. Run: ngrok config add-authtoken YOUR_TOKEN`n" -ForegroundColor White
    exit 1
} else {
    Write-Host "✓ ngrok found" -ForegroundColor Green
}

# Check if local server is running
Write-Host "`n[2/3] Checking local server..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/health" -TimeoutSec 3
    Write-Host "✓ Local server is running on port 5000" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Local server not responding!" -ForegroundColor Yellow
    Write-Host "   Please start the server first: .\start_server.ps1" -ForegroundColor Gray
    Write-Host "`nContinue anyway? (Y/N): " -ForegroundColor Yellow -NoNewline
    $response = Read-Host
    
    if ($response -ne 'Y' -and $response -ne 'y') {
        Write-Host "Exiting. Start server first, then run this script again." -ForegroundColor Red
        exit 1
    }
}

# Start ngrok
Write-Host "`n[3/3] Starting ngrok tunnel on port 5000..." -ForegroundColor Yellow
Write-Host "`n⚡ ngrok session starting..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

Write-Host "📝 IMPORTANT NOTES:" -ForegroundColor Yellow
Write-Host "   • ngrok FREE TIER: URL changes on restart" -ForegroundColor White
Write-Host "   • Session limit: 2 hours" -ForegroundColor White
Write-Host "   • Copy the HTTPS URL below" -ForegroundColor White
Write-Host "   • Update Copilot Studio connector with new URL" -ForegroundColor White
Write-Host "   • Web interface: http://localhost:4040" -ForegroundColor White
Write-Host "`n📖 For static domains: Upgrade to ngrok paid plan ($8/mo)" -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

# Start ngrok (this will block until Ctrl+C)
ngrok http 5000
