from google.adk.agents import Agent

from research_assistant.tools.chem_tools import assess_druglikeness, tanimoto_similarity
from research_assistant.config import make_model
from research_assistant.prompts import ANALYSIS_AGENT_INSTRUCTION
from research_assistant.callbacks import guard_trusted_smiles


analysis_agent = Agent(
    name="analysis_agent",
    model=make_model(),
    description="Calculates molecular properties, drug-likeness (Lipinski, QED) "
    "and Tanimoto similarity from SMILES given in the request. Requires SMILES "
    "with their compound IDs; cannot look up compounds by name.",
    instruction=ANALYSIS_AGENT_INSTRUCTION,
    before_tool_callback=guard_trusted_smiles,
    tools=[assess_druglikeness, tanimoto_similarity],
)
