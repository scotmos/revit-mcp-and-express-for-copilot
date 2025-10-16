# Revit MCP + Express Server for Copilot Studio

Complete solution for integrating Revit with Microsoft Copilot Studio using Model Context Protocol (MCP) and Express.js HTTP server.

## 🎯 What This Does

Enables **natural language BIM automation** in Revit through Microsoft Copilot:
- "Grade all doors in the project" → Generates quality report in seconds
- "Create a wall from point A to B" → Draws wall in Revit
- "Color all windows red" → Changes element appearance
- And much more...

## 📦 Complete Solution Includes

### 1. **Revit MCP Plugin** (`revit-mcp-plugin/`)
- C# Revit API plugin
- HTTP server on port 8080
- Handles MCP commands from Node.js
- Commands: grading, creation, modification, deletion, etc.

### 2. **MCP Server** (`revit-mcp/`)
- Node.js/TypeScript Model Context Protocol server
- Translates MCP calls to Revit HTTP commands
- Built with `@modelcontextprotocol/sdk`

### 3. **Express HTTP Server** (`express-server.js`)
- Production-ready HTTP API on port 3000
- Fast response times (~400ms)
- 10-minute timeout for large models
- Backward compatible with Flask endpoints
- **This is what Copilot Studio calls**

### 4. **Command Set** (`revit-mcp-commandset/`)
- Additional Revit commands
- JSON configuration
- Extensible command system

### 5. **Documentation** (Multiple guides)
- Copilot Studio setup
- Power Automate integration
- Deployment guides
- API reference

## 🚀 Quick Start

### Prerequisites
- **Revit 2023+** with plugin installed
- **Node.js 18+** 
- **ngrok** for tunneling (free tier works)
- **Microsoft Copilot Studio** account

### Installation

1. **Install Revit Plugin**
   ```
   Copy revit-mcp-plugin/bin/Release/*.dll to:
   C:\ProgramData\Autodesk\Revit\Addins\2024\
   ```

2. **Start Revit & Enable MCP**
   - Open Revit
   - Go to Add-ins tab → External Tools
   - Toggle "MCP Switch" to ON (green)

3. **Install Node Dependencies**
   ```bash
   cd mcp-wrapper-http
   npm install
   ```

4. **Start Express Server**
   ```bash
   node express-server.js
   # Or use: start_express.bat
   ```

5. **Start ngrok Tunnel**
   ```bash
   ngrok http 3000
   # Note the HTTPS URL (e.g., https://xxxx.ngrok-free.app)
   ```

6. **Configure Copilot Studio**
   - Create custom connector
   - Host: `xxxx.ngrok-free.app`
   - Base URL: `/`
   - Add action: POST `/api/grade-families`
   - Body: `{ category, gradeType, includeTypes }`

## 📚 Architecture

```
User → Copilot Studio → ngrok → Express Server → MCP Server → Revit Plugin → Revit API
                         (3000)    (stdin/stdout)    (HTTP 8080)
```

### Communication Flow

1. **User asks Copilot**: "Grade all doors"
2. **Copilot Studio** calls connector action via ngrok
3. **Express Server** receives HTTP POST on port 3000
4. **Express spawns MCP subprocess** with JSON-RPC request
5. **MCP Server** sends HTTP request to Revit plugin (port 8080)
6. **Revit Plugin** executes command using Revit API
7. **Results flow back** through the chain
8. **User sees**: "Graded 142 doors, average score 96/100, CSV saved..."

## 🔧 Key Files

### Express Server
- **`express-server.js`** - Main HTTP server (12KB, 415 lines)
- **`package.json`** - Node dependencies
- **`start_express.bat`** - Easy startup script

### Testing & Utilities
- **`run_grade.bat`** - Smart wrapper (tries Express, falls back to direct MCP)
- **`test_grade.json`** - Sample grading request
- **`start_ngrok.ps1`** - ngrok startup automation

### Documentation
- **`EXPRESS_SERVER_COMPLETE.md`** - Complete Express server guide (17KB)
- **`VERSION_2_EXPRESS_SERVER.md`** - API reference
- **`COPILOT_STUDIO_GUIDE.md`** - Copilot setup instructions
- **`DEPLOYMENT_GUIDE.md`** - Production deployment

