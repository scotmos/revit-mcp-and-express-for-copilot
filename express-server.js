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
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Job storage for async operations
const jobs = new Map();

// Job statuses
const JobStatus = {
    PENDING: 'pending',
    PROCESSING: 'processing',
    COMPLETED: 'completed',
    FAILED: 'failed'
};

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
        let resolved = false;

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

        // Collect stderr and check for Revit response immediately
        nodeProcess.stderr.on('data', (data) => {
            stderr += data.toString();
            
            // Check if we have the complete "Response from Revit:" output
            // The JSON can be multi-line and nested, so we need to find the complete object
            const revitResponseStart = stderr.indexOf('Response from Revit: ');
            if (revitResponseStart !== -1 && !resolved) {
                const jsonStart = revitResponseStart + 'Response from Revit: '.length;
                const jsonStr = stderr.substring(jsonStart);
                
                // Try to parse - if successful, we have the complete JSON
                try {
                    const response = JSON.parse(jsonStr);
                    // If we successfully parsed, we got the complete response
                    resolved = true;
                    
                    log(`Parsed response structure: ${JSON.stringify(Object.keys(response))}`);
                    
                    if (response.success && response.data) {
                        log('Successfully parsed Revit response from stderr');
                        clearTimeout(timer);
                        nodeProcess.kill();
                        return resolve(response.data);
                    } else if (response.success) {
                        // Response is successful but data is at top level, not nested
                        log('Response successful with flat structure');
                        clearTimeout(timer);
                        nodeProcess.kill();
                        return resolve(response);
                    } else {
                        log('Revit returned unsuccessful response', 'ERROR');
                        clearTimeout(timer);
                        nodeProcess.kill();
                        return reject(new Error(response.error || 'Unknown error'));
                    }
                } catch (e) {
                    // JSON not complete yet, wait for more data
                    // Don't log this error - it's expected until we get the full JSON
                }
            }
        });

        // Handle completion
        nodeProcess.on('close', (code) => {
            if (resolved) return; // Already handled in stderr handler
            
            clearTimeout(timer);

            if (timedOut) return;

            if (code !== 0 && code !== null) {
                log(`MCP process exited with code ${code}`, 'ERROR');
                log(`STDERR: ${stderr}`, 'ERROR');
                return reject(new Error(`Process exited with code ${code}`));
            }

            try {
                // First, look for "Response from Revit:" in stderr (debug output)
                const revitResponseMatch = stderr.match(/Response from Revit: (\{[\s\S]*?\})\n/);
                if (revitResponseMatch) {
                    try {
                        const response = JSON.parse(revitResponseMatch[1]);
                        if (response.success && response.data) {
                            log('Successfully parsed Revit response from stderr');
                            // Kill the subprocess since we got what we need
                            clearTimeout(timer);
                            nodeProcess.kill();
                            // Return the actual data object
                            return resolve(response.data);
                        } else {
                            log('Revit returned unsuccessful response', 'ERROR');
                            clearTimeout(timer);
                            nodeProcess.kill();
                            return reject(new Error(response.error || 'Unknown error'));
                        }
                    } catch (e) {
                        log(`Failed to parse Revit response: ${e.message}`, 'ERROR');
                    }
                }
                
                // Fallback: Parse output - look for the response with id=2
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
        version: '2.1.0',
        timestamp: new Date().toISOString(),
        features: {
            sync: true,
            async: true
        }
    });
});

/**
 * POST /api/grade-families-async
 * Start async family grading job (RECOMMENDED FOR POWER PLATFORM)
 * Returns immediately with job ID for polling
 */
