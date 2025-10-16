@echo off
REM =============================================================================
REM Start Express Server for Revit MCP Grading
REM Version 2.0
REM =============================================================================

echo.
echo ========================================
echo   Express Server Starter
echo ========================================
echo.

cd /d C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http

REM Check if Node.js is installed
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found!
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo [1/3] Node.js found: 
node --version

REM Check if node_modules exists
if not exist "node_modules\" (
    echo.
    echo [2/3] Installing dependencies...
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] npm install failed!
        pause
        exit /b 1
    )
) else (
    echo [2/3] Dependencies already installed
)

echo.
echo [3/3] Starting Express server on port 3000...
echo.
echo ========================================
echo   Server will start in this window
echo   Press Ctrl+C to stop
echo ========================================
echo.

REM Start the server
node express-server.js

pause
