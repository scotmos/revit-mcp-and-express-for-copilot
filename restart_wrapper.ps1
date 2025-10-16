# Stop old Python processes
Write-Host "Stopping old Python processes..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -notmatch "Visual Studio Code"
} | Stop-Process -Force

Start-Sleep -Seconds 2

# Start new wrapper
Write-Host "Starting pooled HTTP wrapper..." -ForegroundColor Green
cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http
python pooled_wrapper.py

# This will block - if you want to run in background, use:
# Start-Process python -ArgumentList "pooled_wrapper.py" -WindowStyle Normal
