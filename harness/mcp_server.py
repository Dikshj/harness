
from mcp.server import Server
from mcp.types import Tool, TextContent
from harness.tools.registry import get_registry

mcp = Server("autonomous-harness")

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    reg = get_registry()
    return [
        Tool(name=t.name, description=t.description, inputSchema=t.parameters)
        for t in reg.list().values()
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    reg = get_registry()
    tool = reg.get(name)
    result = tool.handler(**arguments)
    return [TextContent(type="text", text=str(result))]

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())
