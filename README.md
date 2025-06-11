# MCP HTTP Wrapper

MCP HTTP Wrapper - Expose stdio-based Model Context Protocol servers via HTTP using official Streamable HTTP   transport. Supports tools, prompts, resources with JSON-RPC 2.0, SSE streaming, session management &amp; security.   Transform any MCP server into a REST API.

## Features

- ✅ **Standards Compliant**: Implements MCP Streamable HTTP transport specification
- ✅ **Full MCP Support**: Tools, prompts, resources, and initialization
- ✅ **JSON-RPC 2.0**: Proper request/response handling with error codes
- ✅ **Server-Sent Events**: Streaming support for real-time communication
- ✅ **Session Management**: Optional session tracking with `Mcp-Session-Id`
- ✅ **Security**: Origin validation, localhost binding by default
- ✅ **Thread Safe**: Robust concurrent request handling
- ✅ **Error Handling**: Comprehensive error messages and port conflict detection

## Installation

No additional dependencies required beyond Python standard library + Flask:

```bash
pip install flask
```

## Quick Start

### Basic Usage

```bash
# Start with default settings (localhost:5000)
python http_wrapper.py python your-mcp-server.py

# Custom host and port
python http_wrapper.py --host 0.0.0.0 --port 8080 python your-mcp-server.py

# For commands with conflicting flags, use --
python http_wrapper.py --port 3000 -- npx -y @modelcontextprotocol/server-filesystem .
```

### Command Line Options

```
--host HOST     Host to bind to (default: 127.0.0.1 - localhost only)
                Use 0.0.0.0 to allow network access
--port PORT     Port to bind to (default: 5000)
--debug         Enable Flask debug mode
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/mcp` | Main JSON-RPC endpoint |
| `GET` | `/mcp` | Server-Sent Events streaming |
| `GET` | `/health` | Health check |

### Supported MCP Methods

- `initialize` - MCP handshake and capability negotiation
- `tools/list` - List available tools
- `tools/call` - Execute a tool
- `prompts/list` - List available prompts
- `prompts/get` - Retrieve a prompt
- `resources/list` - List available resources
- `resources/read` - Read a resource

## Usage Examples

### 1. Initialize Connection

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
      "clientInfo": {"name": "my-client", "version": "1.0.0"}
    },
    "id": 1
  }'
```

### 2. List Available Tools

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}'
```

### 3. Call a Tool

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "read_file",
      "arguments": {"path": "/path/to/file.txt"}
    },
    "id": 3
  }'
```

### 4. Get a Prompt

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "prompts/get",
    "params": {
      "name": "code_review",
      "arguments": {"language": "python"}
    },
    "id": 4
  }'
```

### 5. Read a Resource

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "resources/read",
    "params": {
      "uri": "file:///path/to/resource.txt"
    },
    "id": 5
  }'
```

### 6. Server-Sent Events Stream

```bash
curl -H "Accept: text/event-stream" http://127.0.0.1:5000/mcp
```

### 7. Health Check

```bash
curl http://127.0.0.1:5000/health
```

## Session Management

Use the optional `Mcp-Session-Id` header to maintain session state:

```bash
curl -X POST http://127.0.0.1:5000/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: unique-session-123" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Response Format

All responses follow JSON-RPC 2.0 format:

### Success Response
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [...]
  },
  "id": 1
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": "Unknown method: invalid/method"
  },
  "id": 1
}
```

## Common Error Codes

| Code | Message | Description |
|------|---------|-------------|
| `-32700` | Parse error | Invalid JSON |
| `-32600` | Invalid Request | Malformed JSON-RPC |
| `-32601` | Method not found | Unknown MCP method |
| `-32602` | Invalid params | Missing/invalid parameters |
| `-32603` | Internal error | Server-side error |

## Examples with Popular MCP Servers

### File System Server
```bash
# Install and run
npm install -g @modelcontextprotocol/server-filesystem
python http_wrapper.py -- npx @modelcontextprotocol/server-filesystem /path/to/directory
```

### SQLite Server
```bash
# Install and run
npm install -g @modelcontextprotocol/server-sqlite
python http_wrapper.py -- npx @modelcontextprotocol/server-sqlite /path/to/database.db
```

### Git Server
```bash
# Install and run
npm install -g @modelcontextprotocol/server-git
python http_wrapper.py -- npx @modelcontextprotocol/server-git --repository /path/to/repo
```

## Security Considerations

- **Default localhost binding**: Server binds to `127.0.0.1` by default for security
- **Origin validation**: Validates `Origin` headers when provided
- **Network access**: Use `--host 0.0.0.0` only when network access is needed
- **Input validation**: All JSON-RPC requests are validated
- **Error handling**: Sensitive information is not exposed in error messages

## Troubleshooting

### Port Already in Use
```
❌ Error: Port 5000 is already in use!

Suggestions:
  • Try a different port: --port 5001
  • Check what's using port 5000: netstat -tulpn | grep 5000
  • Kill the conflicting process if it's safe to do so
```

### MCP Server Not Starting
- Check that the MCP server command is correct
- Verify the MCP server executable is in your PATH
- Look at the console output for MCP server error messages

### Connection Issues
- Verify the host and port are correct
- Check firewall settings if accessing from another machine
- Ensure the MCP server is running and responding

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Related

- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)
- [MCP Server Directory](https://github.com/modelcontextprotocol/servers)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