## 🎯 API Endpoints

### Health Check
```http
GET /health
```
Returns: `{ "status": "healthy", "version": "2.0.1" }`

### Grade Families (Primary)
```http
POST /api/grade-families
Content-Type: application/json

{
  "category": "Doors",
  "gradeType": "quick",
  "includeTypes": true
}
```

### Grade Families (Backward Compatible)
```http
POST /api/tools/grade_all_families_by_category
```
Same body as above - for existing Flask-based connectors

### Response Format
```json
{
  "success": true,
  "totalElements": 142,
  "avgScore": 96,
  "csvFilePath": "C:\\...\\RevitFamilyGrades_xxx.csv",
  "gradeDistribution": { "A": 132, "B": 8, "C": 2, "D": 0, "F": 0 },
  "categories": [["Doors", 142, 96]],
  "timestamp": "2025-10-16 18:05:09",
  "revitFileName": "SnowdonTowers.rvt",
  "duration": 426
}
```

## 🔥 Performance

| Metric | Value |
|--------|-------|
| Response Time (local) | ~400ms |
| Response Time (ngrok) | ~400ms |
| Timeout | 600 seconds (10 min) |
| Concurrent Requests | 1 (sequential) |
| Subprocess Startup | ~50ms |
| Revit API Call | ~300ms |

## 🐛 Troubleshooting

### "404 Not Found" from Copilot
- **Check**: Connector Base URL should be `/` or blank
- **Check**: Action path should be `/api/grade-families` or `/api/tools/grade_all_families_by_category`
- **Solution**: Delete and recreate connector action

### "Unable to connect to remote server"
- **Check**: Express server running? `Get-Process node`
- **Check**: Port 3000 available? `netstat -ano | Select-String ":3000"`
- **Solution**: Restart server with `start_express.bat`

### "Request timeout"
- **Check**: Revit open and responsive?
- **Check**: MCP switch ON (green) in Revit plugin?
- **Check**: No hung Node processes? `Get-Process node | Where-Object {$_.CPU -gt 10}`
- **Solution**: Kill hung processes, restart server

### "Invalid JSON response"
- **Check**: Express server logs for parsing errors
- **Solution**: Already handled by smart parsing in v2.0.1

## 📂 Project Structure

```
revit-mcp-and-express-for-copilot/
├── express-server.js              # Express HTTP server (MAIN)
├── package.json                   # Node dependencies
├── start_express.bat              # Easy startup
├── run_grade.bat                  # Smart test wrapper
├── test_grade.json                # Sample request
├── EXPRESS_SERVER_COMPLETE.md     # Complete guide
│
├── revit-mcp/                     # MCP Server (Node.js)
│   ├── src/
│   │   ├── index.ts               # MCP server entry point
│   │   ├── tools/                 # MCP tool implementations
│   │   └── utils/                 # Connection manager, socket client
│   ├── build/                     # Compiled JavaScript
│   └── package.json
│
├── revit-mcp-plugin/              # Revit Plugin (C#)
│   ├── Commands/                  # All Revit API commands
│   │   ├── GradeAllFamiliesByCategoryCommand.cs
│   │   ├── CreateLineElementCommand.cs
│   │   └── ... (30+ commands)
│   ├── Core/                      # HTTP server, request handlers
│   ├── Utils/                     # Helpers, loggers
│   └── revit-mcp-plugin.csproj
│
├── revit-mcp-commandset/          # Additional command set
│   ├── Commands/
│   ├── Models/
│   └── command.json
│
├── docs/                          # Documentation
│   ├── COPILOT_STUDIO_GUIDE.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── ...
│
└── deployment/                    # Deployment scripts
    ├── start_ngrok.ps1
    └── ...
```

## 🔑 Key Features

### Express Server v2.0.1
✅ **Smart Subprocess Management** - Kills MCP process immediately after parsing response
✅ **Intelligent JSON Parsing** - Handles chunked stderr data from MCP server
✅ **Backward Compatible** - Supports old Flask endpoint paths
✅ **Fast Response Times** - ~400ms for typical requests
✅ **Long Timeout Support** - 600 seconds for large models
✅ **CORS Enabled** - Works with browser clients
✅ **Comprehensive Logging** - Duration tracking, error details
✅ **Production Ready** - Battle-tested with Copilot Studio

