import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types


import warnings
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Change to DEBUG for more detailed logs

# Filter warnings if necessary
warnings.filterwarnings("default")

print("Libraries imported successfully")

MODEL_GPT_40 = 'openai/gpt-4o'

def get_weather(city: str) -> dict:
    """Retrieve the current weather report for a specified city.
        Args:
            city (str): The name of the city (e.g., "Dhaka", "Rangpur", "Chandpur").
        Returns:
        dict: A dictionary containing the weather information.
            Includes a 'status' key ('success' or 'error').
            If 'success', includes a 'report' key with weather details.
            If 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather called for {city}")
    city_normalized = city.lower().replace(" ", "")

    # Mock weather data
    mock_weather_data = {
        "dhaka": {"status": "success", "report": "The weather in Dhaka is sunny with a temperature of 25°C"},
        "rangpur": {"status": "success", "report": "The weather in Rangpur is quite windy with a temperature of 15°C. So cold."},
        "chandpur": {"status": "success", "report": "Chandpur is experiencing light rain and a temperature of 18°C."},
    }

    if city_normalized in mock_weather_data:
        return mock_weather_data[city_normalized]
    else:
        return {
            "status": "error",
            "error_message": f"Sorry, I don't have weather information for {city}."
        }

# Create agent
root_agent  = Agent(
    name="weather_agent_v1",
    model=LiteLlm(model=MODEL_GPT_40),
    description="Provides weather information for specific cities.",
    instruction=(
        "You are a helpful weather assistant. "
        "When the user asks for the weather in a specific city, "
        "use the 'get_weather' tool to find the information. "
        "If the tool returns an error, inform the user politely. "
        "If the tool is successful, present the weather report clearly."
    ),
    tools=[get_weather]
)

print(f"Agent {root_agent .name} created using model {MODEL_GPT_40}")

# Session service
session_service = InMemorySessionService()

APP_NAME = "weather_tutorial_app"
USER_ID = 'user_1'
SESSION_ID = "session_001"

# Correct async session creation
async def create_session():
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    print(f"Session created: App={APP_NAME}, User={USER_ID}, Session={SESSION_ID}")
    return session

# Runner initialization
runner = Runner(
    agent=root_agent ,
    app_name=APP_NAME,
    session_service=session_service
)

print(f"Runner created for agent {runner.agent.name}")

# Asynchronous agent query and response handling
async def call_agent_async(query: str, runner, user_id, session_id):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>> User Query: {query}")

    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        print(f" [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            break
    print(f"<<< Agent Response: {final_response_text}")

# Running conversation asynchronously
async def run_conversation():
    session = await create_session()  # Ensure session is created asynchronously
    await call_agent_async("What is the weather like in Dhaka?",
                           runner=runner,
                           user_id=USER_ID,
                           session_id=SESSION_ID)

    await call_agent_async("How about Rangpur?",
                           runner=runner,
                           user_id=USER_ID,
                           session_id=SESSION_ID)

    await call_agent_async("Tell me the weather in Chandpur",
                           runner=runner,
                           user_id=USER_ID,
                           session_id=SESSION_ID)

# Main execution
if __name__ == "__main__":
    try:
        asyncio.run(run_conversation())
    except Exception as e:
        print(f"An error occurred: {e}")
