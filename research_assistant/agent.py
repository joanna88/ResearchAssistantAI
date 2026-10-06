from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types


root_agent = Agent(name="research_assistant", 
                   model=Gemini(
                       model="gemini-3.5-flash-lite",
                       retry_options=types.HttpRetryOptions(initial_delay=1, 
                                                                attempts=5,
                                                                http_status_codes=[429, 500, 503, 504])
                                                                ),
                   description="A research assistant that helps with research tasks.",
                   instruction="You are a research assistant that helps with research tasks. You can answer questions, provide summaries, and assist with research-related tasks.",
                   )
