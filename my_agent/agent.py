from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    description="This is the root agent",
    instruction="You are a helpful assistant.",
    tools=[google_search],
)