app.post('/api/grade-families-async', async (req, res) => {
    try {
        const {
            category = 'All',
            gradeType = 'detailed',
            includeTypes = true,
            outputPath = ''
        } = req.body;

        // Validate inputs
        if (!['quick', 'detailed'].includes(gradeType)) {
            return res.status(400).json({
                success: false,
                error: 'gradeType must be "quick" or "detailed"'
            });
        }

        // Generate job ID
        const jobId = crypto.randomBytes(16).toString('hex');
        
        // Create job record
        const job = {
            id: jobId,
            status: JobStatus.PENDING,
            category,
            gradeType,
            includeTypes,
            outputPath,
            createdAt: new Date().toISOString(),
            startedAt: null,
            completedAt: null,
            result: null,
            error: null
        };

        jobs.set(jobId, job);

        log(`Created async job ${jobId}: category=${category}, gradeType=${gradeType}`);

        // Start processing in background
        setImmediate(() => processAsyncJob(jobId));

        // Return job ID immediately
        res.json({
            success: true,
            jobId: jobId,
            status: JobStatus.PENDING,
            message: 'Job created successfully. Use GET /api/jobs/{jobId} to check status.',
            pollUrl: `/api/jobs/${jobId}`
        });

    } catch (error) {
        log(`Error creating async job: ${error.message}`, 'ERROR');
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/jobs/:jobId
 * Get job status and results
 */
app.get('/api/jobs/:jobId', (req, res) => {
    const jobId = req.params.jobId;
    const job = jobs.get(jobId);

    if (!job) {
        return res.status(404).json({
            success: false,
            error: 'Job not found'
        });
    }

    // Return different responses based on status
    if (job.status === JobStatus.COMPLETED) {
        return res.json({
            success: true,
            jobId: job.id,
            status: job.status,
            result: job.result,
            createdAt: job.createdAt,
            startedAt: job.startedAt,
            completedAt: job.completedAt,
            duration: new Date(job.completedAt) - new Date(job.startedAt)
        });
    } else if (job.status === JobStatus.FAILED) {
        return res.json({
            success: false,
            jobId: job.id,
            status: job.status,
            error: job.error,
            createdAt: job.createdAt,
            startedAt: job.startedAt,
            completedAt: job.completedAt
        });
    } else {
        // Still processing or pending
        return res.json({
            success: true,
            jobId: job.id,
            status: job.status,
            message: job.status === JobStatus.PROCESSING ? 'Job is currently processing' : 'Job is queued',
            createdAt: job.createdAt,
            startedAt: job.startedAt
        });
    }
});

/**
 * GET /api/jobs
 * List all jobs (with optional status filter)
 */
app.get('/api/jobs', (req, res) => {
    const { status, limit = 50 } = req.query;
    
    let jobsList = Array.from(jobs.values());
    
    // Filter by status if provided
    if (status) {
        jobsList = jobsList.filter(job => job.status === status);
    }
    
    // Sort by creation date (newest first)
    jobsList.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    
    // Limit results
    jobsList = jobsList.slice(0, parseInt(limit));
    
    res.json({
        success: true,
        total: jobs.size,
        filtered: jobsList.length,
        jobs: jobsList.map(job => ({
            jobId: job.id,
            status: job.status,
            category: job.category,
            gradeType: job.gradeType,
            createdAt: job.createdAt,
            completedAt: job.completedAt
        }))
    });
});

/**
 * DELETE /api/jobs/:jobId
 * Delete a job (cleanup)
 */
app.delete('/api/jobs/:jobId', (req, res) => {
    const jobId = req.params.jobId;
    const job = jobs.get(jobId);

    if (!job) {
        return res.status(404).json({
            success: false,
            error: 'Job not found'
        });
    }

    jobs.delete(jobId);
    log(`Deleted job ${jobId}`);

    res.json({
        success: true,
        message: 'Job deleted successfully'
    });
});

/**
 * Background job processor
 */
async function processAsyncJob(jobId) {
    const job = jobs.get(jobId);
    if (!job) return;

    try {
        job.status = JobStatus.PROCESSING;
        job.startedAt = new Date().toISOString();
        log(`Processing job ${jobId}: category=${job.category}`);

        // Call the grading function
        const result = await callMCPGrading(
            job.category,
            job.gradeType,
            job.includeTypes,
            job.outputPath
        );

        // Job completed successfully
        job.status = JobStatus.COMPLETED;
        job.completedAt = new Date().toISOString();
        job.result = result;
        
        log(`Job ${jobId} completed successfully: ${result.totalElements} elements, avg ${result.avgScore}`);

    } catch (error) {
        // Job failed
        job.status = JobStatus.FAILED;
        job.completedAt = new Date().toISOString();
        job.error = error.message;
        
        log(`Job ${jobId} failed: ${error.message}`, 'ERROR');
    }
}

/**
 * POST /api/grade-families-sync
 * Grade all families by category (SYNCHRONOUS)
 * WARNING: May timeout in Power Platform for large projects
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
app.post('/api/grade-families-sync', async (req, res) => {
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
 * POST /api/tools/grade_all_families_by_category
 * BACKWARD COMPATIBILITY: Old Flask endpoint
 * Redirects to new endpoint for compatibility with existing Copilot Studio connectors
 */
app.post('/api/tools/grade_all_families_by_category', async (req, res) => {
    log('Received request on old Flask endpoint - forwarding to new endpoint');
    
    const startTime = Date.now();
    
    try {
        // Extract parameters with defaults (same as new endpoint)
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
        version: '2.1.0',
        description: 'HTTP API for grading Revit families with async support',
        endpoints: {
            // Health
            'GET /health': 'Health check',
            
            // Grading endpoints (equal URL lengths)
            'POST /api/grade-families-sync': 'Grade families (synchronous - fast, may timeout)',
            'POST /api/grade-families-async': 'Grade families (asynchronous - safe, recommended)',
            
            // Async job management
            'GET /api/jobs/:jobId': 'Get job status and results',
            'GET /api/jobs': 'List all jobs (optional: ?status=completed&limit=50)',
            'DELETE /api/jobs/:jobId': 'Delete a completed job',
            
            // Information
            'GET /api/info': 'This endpoint'
        },
        examples: {
            'Synchronous grading (fast, may timeout)': {
                method: 'POST',
                url: '/api/grade-families-sync',
                body: {
                    category: 'Doors',
                    gradeType: 'quick',
                    includeTypes: true
                },
                note: 'Use for small projects (<4 min). Power Platform will timeout after 240 seconds.'
            },
            'Async grading (Power Platform safe) - RECOMMENDED': {
                step1: {
                    description: 'Start job',
                    method: 'POST',
                    url: '/api/grade-families-async',
                    body: {
                        category: 'All',
                        gradeType: 'detailed',
                        includeTypes: true
                    },
                    returns: {
                        success: true,
                        jobId: 'abc123...',
                        status: 'pending',
                        pollUrl: '/api/jobs/abc123...'
                    }
                },
                step2: {
                    description: 'Poll for results (every 5-10 seconds)',
                    method: 'GET',
                    url: '/api/jobs/abc123...',
                    returns_when_complete: {
                        success: true,
                        status: 'completed',
                        result: {
                            totalElements: 142,
                            avgScore: 96.4,
                            csvFilePath: 'C:\\Users\\...\\RevitFamilyGrades.csv'
                        }
                    }
                }
            }
        },
        notes: [
            'v2.1.0 adds async job pattern for Power Platform timeout workaround',
            'Synchronous endpoint: Use for small projects, returns results immediately',
            'Async endpoints: Use for large projects, poll for results',
            'Power Platform has 240-second (4 minute) timeout limit',
            'Async pattern ensures client never waits more than polling interval',
            'Job storage is in-memory (jobs lost on server restart)',
            'Compatible with Power Automate, Copilot Actions, and Custom Connectors',
            'CORS enabled for browser access'
        ],
        currentJobs: {
            total: jobs.size,
            pending: Array.from(jobs.values()).filter(j => j.status === JobStatus.PENDING).length,
            processing: Array.from(jobs.values()).filter(j => j.status === JobStatus.PROCESSING).length,
            completed: Array.from(jobs.values()).filter(j => j.status === JobStatus.COMPLETED).length,
            failed: Array.from(jobs.values()).filter(j => j.status === JobStatus.FAILED).length
        }
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
