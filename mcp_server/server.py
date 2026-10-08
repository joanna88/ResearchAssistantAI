from mcp.server.mcpserver import MCPServer
from mcp_server.pubchem import lookup_compound_by_name


server = MCPServer(
    "chem-data",
    instructions="Chemical data lookups (PubChem) for drug-discovery research.",
)
server.tool()(lookup_compound_by_name)


if __name__ == "__main__":
    server.run()