### Revit MCP Plugin
✅ **30+ Commands** - Grading, creation, modification, deletion, querying
✅ **HTTP Server** - Port 8080, handles JSON requests
✅ **Switch Control** - Enable/disable MCP from Revit UI
✅ **Error Handling** - Graceful failures with detailed messages
✅ **Logging** - Daily log files for debugging

### MCP Server
✅ **Stdio Transport** - Standard Model Context Protocol
✅ **Socket Connection** - Connects to Revit plugin via TCP
✅ **Tool Registration** - Auto-discovers available commands
✅ **Type Safety** - Written in TypeScript with Zod schemas

## 🌟 Use Cases

### Family Quality Grading
- Batch grade all families by category
- Generate CSV reports with recommendations
- Identify imported geometry (SAT, meshes)
- Track performance metrics (face count, solid count)

### Element Creation
- Create walls, doors, windows from coordinates
- Place point-based elements (columns, furniture)
- Draw line-based elements (pipes, ducts)
- Create surface-based elements (roofs, floors)

### Element Modification
- Change element properties
- Move/rotate/scale elements
- Update parameters
- Modify geometry

### Querying & Analysis
- Get current view elements
- Get selected elements
- Filter by category, type, parameters
- AI-powered element filtering

### Visual Feedback
- Color elements by criteria
- Highlight problematic families
- Show grading results visually

## 📄 License

MIT License - See LICENSE file

## 👥 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Submit pull request with clear description

## 📞 Support

- **Documentation**: See docs/ folder
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## 🔗 Related Projects

- [Model Context Protocol](https://github.com/modelcontextprotocol/specification)
- [Revit API Documentation](https://www.revitapidocs.com/)
- [Microsoft Copilot Studio](https://www.microsoft.com/en-us/microsoft-copilot/microsoft-copilot-studio)

## 📅 Version History

### v2.0.1 (2025-10-16) - Current
- ✅ Express Server with smart parsing
- ✅ Backward compatible endpoints
- ✅ Fast response times (~400ms)
- ✅ Copilot Studio integration tested
- ✅ Complete documentation

### v1.0.0 (2025-10-15)
- Initial Flask implementation
- Basic HTTP API
- 30-second timeout

## 🎓 Getting Started Tutorial

### 1. First Time Setup (15 minutes)
1. Install Revit plugin → See `revit-mcp-plugin/README.md`
2. Start Revit, enable MCP switch
3. Install Node.js dependencies → `npm install`
4. Start Express server → `start_express.bat`
5. Start ngrok → `ngrok http 3000`

### 2. Configure Copilot Studio (10 minutes)
1. Create custom connector → See `COPILOT_STUDIO_GUIDE.md`
2. Add action with ngrok URL
3. Test action in connector
4. Create Copilot agent
5. Add action to agent

### 3. Test Integration (5 minutes)
1. Open Copilot agent test pane
2. Ask: "Grade all doors"
3. Verify action executes
4. Check results in Copilot and Revit

### 4. Production Deployment (20 minutes)
1. Get permanent domain or persistent ngrok
2. Update connector with production URL
3. Add authentication if needed
4. Set up monitoring
5. Deploy → See `DEPLOYMENT_GUIDE.md`

**Total Time**: ~50 minutes from zero to production

## 🚨 Important Notes

### Security
- ngrok URLs are public - add authentication for production
- API keys recommended for production deployments
- Consider IP whitelisting for sensitive environments

### Revit Requirements
- Revit must be running for API to work
- MCP switch must be ON (green)
- One Revit instance per Express server

### Performance
- Sequential request processing (not concurrent)
- Large models may take longer to grade
- Consider batch processing for multiple projects

### Maintenance
- Update ngrok URL if it changes
- Monitor server logs for errors
- Restart Revit daily for best performance
- Clean up temp CSV files periodically

---

**Built with ❤️ for Revit BIM automation**

**Ready to automate your BIM workflows with AI? Let's go! 🚀**
