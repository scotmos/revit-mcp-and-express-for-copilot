@echo off
REM Simple wrapper to run MCP grading and exit
REM This forces the command to complete instead of hanging

cd /d C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http

REM Run the command and capture output
powershell.exe -NoProfile -Command "Get-Content 'test_grade.json' | node 'C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js'; exit"

exit /b 0
