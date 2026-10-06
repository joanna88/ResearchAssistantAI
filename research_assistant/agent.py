from google.adk.agents.llm_agent import Agent


root_agent = Agent(name="research_assistant", 
                   model='gemini-2.5-flash',
                   description="A research assistant that helps with research tasks.",
                   instruction="You are a research assistant that helps with research tasks. You can answer questions, provide summaries, and assist with research-related tasks.",
                )
