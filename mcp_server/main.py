from fastmcp import FastMCP
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
mcp.tool()(months.get_months)
mcp.tool()(months.get_month_by_id)
mcp.tool()(months.get_months_by_year)
mcp.tool()(months.get_current_month)

# insights tools
mcp.tool()(insights.get_insights)
mcp.tool()(insights.get_insight_by_id)
mcp.tool()(insights.get_insights_by_type)
mcp.tool()(insights.get_insights_for_day)

# suggestions tools
mcp.tool()(suggestions.get_suggestions)
mcp.tool()(suggestions.get_suggestion_by_id)
mcp.tool()(suggestions.get_suggestions_by_type)

# tags tools
mcp.tool()(tags.get_tags)
mcp.tool()(tags.get_tag_by_id)

# trackables tools
mcp.tool()(trackables.get_trackables)
mcp.tool()(trackables.get_trackable_by_id)
mcp.tool()(trackables.get_trackable_types)
mcp.tool()(trackables.get_trackable_type_by_id)
mcp.tool()(trackables.get_trackables_for_day)
mcp.tool()(trackables.get_trackable_progress)

# workspaces tools
mcp.tool()(workspaces.get_workspaces)
mcp.tool()(workspaces.get_workspace_by_id)
mcp.tool()(workspaces.get_workspace_days)
mcp.tool()(workspaces.get_workspace_insights)

if __name__ == "__main__":
    mcp.run()
