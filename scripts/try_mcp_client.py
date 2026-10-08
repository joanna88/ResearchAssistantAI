import asyncio
import sys
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server.server"]
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            for tool in tools.tools:
                tool_data = {
                    "tool_name": tool.name,
                    "tool_description": tool.description,
                    "tool_input_schema": tool.input_schema,
                }
                print(json.dumps(tool_data, indent=2))

            for name in ["sotorasib", "notarealdrugxyz"]:
                result = await session.call_tool(
                    "lookup_compound_by_name", {"name": name}
                )

                data = json.loads(result.content[0].text)
                print(json.dumps(data, indent=1))


asyncio.run(main())
