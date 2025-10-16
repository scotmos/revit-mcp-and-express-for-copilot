# Test Revit MCP via ngrok
# Make sure Revit is open with a document

Write-Host "Testing Revit MCP Server via ngrok..." -ForegroundColor Cyan
Write-Host "URL: https://6c701ec65166.ngrok-free.app" -ForegroundColor Yellow
Write-Host ""

# Test 1: Health Check
Write-Host "Test 1: Health Check" -ForegroundColor Green
try {
    $health = Invoke-RestMethod -Uri "https://6c701ec65166.ngrok-free.app/health" -Method GET
    Write-Host "✓ Health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "✗ Health check failed: $_" -ForegroundColor Red
    exit
}
Write-Host ""

# Test 2: Get Current View Info
Write-Host "Test 2: Get Current View Info" -ForegroundColor Green
$body = @{
    jsonrpc = "2.0"
    method = "tools/call"
    params = @{
        name = "get_current_view_info"
        arguments = @{}
    }
    id = "test_view"
} | ConvertTo-Json -Depth 10

try {
    $result = Invoke-RestMethod -Uri "https://6c701ec65166.ngrok-free.app/mcp" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    if ($result.error) {
        Write-Host "✗ Error: $($result.error.message)" -ForegroundColor Red
    } else {
        Write-Host "✓ View Info Retrieved:" -ForegroundColor Green
        Write-Host "  $($result | ConvertTo-Json -Depth 5)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 3: Get Elements in Current View (Walls only)
Write-Host "Test 3: Get Walls in Current View" -ForegroundColor Green
$body = @{
    jsonrpc = "2.0"
    method = "tools/call"
    params = @{
        name = "get_current_view_elements"
        arguments = @{
            modelCategoryList = @("OST_Walls")
            limit = 5
        }
    }
    id = "test_walls"
} | ConvertTo-Json -Depth 10

try {
    $result = Invoke-RestMethod -Uri "https://6c701ec65166.ngrok-free.app/mcp" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    if ($result.error) {
        Write-Host "✗ Error: $($result.error.message)" -ForegroundColor Red
    } else {
        Write-Host "✓ Walls Retrieved:" -ForegroundColor Green
        Write-Host "  $($result | ConvertTo-Json -Depth 5)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 4: Get Available Family Types
Write-Host "Test 4: Get Available Family Types" -ForegroundColor Green
$body = @{
    jsonrpc = "2.0"
    method = "tools/call"
    params = @{
        name = "get_available_family_types"
        arguments = @{
            limit = 3
        }
    }
    id = "test_families"
} | ConvertTo-Json -Depth 10

try {
    $result = Invoke-RestMethod -Uri "https://6c701ec65166.ngrok-free.app/mcp" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    if ($result.error) {
        Write-Host "✗ Error: $($result.error.message)" -ForegroundColor Red
    } else {
        Write-Host "✓ Family Types Retrieved:" -ForegroundColor Green
        Write-Host "  $($result | ConvertTo-Json -Depth 5)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "Tests Complete!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Go to https://make.powerautomate.com" -ForegroundColor White
Write-Host "2. Create a Custom Connector" -ForegroundColor White
Write-Host "3. Use host: 6c701ec65166.ngrok-free.app" -ForegroundColor White
Write-Host "4. Follow COPILOT_STUDIO_SETUP.md for detailed instructions" -ForegroundColor White
