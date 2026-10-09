from mcp.server.mcpserver import MCPServer
from mcp_server.pubchem import lookup_compound_by_name
from mcp_server.chembl import search_targets, get_target_activities


server = MCPServer(
    "chem-data",
    instructions="Chemical data lookups from PubChem and ChEMBL for drug-discovery "
    "research, including compound identity, target search, and target "
    "activity data.",
)
server.tool()(lookup_compound_by_name)
server.tool()(search_targets)
server.tool()(get_target_activities)

if __name__ == "__main__":
    server.run()
