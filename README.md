# Revit MCP Copilot Integration

> **Complete platform for AI-powered Revit automation using Microsoft Copilot Studio and Power Automate**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Revit 2024](https://img.shields.io/badge/Revit-2024-blue.svg)](https://www.autodesk.com/products/revit)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io)

## 🎯 Overview

This project provides a complete integration platform that connects **Autodesk Revit** with **Microsoft Copilot Studio** and **Power Automate**, enabling natural language automation of BIM workflows.

**What you can do:**
- Grade family geometry quality across entire projects
- Automate repetitive Revit tasks through conversational AI
- Schedule batch operations via Power Automate
- Export detailed analysis reports to CSV
- Create custom Revit commands accessible via chat

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Microsoft Cloud                          │
│  ┌─────────────────────┐      ┌────────────────────────┐   │
│  │  Copilot Studio     │      │   Power Automate       │   │
│  │  (Conversational)   │      │   (Scheduled Flows)    │   │
│  └──────────┬──────────┘      └───────────┬────────────┘   │
│             │                              │                │
│             └──────────┬───────────────────┘                │
│                        │ HTTPS                              │
└────────────────────────┼────────────────────────────────────┘
                         │
                    ┌────▼─────┐
                    │  ngrok   │ (Public tunnel)
                    │  Tunnel  │
                    └────┬─────┘
                         │
                         │ localhost:5000
┌────────────────────────┼────────────────────────────────────┐
│                 Local Machine                               │
│                   ┌────▼──────────┐                         │
│                   │  HTTP Wrapper │ (Python Flask)          │
│                   │  Port 5000    │                         │
│                   └────┬──────────┘                         │
│                        │ stdin/stdout (JSON-RPC)            │
│                   ┌────▼──────────┐                         │
│                   │  MCP Server   │ (Node.js)               │
│                   │  TypeScript   │                         │
│                   └────┬──────────┘                         │
│                        │ Socket (Port 8080)                 │
│                   ┌────▼──────────┐                         │
│                   │ Revit Plugin  │ (C# .NET)               │
│                   │ RevitMCP      │                         │
│                   └────┬──────────┘                         │
│                        │                                    │
│                   ┌────▼──────────┐                         │
│                   │  Autodesk     │                         │
│                   │  Revit 2024   │                         │
│                   └───────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Components

### 1. **MCP Server** (`mcp-server/`)
- **Technology**: Node.js + TypeScript
- **Purpose**: Implements Model Context Protocol for tool execution
- **Key Features**:
  - 17 Revit automation tools
  - Bulk family grading with detailed analysis
  - JSON-RPC communication with Revit
  - stdin/stdout interface

### 2. **HTTP Wrapper** (`http-wrapper/`)
- **Technology**: Python Flask
- **Purpose**: Exposes MCP server via REST API for cloud access
- **Key Features**:
  - RESTful endpoints for Copilot Studio
  - Per-request MCP server execution (stable, no crashes)
  - CORS support for Microsoft cloud services
  - Health check endpoints

### 3. **Revit Plugin** (`revit-plugin/`)
- **Technology**: C# .NET (Revit API)
- **Purpose**: Executes commands inside Revit via external events
- **Key Features**:
  - Socket server (port 8080) for MCP communication
  - Command registry system
  - Family geometry grading engine
  - CSV export functionality

### 4. **Deployment Tools** (`deployment/`)
- PowerShell scripts for setup automation
- DLL deployment helpers
- ngrok tunnel management
- Environment verification

### 5. **Documentation** (`docs/`)
- Complete deployment guide
- Power Automate integration patterns
- Copilot Studio connector setup
- Architecture details

## 🚀 Quick Start

### Prerequisites
- **Revit 2024** installed
- **Node.js** 18+ installed
- **Python** 3.8+ installed
- **ngrok** account (free tier works)
- **Microsoft Copilot Studio** access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/DougBourban/revit-mcp-copilot-integration.git
   cd revit-mcp-copilot-integration
   ```

2. **Install dependencies**
   ```bash
   # Install Node.js dependencies
   cd mcp-server
   npm install
   npm run build
   
   # Install Python dependencies
   cd ../http-wrapper
   pip install -r requirements.txt
   ```

3. **Deploy Revit plugin**
   ```powershell
   cd ../deployment
   .\deploy_revit_plugin.ps1
   ```

4. **Start the servers**
   ```powershell
   # Terminal 1: Start HTTP wrapper
   cd http-wrapper
   python simple_rest_api.py
   
   # Terminal 2: Start ngrok
   ngrok http 5000
   ```

5. **Open Revit**
   - Open Revit 2024
   - Open a sample project
   - Enable MCP switch in Revit plugin UI

6. **Configure Copilot Studio**
   - Follow [`docs/COPILOT_STUDIO_SETUP.md`](docs/COPILOT_STUDIO_SETUP.md)
   - Use your ngrok URL as the base URL

## 📖 Documentation

- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Complete setup instructions
- **[Power Automate Integration](docs/POWER_AUTOMATE_INTEGRATION.md)** - Scheduled automation
- **[Copilot Studio Setup](docs/COPILOT_STUDIO_SETUP.md)** - Connector configuration
- **[Architecture](docs/ARCHITECTURE.md)** - Technical details

## 🎯 Example: Grade All Families

**Via Copilot Studio (Conversational):**
```
User: "Grade all doors in the project"
Copilot: ✅ Successfully graded 142 door families
         📊 Average Score: 96.4/100
         📁 CSV: C:\Temp\RevitFamilyGrades_Project_20251015.csv
         
         Grade Distribution:
         - A (Excellent): 132 families
         - D (Needs Review): 10 families
```

**Via Power Automate (Scheduled):**
- Runs daily at 9 AM
- Grades all families by category
- Emails CSV report to team
- Tracks quality trends over time

## 🔧 Key Features

### Family Geometry Grading
- **Geometry Type**: Checks for solids vs meshes (meshes perform poorly)
- **Face Count**: Analyzes polygon complexity
- **Import Source**: Detects SAT/ACIS imports (often problematic)
- **Nesting**: Checks nested family depth
- **Overall Score**: Weighted grade (A-F scale, 0-100 points)

### CSV Export
- **Detailed Mode**: 17 columns with full analysis
- **Quick Mode**: 5 columns for rapid review
- Auto-generated filenames with timestamps
- Compatible with Excel, Power BI, databases

### Supported Categories
- Doors, Windows, Furniture, Equipment
- Plumbing Fixtures, Railings, Walls, Floors
- **"All"** keyword for project-wide analysis

## ⚙️ Configuration

### Environment Variables
```bash
# Required
REVIT_MCP_SERVER_PATH=C:\path\to\mcp-server\build\index.js
NGROK_AUTHTOKEN=your_ngrok_token

# Optional
HTTP_WRAPPER_PORT=5000
MCP_SOCKET_PORT=8080
LOG_LEVEL=INFO
```

### Custom Commands
Add new Revit commands by:
1. Creating C# command in `revit-plugin/Commands/`
2. Adding TypeScript wrapper in `mcp-server/src/tools/`
3. Registering in `commandRegistry.json`

See [`docs/ADDING_CUSTOM_COMMANDS.md`](docs/ADDING_CUSTOM_COMMANDS.md)

## 🐛 Troubleshooting

### Common Issues

**"Operation failed (404)"**
- Check ngrok URL is current (free tier changes on restart)
- Update Copilot Studio connector with new URL

**"Request timeout"**
- Use `gradeType: "quick"` instead of `"detailed"`
- Test with smaller categories first
- Consider Power Automate for long operations (no timeout)

**"MCP switch is OFF"**
- Open Revit plugin UI
- Toggle MCP switch to ON
- Verify port 8080 is listening: `netstat -ano | findstr :8080`

See [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) for more

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on [Model Context Protocol](https://modelcontextprotocol.io)
- Inspired by the Revit API community
- Uses [ngrok](https://ngrok.com) for tunneling
- Powered by Microsoft Copilot Studio

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/DougBourban/revit-mcp-copilot-integration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/DougBourban/revit-mcp-copilot-integration/discussions)
- **Email**: support@example.com

## 🗺️ Roadmap

- [ ] Support for Revit 2025
- [ ] Additional grading criteria (materials, parameters)
- [ ] Real-time collaboration features
- [ ] Docker deployment option
- [ ] Azure VM deployment templates
- [ ] Pre-built Copilot topics library
- [ ] Power BI dashboard templates

---

**Made with ❤️ for the BIM community**
