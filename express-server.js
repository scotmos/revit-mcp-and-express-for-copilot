/**
 * Express HTTP Server for Revit MCP Grading
 * 
 * This server provides a simple HTTP API for grading Revit families.
 * It connects directly to the Revit plugin on port 8080 via TCP/WebSocket.
 * 
 * Advantages over batch script:
 * - Persistent server process (no startup overhead per request)
 * - Configurable timeouts (10+ minutes for large models)
 * - Standard HTTP API (compatible with curl, Power Automate, Copilot Actions)
 * - Better error handling and logging
 * - CORS enabled for web clients
 */

const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Path to Node MCP server
const MCP_SERVER_PATH = path.join('C:', 'Users', 'ScottM', 'source', 'repos', 'MCP', 'revit-mcp', 'build', 'index.js');

// Logging helper
function log(message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] [${level}] ${message}`);
}

/**
 * Call the MCP server with grading request
 * Uses subprocess approach like our proven batch script
 */
async function callMCPGrading(category, gradeType, includeTypes, outputPath = '') {
    return new Promise((resolve, reject) => {
        const timeout = 600000; // 10 minutes
        let timedOut = false;

        log(`Starting MCP grading: category=${category}, gradeType=${gradeType}`);

        // Create JSON-RPC messages (same as batch script)
        const initMessage = {
            jsonrpc: '2.0',
            method: 'initialize',
            params: {
                protocolVersion: '2024-11-05',
                capabilities: {},
                clientInfo: { name: 'express-server', version: '2.0.0' }
            },
            id: 1
        };

        const gradeMessage = {
            jsonrpc: '2.0',
            method: 'tools/call',
            params: {
                name: 'grade_all_families_by_category',
                arguments: {
                    category: category,
                    gradeType: gradeType,
                    includeTypes: includeTypes,
                    ...(outputPath && { outputPath })
                }
            },
            id: 2
        };

        const input = JSON.stringify(initMessage) + '\n' + JSON.stringify(gradeMessage) + '\n';

        // Spawn Node process
        const nodeProcess = spawn('node', [MCP_SERVER_PATH], {
            stdio: ['pipe', 'pipe', 'pipe']
        });

        let stdout = '';
        let stderr = '';

        // Set timeout
        const timer = setTimeout(() => {
            timedOut = true;
            nodeProcess.kill();
            reject(new Error(`Request timeout after ${timeout / 1000} seconds`));
        }, timeout);

        // Collect stdout
        nodeProcess.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        // Collect stderr
        nodeProcess.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        // Handle completion
        nodeProcess.on('close', (code) => {
            clearTimeout(timer);

            if (timedOut) return;

            if (code !== 0 && code !== null) {
                log(`MCP process exited with code ${code}`, 'ERROR');
                log(`STDERR: ${stderr}`, 'ERROR');
                return reject(new Error(`Process exited with code ${code}`));
            }

            try {
                // Parse output - look for the response with id=2
                const lines = stdout.split('\n').filter(line => line.trim());
                
                for (const line of lines) {
                    try {
                        const response = JSON.parse(line);
                        
                        if (response.id === 2) {
                            log('Successfully received grading response');
                            
                            // Handle both direct result and nested content structure
                            if (response.result) {
                                const result = response.result;
                                
                                // Check for nested content array
                                if (result.content && Array.isArray(result.content) && result.content.length > 0) {
                                    const content = result.content[0];
                                    if (content.text) {
                                        // Check if text starts with error indicator
                                        if (content.text.startsWith('❌') || content.text.includes('Failed to grade')) {
                                            return reject(new Error(content.text));
                                        }
                                        
                                        try {
                                            const data = JSON.parse(content.text);
                                            return resolve(data);
                                        } catch (e) {
                                            // If not JSON, treat as plain text error message
                                            log(`Content is not JSON: ${content.text.substring(0, 200)}`, 'WARN');
                                            return reject(new Error(content.text));
                                        }
                                    }
                                }
                                
                                // Direct result
                                return resolve(result);
                            }
                            
                            if (response.error) {
                                return reject(new Error(response.error.message || JSON.stringify(response.error)));
                            }
                        }
                    } catch (e) {
                        // Not valid JSON, skip
                        continue;
                    }
                }

                reject(new Error('No valid response found in output'));
            } catch (error) {
                log(`Error parsing output: ${error.message}`, 'ERROR');
                reject(error);
            }
        });

        // Handle process errors
        nodeProcess.on('error', (error) => {
            clearTimeout(timer);
            log(`Process error: ${error.message}`, 'ERROR');
            reject(error);
        });

        // Send input to stdin
        nodeProcess.stdin.write(input);
        nodeProcess.stdin.end();
    });
}

// ============================================================================
// API ENDPOINTS
// ============================================================================

/**
 * GET /health
 * Health check endpoint
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'Revit MCP Express Server',
        version: '2.0.0',
        timestamp: new Date().toISOString()
    });
});

/**
 * POST /api/grade-families
 * Grade all families by category
 * 
 * Body:
 * {
 *   "category": "Doors",        // Category name or "All"
 *   "gradeType": "detailed",    // "quick" or "detailed"
 *   "includeTypes": true,       // Include all type instances
 *   "outputPath": ""            // Optional custom CSV path
 * }
 * 
 * Response:
 * {
 *   "success": true,
 *   "totalElements": 142,
 *   "avgScore": 96.4,
 *   "csvFilePath": "C:\\Users\\...\\RevitFamilyGrades_....csv",
 *   "gradeDistribution": { "A": 132, "B": 0, ... },
 *   "categories": ["Doors"],
 *   "timestamp": "2025-10-16 15:23:45",
 *   "revitFileName": "SnowdonTowers.rvt"
 * }
 */
app.post('/api/grade-families', async (req, res) => {
    const startTime = Date.now();
    
    try {
        // Extract parameters with defaults
        const {
            category = 'All',
            gradeType = 'detailed',
            includeTypes = true,
            outputPath = ''
        } = req.body;

        log(`Received grading request: category=${category}, gradeType=${gradeType}, includeTypes=${includeTypes}`);

        // Validate inputs
        if (!['quick', 'detailed'].includes(gradeType)) {
            return res.status(400).json({
                success: false,
                error: 'gradeType must be "quick" or "detailed"'
            });
        }

        // Call MCP grading
        const result = await callMCPGrading(category, gradeType, includeTypes, outputPath);

        const duration = Date.now() - startTime;
        log(`Grading completed successfully in ${duration}ms: ${result.totalElements} elements, avg ${result.avgScore}`);

        // Return standardized response
        res.json({
            success: true,
            totalElements: result.totalElements || 0,
            avgScore: result.avgScore || 0,
            csvFilePath: result.csvFilePath || '',
            gradeDistribution: result.gradeDistribution || {},
            categories: result.categories || [category],
            timestamp: result.timestamp || new Date().toISOString(),
            revitFileName: result.revitFileName || '',
            duration: duration
        });

    } catch (error) {
        const duration = Date.now() - startTime;
        log(`Grading failed after ${duration}ms: ${error.message}`, 'ERROR');

        res.status(500).json({
            success: false,
            error: error.message,
            duration: duration
        });
    }
});

/**
 * GET /api/info
 * Get server information and usage examples
 */
app.get('/api/info', (req, res) => {
    res.json({
        name: 'Revit MCP Express Server',
        version: '2.0.0',
        description: 'HTTP API for grading Revit families',
        endpoints: {
            'GET /health': 'Health check',
            'POST /api/grade-families': 'Grade families by category',
            'GET /api/info': 'This endpoint'
        },
        examples: {
            'Quick grading': {
                method: 'POST',
                url: '/api/grade-families',
                body: {
                    category: 'Doors',
                    gradeType: 'quick',
                    includeTypes: true
                }
            },
            'Detailed grading': {
                method: 'POST',
                url: '/api/grade-families',
                body: {
                    category: 'All',
                    gradeType: 'detailed',
                    includeTypes: true
                }
            }
        },
        notes: [
            'Supports timeouts up to 10 minutes for large models',
            'Returns full JSON response with CSV file path',
            'Compatible with Power Automate and Copilot Actions',
            'CORS enabled for browser access'
        ]
    });
});

// ============================================================================
// START SERVER
// ============================================================================

app.listen(PORT, '0.0.0.0', () => {
    console.log('\n' + '='.repeat(70));
    console.log('  🚀 Revit MCP Express Server v2.0');
    console.log('='.repeat(70));
    console.log(`\n  📍 Server running on:`);
    console.log(`     Local:   http://localhost:${PORT}`);
    console.log(`     Network: http://0.0.0.0:${PORT}`);
    console.log(`\n  📚 Endpoints:`);
    console.log(`     GET  /health              - Health check`);
    console.log(`     GET  /api/info            - Server information`);
    console.log(`     POST /api/grade-families  - Grade families`);
    console.log(`\n  ⏱️  Timeout: 10 minutes (configurable)`);
    console.log(`  🔗 CORS: Enabled`);
    console.log(`  📝 Logs: Console output`);
    console.log('\n' + '='.repeat(70));
    console.log(`\n  ✨ Ready to accept requests!\n`);
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    log('Shutting down server...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    log('Shutting down server...');
    process.exit(0);
});
