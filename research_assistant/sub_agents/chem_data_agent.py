import sys

from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams

from research_assistant.config import make_model
from research_assistant.callbacks import (
    guard_compound_lookup,
    record_trusted_smiles,
    record_mutation_summary,
)
from research_assistant.prompts import CHEM_DATA_AGENT_INSTRUCTION


PROJECT_ROOT = Path(__file__).resolve().parents[2]

mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable, args=["-m", "mcp_server.server"], cwd=PROJECT_ROOT
        ),
        timeout=60,
    )
)

chem_data_agent = Agent(
    name="chem_data_agent",
    model=make_model(),
    description="Retrieves compound SMILES and identifiers from PubChem, "
    "resolves biological targets, and retrieves experimental bioactivity "
    "data from ChEMBL. Reports source-verified chemical structures, target information,"
    " activity measurements, and mutation annotations without inventing missing data.",
    instruction=CHEM_DATA_AGENT_INSTRUCTION,
    tools=[mcp_toolset],
    before_tool_callback=guard_compound_lookup,
    after_tool_callback=[record_trusted_smiles, record_mutation_summary],
)
