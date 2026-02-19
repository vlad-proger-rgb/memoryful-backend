from fastmcp import FastMCP
# from .settings import MCP_HOST, MCP_PORT
from .tools import (
    days,
    months,
    insights,
    suggestions,
    tags,
    trackables,
    workspaces,
)

mcp = FastMCP(
    name="Memoryful MCP Server"
)

# days tools
mcp.tool()(days.get_days)
mcp.tool()(days.get_day_by_timestamp)
mcp.tool()(days.get_random_day)

# months tools
mcp.tool()(months.get_months_by_year)
mcp.tool()(months.get_month_by_year_and_month_number)

# insights tools
mcp.tool()(insights.get_insights)

# suggestions tools
mcp.tool()(suggestions.get_suggestions)

# tags tools
mcp.tool()(tags.get_tags)
mcp.tool()(tags.get_tag_by_id)

# trackables tools
mcp.tool()(trackables.get_trackables)
mcp.tool()(trackables.get_trackable_by_id)
mcp.tool()(trackables.get_trackable_types)
mcp.tool()(trackables.get_trackable_type_by_id)

# workspaces tools
mcp.tool()(workspaces.get_my_workspace)

if __name__ == "__main__":
    mcp.run()
    # mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT)
