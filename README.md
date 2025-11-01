# Backlog API MCP Server

A Model Context Protocol (MCP) server that provides local access to Backlog API documentation. This server fetches documentation from the official Backlog API documentation site, converts it to Markdown format, and serves it via MCP for easy integration with AI assistants and development tools.

## Features

- 🔄 **Automatic Documentation Fetching**: Automatically fetches Backlog API documentation from the web
- 📝 **Markdown Conversion**: Converts HTML documentation to clean Markdown format using JINA Reader
- 🐳 **Docker Support**: Easy deployment with Docker and docker compose
- ⚡ **Fast Startup**: Immediate server availability with progressive document loading
- 🔍 **Search & Query**: Search API endpoints, parameters, and error codes
- 🔁 **Retry Logic**: Robust retry mechanism with exponential backoff
- 📊 **Health Monitoring**: Health check endpoint for monitoring

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- JINA Reader API key ([Get one here](https://jina.ai/reader))

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd backlog-api-doc
```

2. **Create environment file**
```bash
cp .env.example .env
```

3. **Configure API key**
Edit `.env` and set your JINA Reader API key:
```bash
JINA_API_KEY=your_jina_api_key_here
```

4. **Start the server**
```bash
docker compose up -d
```

5. **Verify the server is running**
```bash
curl http://localhost:58080/health
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JINA_API_KEY` | JINA Reader API key (required) | - |
| `SCRAPING_DELAY` | Delay between requests (ms) | 1000 |
| `MAX_CONCURRENT_REQUESTS` | Maximum concurrent requests | 3 |
| `OUTPUT_DIR` | Output directory for docs | `/app/data` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MCP_PORT` | MCP server port | 58080 |
| `MCP_HOST` | MCP server host | `0.0.0.0` |
| `FORCE_REFRESH` | Force refresh of documentation | `false` |

## MCP API Endpoints

### Health Check
```bash
GET /health
```

Returns server status, initialization state, and document availability.

### Search API Documentation
```bash
POST /mcp/search_backlog_api
Content-Type: application/json

{
  "query": "issues create",
  "category": "endpoints"  // optional
}
```

### Get API Specification
```bash
POST /mcp/get_api_spec
Content-Type: application/json

{
  "endpoint": "GET /api/v2/issues"
}
```

### List API Categories
```bash
GET /mcp/list_api_categories
```

### Get Error Information
```bash
POST /mcp/get_error_info
Content-Type: application/json

{
  "error_code": "40001"
}
```

## Document Structure

The fetched documentation is organized as follows:

```
data/
├── authentication/     # Authentication documentation
├── endpoints/         # API endpoint documentation
│   ├── issues/       # Issues API
│   ├── projects/     # Projects API
│   └── users/        # Users API
├── errors/           # Error codes
└── sdks/             # SDK documentation
```

## Startup Flow

The server implements a progressive loading strategy for fast startup:

1. **Phase 1 (0-5 seconds)**: Server starts immediately
2. **Phase 2 (5-15 seconds)**: Essential documentation pages are fetched (17 priority pages)
3. **Phase 3 (background)**: Remaining documentation is fetched in the background

### Priority Pages

The following pages are fetched first for immediate availability:

- Authentication
- Getting Started
- Issues API (overview, get list, get, create, update)
- Projects API (get list, get)
- Users API (get list, get)
- Error Codes

## MCP Client Configuration

This server can be used with MCP-compatible clients like Claude Desktop, Cursor, or other AI assistants. There are two ways to connect:

### Option 1: HTTP-based Connection (Direct)

For clients that support HTTP transport:

```json
{
  "mcpServers": {
    "backlog-api": {
      "url": "http://localhost:58080",
      "description": "Backlog API Documentation MCP Server",
      "transport": "http"
    }
  }
}
```

See `mcp-client-config.json` for a complete example with tool definitions.

### Option 2: stdio-based Connection (Recommended)

Most MCP clients (like Claude Desktop) use stdio transport. Use the provided stdio wrapper:

**Using Docker (Recommended - No local dependencies required):**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "backlog-api-mcp",
        "python",
        "/app/mcp-server-stdio.py"
      ],
      "env": {}
    }
  }
}
```

**Using local Python (requires httpx installed):**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "python3",
      "args": [
        "/absolute/path/to/backlog-api-doc/mcp-server-stdio.py"
      ],
      "env": {}
    }
  }
}
```

**Note**: Make sure the HTTP server is running on `http://localhost:58080` before starting the stdio wrapper. For local Python, install dependencies: `pip install httpx` (or use `--break-system-packages` if needed).


