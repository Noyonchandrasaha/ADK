from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

def get_current_time(city: str) -> dict:
    return{
        "status": "success",
        "city": city,
        "time": "10.00 AM"
    }

root_agent = Agent(
    model=LiteLlm(
        model="openai/gpt-4o",        # OpenAI model
        temperature=0.1
    ),
    name='root_agent',
    description='Tells the current time in a specified city.',
    instruction=f'You are a helpful assistant that tells the current time in cities. Use the {get_current_time} tool for this purpose.',
    tools=[get_current_time],
)
