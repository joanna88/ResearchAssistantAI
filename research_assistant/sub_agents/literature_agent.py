from google.adk.agents import Agent

from research_assistant.config import make_model
from research_assistant.prompts import LITERATURE_AGENT_INSTRUCTION
from research_assistant.tools.literature_tools import (
    ingest_literature,
    search_literature,
)


literature_agent = Agent(
    name="literature_agent",
    model=make_model(),
    description="Retrieves Europe PMC abstracts for a research question and "
    "returns findings with citations (title, year, link). Use for any literature "
    "or evidence question.",
    instruction=LITERATURE_AGENT_INSTRUCTION,
    tools=[ingest_literature, search_literature],
)
