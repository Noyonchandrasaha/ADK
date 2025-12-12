import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from typing import Optional
import warnings
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Change to DEBUG for more detailed logs

# Filter warnings if necessary
warnings.filterwarnings("default")

print("Libraries imported successfully")

MODEL_GPT_40 = 'openai/gpt-4o'

# Weather Tool
def get_weather(city: str) -> dict:
    """Retrieve the current weather report for a specified city."""
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

# Greeting Tool
def say_hello(name: Optional[str] = None) -> str:
    """Provides a simple greeting. If a name is provided, it will be used."""
    if name:
        greeting = f"Hello, {name}!"
        print(f"--- Tool: say_hello called with name: {name} ---")
    else:
        greeting = "Hello there!"
        print(f"--- Tool: say_hello called without a specific name (name_arg_value: {name} ---)")
    return greeting

# Goodbye Tool
def say_goodbye() -> str:
    """Provides a simple farewell message."""
    print(f"--- Tool: say_goodbye called ---")
    return "Goodbye! Have a great day."

print("Greeting and Farewell tools defined.")

# ---- Greeting Agent ----
greeting_agent = None
try:
    greeting_agent = Agent(
        model=LiteLlm(model=MODEL_GPT_40),
        name="greeting_agent",
        instruction=(
            "You are the Greeting Agent. Your ONLY task is to provide a friendly greeting to the user. "
            "Use the 'say_hello' tool to generate the greeting."
            "If the user provides their name, make sure to pass it to the tool. "
            "Do not engage in any other conversation or tasks."
        ),
        description="Handles simple greetings and hellos using the 'say_hello' tool.",
        tools=[say_hello],
    )
    print(f"Agent {greeting_agent.name} created using model {greeting_agent.model}.")
except Exception as e:
    print(f"Could not create Greeting agent. Error: {e}")

# ---- Farewell Agent ----
farewell_agent = None
try:
    farewell_agent = Agent(
        name="farewell_agent",
        model=LiteLlm(MODEL_GPT_40),
        description=(
            "You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message. "
            "Use the 'say_goodbye' tool when the user indicates they are leaving or ending the conversation."
        ),
        instruction="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
        tools=[say_goodbye],
    )
    print(f"Agent {farewell_agent.name} created using model {farewell_agent.model}.")
except Exception as e:
    print(f"Could not create Farewell agent. Error: {e}")

# Create root agent if sub-agents exist
if greeting_agent and farewell_agent and 'get_weather' in globals():
    root_agent_model = MODEL_GPT_40

    root_agent = Agent(
        name="weather_agent_v2",
        model=root_agent_model,
        description=(
            "The main coordinator agent. Handles weather requests and delegates greetings/farewells to specialists."
        ),
        instruction=(
            "You are the main Weather Agent coordinating a team. Your primary responsibility is to provide weather information. "
            "Use the 'get_weather' tool ONLY for specific weather requests. (e.g., 'weather in Dhaka'). "
            "You have specialized sub-agents: "
            "1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. "
            "2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. "
            "Analyze the user's query. If it's a greeting, delegate to 'greeting_agent'. If it's a farewell, delegate to 'farewell_agent'. "
            "If it's a weather request, handle it yourself using 'get_weather'."
        ),
        tools=[get_weather],
        sub_agents=[greeting_agent, farewell_agent]
    )
    print(f"Root Agent {root_agent.name} created using model {root_agent_model} with sub-agents: {[sa.name for sa in root_agent.sub_agents]}")

else:
    print("Cannot create root agent because one or more sub-agents failed to initialize or 'get_weather' tool is missing.")
    if not greeting_agent: print(" - Greeting Agent is missing.")
    if not farewell_agent: print(" - Farewell Agent is missing.")
    if 'get_weather' not in globals(): print(" - get_weather function is missing.")

root_agent_var_name = 'root_agent' if 'root_agent' in globals() else 'root_agent'
if root_agent_var_name in globals() and globals()[root_agent_var_name]:
    # Define the main async function for the conversation logic.
    async def run_team_conversation():
        print("\n--- Testing Agent Team Delegation ---")
        session_service = InMemorySessionService()
        APP_NAME = "weather_tutorial_agent_team"
        USER_ID = "user_1_agent_team"
        SESSION_ID = "session_001_agent_team"
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
        print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

        actual_root_agent = globals()[root_agent_var_name]
        runner_agent_team = Runner(
            agent=actual_root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        print(f"Runner created for agent '{actual_root_agent.name}'.")
else:
    print("⚠️ Root agent ('root_agent' or 'root_agent') not found. Cannot define run_team_conversation.")

# Main execution
if __name__ == "__main__":
    try:
        asyncio.run(run_team_conversation())
    except Exception as e:
        print(f"An error occurred: {e}")
