# Memoryful MCP Server

A Model Context Protocol (MCP) server that provides read-only access to the Memoryful API through standardized MCP tools.

## Features

- **13 Read-only Tools** for accessing Memoryful data
- **Comprehensive Coverage** of all main entities (days, months, insights, suggestions, tags, trackables, workspaces)
- **Error Handling** with proper logging through MCP context
- **Modern Python** using type hints and async/await

## Available Tools

### Days

- `get_days` - Get days with pagination, sorting, filtering by tags
- `get_day_by_timestamp` - Get a specific day by UNIX timestamp
- `get_random_day` - Get a random day with optional date range

### Months

- `get_months_by_year` - Get all months for a specific year
- `get_month_by_year_and_month_number` - Get a specific month

### Insights

- `get_insights` - Get insights with pagination, optionally filtered by day timestamp

### Suggestions

- `get_suggestions` - Get suggestions with pagination, optionally filtered by day timestamp

### Tags

- `get_tags` - Get all tags
- `get_tag_by_id` - Get a specific tag by ID

### Trackables

- `get_trackables` - Get trackable items, optionally filtered by type or search query
- `get_trackable_by_id` - Get a specific trackable by ID
- `get_trackable_types` - Get all trackable types
- `get_trackable_type_by_id` - Get a specific trackable type by ID

### Workspaces

- `get_my_workspace` - Get the current user's workspace settings

## Installation

1. **Install dependencies:**

    ```bash
    pip install -r requirements.mcp.txt
    ```

2. **Set up environment variables:**

    ```bash
    cp .env.example .env
    # Edit .env with your configuration
    ```

## Configuration

Create a `.env` file with the following variables:

```env
MEMORYFUL_API_BASE_URL=http://localhost:8000
MCP_HOST=127.0.0.1
MCP_PORT=3001
```

### Authentication

The server supports two authentication methods:

1. **HTTP Authorization header** (SSE transport) — set the `Authorization: Bearer <token>` header in your MCP client
2. **`MEMORYFUL_ACCESS_TOKEN` env var** (STDIO transport) — for clients like Claude Desktop where HTTP headers are not available

## Usage

### Running the Server

```bash
# From the memoryful-backend directory
py -m mcp_server.main
```

The server starts with SSE transport on the configured host/port (default `127.0.0.1:3001`).

### Using with MCP Clients

**Example with Claude Desktop (STDIO):**

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memoryful": {
      "command": "cmd",
      "args": [
        "/c",
        "cd /d c:\\path\\to\\memoryful-backend && py -m mcp_server.main"
      ],
      "env": {
        "MEMORYFUL_ACCESS_TOKEN": "your_access_token_here"
      }
    }
  }
}
```

**Example with MCP Inspector (SSE):**

1. Set Transport Type to **SSE**
2. Set URL to `http://localhost:3001/sse`
3. Add `Authorization: Bearer <token>` in Custom Headers

## Development

### Project Structure

```text
mcp_server/
├── main.py              # MCP server setup and tool registration
├── settings.py          # Environment configuration
├── requirements.mcp.txt # Python dependencies
├── schemas/             # Pydantic response wrapper
│   └── __init__.py
├── tools/               # Tool implementations
│   ├── days.py
│   ├── months.py
│   ├── insights.py
│   ├── suggestions.py
│   ├── tags.py
│   ├── trackables.py
│   └── workspaces.py
├── tests/               # Unit tests
│   ├── conftest.py
│   ├── test_days.py
│   ├── test_months.py
│   ├── test_insights.py
│   ├── test_suggestions.py
│   ├── test_tags.py
│   ├── test_trackables.py
│   └── test_workspaces.py
└── utils/
    └── api_client.py    # HTTP client with auth forwarding
```

### Adding New Tools

1. Create a new file in `tools/` or add to existing files
2. Define async functions with `ctx: Context` parameter
3. Use `APIClient(ctx)` to make API calls
4. Register the tool in `main.py` with `mcp.tool()(your_function)`

### Running Tests

```bash
py -m pytest mcp_server/tests -v
```

## Dependencies

- `fastmcp` - MCP server framework
- `httpx` - Async HTTP client for API requests
- `python-dotenv` - Environment variable management
