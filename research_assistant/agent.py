import sys

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

from research_assistant.prompts import CHEM_AGENT_INSTRUCTION
from research_assistant.tools.chem_tools import assess_druglikeness, tanimoto_similarity
from research_assistant.callbacks import guard_compound_lookup


PROJECT_ROOT = Path(__file__).resolve().parents[1]

mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable, args=["-m", "mcp_server.server"], cwd=PROJECT_ROOT
        ),
        timeout=60,
    )
)


root_agent = Agent(
    name="research_assistant",
    model=Gemini(
        model="gemini-3.5-flash-lite",
        retry_options=types.HttpRetryOptions(
            initial_delay=1, attempts=5, http_status_codes=[429, 500, 503, 504]
        ),
    ),
    description="A drug-discovery research assistant for compound and target lookup, "
    "bioactivity analysis, molecular property and drug-likeness evaluation, "
    "and structural similarity analysis.",
    instruction=CHEM_AGENT_INSTRUCTION,
    tools=[assess_druglikeness, tanimoto_similarity, mcp_toolset],
    before_tool_callback=guard_compound_lookup,
)
