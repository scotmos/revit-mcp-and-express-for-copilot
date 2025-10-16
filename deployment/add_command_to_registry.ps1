# Add grade_all_families_by_category to commandRegistry.json

$ErrorActionPreference = "Stop"

$registryPath = "C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Commands\commandRegistry.json"

Write-Host "Adding grade_all_families_by_category to command registry..." -ForegroundColor Cyan

# Read the registry
$registry = Get-Content $registryPath -Raw | ConvertFrom-Json

# Check if command already exists
$existing = $registry.commands | Where-Object { $_.name -eq "grade_all_families_by_category" }

if ($existing) {
    Write-Host "Command already exists in registry!" -ForegroundColor Yellow
    Write-Host "Updating enabled status to true..." -ForegroundColor Yellow
    $existing.enabled = $true
} else {
    Write-Host "Adding new command to registry..." -ForegroundColor Yellow
    
    # Create the new command object
    $newCommand = @{
        name = "grade_all_families_by_category"
        className = "RevitMCPCommandSet.Commands.GradeAllFamiliesByCategoryCommand"
        assemblyName = "RevitMCPCommandSet"
        assemblyPath = "RevitMCPCommandSet\{VERSION}\RevitMCPCommandSet.dll"
        enabled = $true
    }
    
    # Add to commands array
    $registry.commands += $newCommand
}

# Save the updated registry
$registry | ConvertTo-Json -Depth 10 | Set-Content $registryPath -Encoding UTF8

Write-Host "✓ Command added successfully!" -ForegroundColor Green
Write-Host "`nCommand details:" -ForegroundColor Cyan
Write-Host "  Name: grade_all_families_by_category" -ForegroundColor White
Write-Host "  Class: RevitMCPCommandSet.Commands.GradeAllFamiliesByCategoryCommand" -ForegroundColor White
Write-Host "  Assembly: RevitMCPCommandSet.dll" -ForegroundColor White
Write-Host "  Enabled: true" -ForegroundColor White

Write-Host "`n⚠ IMPORTANT: Restart Revit for this change to take effect!" -ForegroundColor Yellow
