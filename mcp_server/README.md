# Memoryful MCP Server

A Model Context Protocol (MCP) server that provides read-only access to the Memoryful API through standardized MCP tools.

## Features

- **31 Read-only Tools** for accessing Memoryful data
- **Automatic Token Refresh** using refresh tokens
- **Comprehensive Coverage** of all main entities (days, months, insights, suggestions, tags, trackables, workspaces)
- **Error Handling** with proper logging through MCP context
- **Modern Python** using type hints and async/await

## Available Tools

### Days

- `get_days` - List days with pagination
- `get_day_by_id` - Get specific day by ID
- `get_days_by_date_range` - Get days within date range
- `search_days` - Search days by content

### Months

- `get_months` - List months with pagination
- `get_month_by_id` - Get specific month by ID
- `get_months_by_year` - Get all months for a year
- `get_current_month` - Get current month

### Insights

- `get_insights` - List insights with pagination
- `get_insight_by_id` - Get specific insight by ID
- `get_insights_by_type` - Get insights filtered by type
- `get_insights_for_day` - Get insights for a specific day

### Suggestions

- `get_suggestions` - List suggestions with pagination
- `get_suggestion_by_id` - Get specific suggestion by ID
- `get_suggestions_for_day` - Get suggestions for a specific day
- `get_suggestions_by_type` - Get suggestions filtered by type

### Tags

- `get_tags` - List tags with pagination
- `get_tag_by_id` - Get specific tag by ID
- `get_tag_by_name` - Get specific tag by name
- `get_tags_for_day` - Get tags for a specific day
- `search_tags` - Search tags by name

### Trackables

- `get_trackables` - List trackable items with pagination
- `get_trackable_by_id` - Get specific trackable by ID
- `get_trackable_types` - List trackable types
- `get_trackable_type_by_id` - Get specific trackable type by ID
- `get_trackables_for_day` - Get trackables for a specific day
- `get_trackable_progress` - Get progress history for a trackable

### Workspaces

- `get_workspaces` - List workspaces with pagination
- `get_workspace_by_id` - Get specific workspace by ID
- `get_workspace_days` - Get days for a specific workspace
- `get_workspace_insights` - Get insights for a specific workspace

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
MEMORYFUL_REFRESH_TOKEN=your_refresh_token_here
```

### Getting a Refresh Token

1. Start your Memoryful backend server
2. Log in through your app or API to get a refresh token
3. The refresh token is typically returned in the login response or set as a cookie

## Usage

### Running the Server

```bash
# From the mcp_server directory
python -m mcp_server.main
```

### Using with MCP Clients

The server will automatically register all tools and can be used by any MCP-compatible client.

**Example with Claude Desktop:**

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memoryful": {
      "command": "cmd",
      "args": [
        "/c",
        "cd /d c:\\Users\\somet\\Desktop\\Proging\\Memoryful\\memoryful-backend && py -m mcp_server.main"
      ]
    }
  }
}
```

### Example Tool Usage

Once connected, you can use tools like:

- "Get the last 10 days from my Memoryful data"
- "Search for insights about productivity"
- "Show me all tags for today"
- "Get trackable progress for my exercise goal"

## Development

### Project Structure

```text
mcp_server/
├── main.py              # MCP server setup and tool registration
├── settings.py          # Environment configuration
├── requirements.mcp.txt # Python dependencies
├── tools/               # Tool implementations
│   ├── days.py
│   ├── months.py
│   ├── insights.py
│   ├── suggestions.py
│   ├── tags.py
│   ├── trackables.py
│   └── workspaces.py
└── utils/
    └── api_client.py    # HTTP client with auto-refresh
```

### Adding New Tools

1. Create a new file in `tools/` or add to existing files
2. Define async functions with `ctx: Context` parameter
3. Use `APIClient(ctx)` to make API calls
4. Register the tool in `main.py` with `mcp.tool()(your_function)`

## Security

- Uses refresh tokens instead of access tokens for better security
- Automatic token refresh prevents expired token issues
- All requests are made over HTTPS in production
- No sensitive data is stored in logs

## Troubleshooting

### Common Issues

1. **"No refresh token provided"**
   - Check that `MEMORYFUL_REFRESH_TOKEN` is set in `.env`
   - Verify the refresh token is valid and not expired

2. **"Token refresh failed"**
   - Ensure your Memoryful backend is running
   - Check that the refresh token hasn't been revoked
   - Verify `MEMORYFUL_API_BASE_URL` is correct

3. **Connection errors**
   - Make sure your Memoryful API server is running
   - Check the API URL in your configuration
   - Verify network connectivity

### Debug Mode

The server logs errors and token refresh events through the MCP context, which will be visible in your MCP client's logs.

## Dependencies

- `fastmcp` - MCP server framework
- `httpx` - Async HTTP client for API requests
- `python-dotenv` - Environment variable management
