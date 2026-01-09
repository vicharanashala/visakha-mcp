#!/usr/bin/env python3
"""
Minimal test to verify both tools are exposed via MCP
"""
from fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("Test Server")

@mcp.tool()
async def tool_one(query: str) -> str:
    """First tool"""
    return f"Tool one: {query}"

@mcp.tool()
async def tool_two(data: str, optional: Optional[str] = None) -> dict:
    """Second tool"""
    return {"success": True, "data": data, "optional": optional}

if __name__ == "__main__":
    print("Starting test MCP server with 2 tools...")
    mcp.run(transport='streamable-http', host='0.0.0.0', port=9011)
