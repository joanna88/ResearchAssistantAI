from google.adk.agents import Agent
from google.adk.tools import AgentTool

from research_assistant.config import make_model
from research_assistant.prompts import COORDINATOR_AGENT_INSTRUCTION
from research_assistant.sub_agents.analysis_agent import analysis_agent
from research_assistant.sub_agents.chem_data_agent import chem_data_agent
from research_assistant.sub_agents.literature_agent import literature_agent
from research_assistant.callbacks import save_user_message


root_agent = Agent(
    name="research_assistant",
    model=make_model(),
    description="A drug-discovery research assistant for compound and target lookup, "
    "bioactivity analysis, molecular property and drug-likeness evaluation, "
    "structural similarity analysis and literature retrieval from Europe PMC abstracts.",
    instruction=COORDINATOR_AGENT_INSTRUCTION,
    before_agent_callback=save_user_message,
    tools=[
        AgentTool(chem_data_agent),
        AgentTool(analysis_agent),
        AgentTool(literature_agent),
    ],
)
