from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from research_assistant.prompts import CHEM_AGENT_INSTRUCTION
from research_assistant.tools.chem_tools import assess_druglikeness


root_agent = Agent(name="research_assistant", 
                   model=Gemini(
                       model="gemini-3.5-flash-lite",
                       retry_options=types.HttpRetryOptions(initial_delay=1, 
                                                                attempts=5,
                                                                http_status_codes=[429, 500, 503, 504])
                                                                ),
                   description="A research assistant for evaluating molecular properties and drug-likeness metrics from SMILES strings.",

                   instruction=CHEM_AGENT_INSTRUCTION,
                   tools=[assess_druglikeness],
                   )
