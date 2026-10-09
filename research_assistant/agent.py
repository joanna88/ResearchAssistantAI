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
from research_assistant.tools.literature_tools import (
    ingest_literature,
    search_literature,
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
    "structural similarity analysis and literature retrieval from Europe PMC abstracts.",
    instruction=CHEM_AGENT_INSTRUCTION,
    tools=[
        assess_druglikeness,
        tanimoto_similarity,
        ingest_literature,
        search_literature
    ],
    before_tool_callback=guard_compound_lookup,
)


from research_assistant.sub_agents.chem_data_agent import chem_data_agent

root_agent = chem_data_agent  # TEMPORARY: test the specialist alone
