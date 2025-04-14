# server.py
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Quay")

if __name__ == "__main__":
    mcp.run()