### Claude Desktop Configuration

For Claude Desktop, edit the configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Recommended: Using Docker (no local Python dependencies needed)**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "backlog-api-mcp",
        "python",
        "/app/mcp-server-stdio.py"
      ]
    }
  }
}
```

**Alternative: Using local Python (requires httpx)**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "python3",
      "args": [
        "/absolute/path/to/backlog-api-doc/mcp-server-stdio.py"
      ]
    }
  }
}
```

**Important**: 
- Make sure Docker container `backlog-api-mcp` is running before using Docker method
- For local Python method, install httpx: `pip3 install httpx` (may need `--break-system-packages` flag)

Restart Claude Desktop after configuration.

### Amazon Q Configuration

For Amazon Q Developer, edit the configuration file:

**macOS/Linux**: `~/.aws/amazonq/mcp.json`

**Using Docker:**

```json
{
  "mcpServers": {
    "backlog-api": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "backlog-api-mcp",
        "python",
        "/app/mcp-server-stdio.py"
      ]
    }
  }
}
```

**Troubleshooting for Amazon Q:**

If you see "Transport closed" error:
1. Ensure Docker container is running: `docker compose ps`
2. Test the wrapper manually: `echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | docker exec -i backlog-api-mcp python /app/mcp-server-stdio.py`
3. Check logs: `docker compose logs backlog-api-mcp`
4. Ensure Docker daemon is accessible from Amazon Q

See `mcp-config-amazon-q.json` for a complete example.

## Usage Examples

### Using curl (HTTP API)

```bash
# Search for "issues" related APIs
curl -X POST http://localhost:58080/mcp/search_backlog_api \
  -H "Content-Type: application/json" \
  -d '{"query": "issues create"}'

# Get specific API specification
curl -X POST http://localhost:58080/mcp/get_api_spec \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "GET /api/v2/issues"}'

# List API categories
curl http://localhost:58080/mcp/list_api_categories

# Get error information
curl -X POST http://localhost:58080/mcp/get_error_info \
  -H "Content-Type: application/json" \
  -d '{"error_code": "40001"}'
```

### Using MCP Client (stdio)

Once configured, you can use the tools directly in your MCP client:

- `search_backlog_api`: Search for API documentation
- `get_api_spec`: Get detailed API specification
- `list_api_categories`: List available API categories
- `get_error_info`: Get error code information

### Force Refresh

To force refresh all documentation:

```bash
docker compose exec backlog-api-mcp python -c "
import os
os.environ['FORCE_REFRESH']='true'
exec(open('src/fetch_docs.py').read())
"
```

Or set `FORCE_REFRESH=true` in `.env` and restart:

```bash
docker compose restart
```

## Development

### Project Structure

```
backlog-api-doc/
├── src/
│   ├── fetch_docs.py      # Document fetching logic
│   ├── mcp_server.py      # MCP server implementation
│   ├── config.py          # Configuration management
│   └── utils/
│       ├── retry.py       # Retry utilities
│       └── markdown.py    # Markdown conversion
├── mcp-server-stdio.py    # stdio wrapper for MCP clients
├── mcp-client-config.json # MCP client configuration example
├── mcp-config-claude.json # Claude Desktop configuration example
├── docker compose.yml     # Docker Compose configuration
├── Dockerfile             # Docker image definition
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Building Locally

```bash
# Build the Docker image
docker build -t backlog-api-doc:latest .

# Run the container
docker run -d \
  --name backlog-api-mcp \
  --env-file .env \
  -p 58080:58080 \
  -v $(pwd)/data:/app/data \
  backlog-api-doc:latest
```

### Running Tests

```bash
# Check server health
curl http://localhost:58080/health

# Test search functionality
curl -X POST http://localhost:58080/mcp/search_backlog_api \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication"}'
```

## Troubleshooting

### Server won't start

1. Check that `JINA_API_KEY` is set in `.env`
2. Verify Docker is running: `docker ps`
3. Check logs: `docker compose logs backlog-api-mcp`

### Documentation not fetching

1. Verify JINA API key is valid
2. Check network connectivity
3. Review logs for specific errors: `docker compose logs -f`

### Port already in use

Change the port in `.env`:
```bash
MCP_PORT=8081
```

## License

This project is provided as-is for local use. Please ensure compliance with Backlog API documentation usage terms.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Links

- [Backlog API Documentation](https://developer.nulab.com/ja/docs/backlog/)
- [JINA Reader](https://jina.ai/reader)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

📖 [日本語版README](README_ja.md)
