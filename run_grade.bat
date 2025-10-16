@echo off
REM =============================================================================
REM Revit Family Grading - Power Automate Compatible Script
REM Version 2.0 - Express Server with Direct MCP Fallback
REM =============================================================================
REM
REM This script tries two methods:
REM   1. HTTP POST to Express server (if running) - PREFERRED
REM   2. Direct Node MCP call via PowerShell - FALLBACK
REM
REM Usage from Power Automate:
REM   Action: "Run DOS command"
REM   Command: C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http\run_grade.bat
REM   Working folder: C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http
REM   Timeout: 600 seconds
REM
REM =============================================================================

cd /d C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http

echo.
echo ========================================
echo   Revit Family Grading Tool v2.0
echo ========================================
echo.

REM ---------------------------------------------------------------------------
REM METHOD 1: Try Express Server (HTTP)
REM ---------------------------------------------------------------------------

echo [1/2] Checking Express server...

REM Test if server is running
curl -s -o NUL -w "%%{http_code}" http://localhost:3000/health > %TEMP%\health_check.txt 2>NUL
set /p HEALTH_CODE=<%TEMP%\health_check.txt
del %TEMP%\health_check.txt 2>NUL

if "%HEALTH_CODE%"=="200" (
    echo   Express server is RUNNING
    echo.
    echo [2/2] Sending grading request via HTTP...
    
    REM Call Express server with curl
    curl -X POST http://localhost:3000/api/grade-families ^
         -H "Content-Type: application/json" ^
         -d "{\"category\":\"Doors\",\"gradeType\":\"quick\",\"includeTypes\":true}" ^
         2>NUL
    
    echo.
    echo ========================================
    echo   Grading Complete (Express Server)
    echo ========================================
    exit /b 0
)

REM ---------------------------------------------------------------------------
REM METHOD 2: Fallback to Direct Node MCP Call
REM ---------------------------------------------------------------------------

echo   Express server NOT running
echo   Falling back to direct MCP call...
echo.
echo [2/2] Calling Node MCP directly via PowerShell...

powershell.exe -NoProfile -Command "Get-Content 'test_grade.json' | node 'C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js'; exit"

echo.
echo ========================================
echo   Grading Complete (Direct MCP)
echo ========================================

exit /b 0
