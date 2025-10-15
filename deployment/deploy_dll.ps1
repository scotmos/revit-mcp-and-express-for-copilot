# Deploy the RevitMCPCommandSet DLL with bulk grading functionality
# IMPORTANT: Close Revit before running this script!

$ErrorActionPreference = "Stop"

Write-Host "Deploying RevitMCPCommandSet.dll with grade_all_families_by_category..." -ForegroundColor Cyan

# Source directory (our build output with the new code)
$sourceDir = "C:\Users\ScottM\source\repos\MCP\revit-mcp-commandset\revit-mcp-commandset\bin\Debug R24"

# Destination directories
$dest1 = "C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Commands\2024"
$dest2 = "C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Commands\RevitMCPCommandSet\2024"

# Check if Revit is running
$revitProcess = Get-Process -Name "Revit" -ErrorAction SilentlyContinue
if ($revitProcess) {
    Write-Host "⚠ WARNING: Revit is currently running!" -ForegroundColor Red
    Write-Host "Please close Revit before deploying the DLL." -ForegroundColor Yellow
    Write-Host "Press Enter after closing Revit, or Ctrl+C to cancel..."
    Read-Host
}

# Verify source DLL exists and has the right size
$sourceDll = Join-Path $sourceDir "RevitMCPCommandSet.dll"
if (-not (Test-Path $sourceDll)) {
    Write-Host "✗ Source DLL not found: $sourceDll" -ForegroundColor Red
    exit 1
}

$dllInfo = Get-Item $sourceDll
Write-Host "Source DLL: $($dllInfo.Length) bytes, modified $($dllInfo.LastWriteTime)" -ForegroundColor Gray

if ($dllInfo.Length -ne 259584) {
    Write-Host "⚠ WARNING: DLL size is $($dllInfo.Length) bytes, expected 259584 bytes" -ForegroundColor Yellow
    Write-Host "This might not be the version with the bulk grading code!" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit 1
    }
}

# Create destination directories if they don't exist
@($dest1, $dest2) | ForEach-Object {
    if (-not (Test-Path $_)) {
        Write-Host "Creating directory: $_" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# Copy DLL and dependencies to both locations
Write-Host "`nDeploying to destination 1: $dest1" -ForegroundColor Cyan
Copy-Item (Join-Path $sourceDir "RevitMCPCommandSet.dll") -Destination $dest1 -Force
Copy-Item (Join-Path $sourceDir "RevitMCPCommandSet.pdb") -Destination $dest1 -Force
Copy-Item (Join-Path $sourceDir "RevitMCPSDK.dll") -Destination $dest1 -Force
Write-Host "✓ Deployed to destination 1" -ForegroundColor Green

Write-Host "`nDeploying to destination 2: $dest2" -ForegroundColor Cyan
Copy-Item (Join-Path $sourceDir "RevitMCPCommandSet.dll") -Destination $dest2 -Force
Copy-Item (Join-Path $sourceDir "RevitMCPCommandSet.pdb") -Destination $dest2 -Force
Copy-Item (Join-Path $sourceDir "RevitMCPSDK.dll") -Destination $dest2 -Force
Write-Host "✓ Deployed to destination 2" -ForegroundColor Green

# Verify deployment
Write-Host "`nVerifying deployment..." -ForegroundColor Cyan
$deployed1 = Get-Item (Join-Path $dest1 "RevitMCPCommandSet.dll")
$deployed2 = Get-Item (Join-Path $dest2 "RevitMCPCommandSet.dll")

Write-Host "Destination 1: $($deployed1.Length) bytes, modified $($deployed1.LastWriteTime)" -ForegroundColor Gray
Write-Host "Destination 2: $($deployed2.Length) bytes, modified $($deployed2.LastWriteTime)" -ForegroundColor Gray

if ($deployed1.Length -eq $dllInfo.Length -and $deployed2.Length -eq $dllInfo.Length) {
    Write-Host "`n✓ Deployment successful!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Start Revit 2024" -ForegroundColor White
    Write-Host "2. Open the SnowdonTowers project" -ForegroundColor White
    Write-Host "3. Turn the MCP switch ON" -ForegroundColor White
    Write-Host "4. Run the test script: .\test_grade_command.ps1" -ForegroundColor White
} else {
    Write-Host "`n⚠ Warning: Deployed DLL sizes don't match source!" -ForegroundColor Yellow
}
