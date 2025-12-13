import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
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

session_service_stateful = InMemorySessionService()
print("New InMemorySessionService created for sate demonstration.")

SESSION_ID_STATEFUL = "session_state-demo_001"
USER_ID_STATEFUL = "user_state_demo"

APP_NAME = "muliagent"

initial_state = {
    "user_preference_temperature_unit": "Celsius"
}
async def create_session():
    session_stateful = await session_service_stateful.create_session(
        app_name= APP_NAME,
        user_id=USER_ID_STATEFUL,
        session_id=SESSION_ID_STATEFUL,
        state=initial_state
    )
    print(f"Session {SESSION_ID_STATEFUL} created for user {USER_ID_STATEFUL}")

    retrieved_session = await session_service_stateful.get_session(app_name=APP_NAME, user_id=USER_ID_STATEFUL, session_id= SESSION_ID_STATEFUL)

    print("\n --- Initial Session State ---")
    if retrieved_session:
        print(retrieved_session.state)
    else:
        print("Error: Could not retrieve session.")

# Weather Tool
def get_weather_stateful(city: str, tool_context: ToolContext) -> dict:
    """Retrieves weather, conberts temp unit based on session state."""
    print(f"--- Tool: get_weather called for {city}")

    #--- Read prefernce form state ---
    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "Celsius")
    print(f" ---Tool: Reading state 'user_preference_temperature_unit': {preferred_unit}")
    city_normalized = city.lower().replace(" ", "")

    # Mock weather data
    mock_weather_data = {
        "dhaka": {"temp_c": 25, "condition": "sunny"},
        "rangpur": {"temp_c": 15, "condition": "cloudy"},
        "chandpur": {"temp_c": 18, "condition": "light rain"},
    }

    if city_normalized in mock_weather_data:
        data = mock_weather_data[city_normalized]
        temp_c = data['temp_c']
        condition = data["condition"]

        if preferred_unit == "Fahrenheir":
            temp_value = (temp_c * 9/5) + 32
            temp_unit = "°F"
        else:
            temp_value = temp_c
            temp_unit = "°C"

        report = f"The weather in {city.capitalize} is {condition} with a temperature of {temp_value:.0f} {temp_unit}."
        result = {
            "status": "success",
            "report": report
        }
        print(f"--- Tool: Generated report in {preferred_unit}. Result: {result} ---")

        tool_context.state["last_city_checked_statefull"] = city
        print(f" ---Tool: Update sate 'last_city_checked_stateful': {city} ----")
        return result

    else:
        error_msg = f"Sorry, I don't have weather information for '{city}'."
        print(f"----Tool: City {city} not found----")
        return {
            "status": "error",
            "error_message": error_msg
        }
    
print("State-awre 'get_weather_stateful' tool defined.")

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

# ---- Redefine Greeting Agent ----
greeting_agent = None
try:
    greeting_agent = Agent(
        model=LiteLlm(model=MODEL_GPT_40),
        name="greeting_agent",
        instruction=(
            "You are the Greeting Agent. Your ONLY task is to provide a friendly greeting using the 'say_hello' tool. Do nothing else."
        ),
        description="Handles simple greetings and hellos using the 'say_hello' tool.",
        tools=[say_hello],
    )
    print(f"Agent {greeting_agent.name} created using model {greeting_agent.model}.")
except Exception as e:
    print(f"Could not create Greeting agent. Error: {e}")

# ---- Redefine  Farewell Agent ----
farewell_agent = None
try:
    farewell_agent = Agent(
        name="farewell_agent",
        model=LiteLlm(MODEL_GPT_40),
        description=(
            "You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message using the 'say_goodbye' tool. Do not perform any other actions."
        ),
        instruction="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
        tools=[say_goodbye],
    )
    print(f"Agent {farewell_agent.name} created using model {farewell_agent.model}.")
except Exception as e:
    print(f"Could not create Farewell agent. Error: {e}")

# --- Define the Updated Root Agent ---
root_agent = None
runner_root_stateful = None 

# Create root agent if sub-agents exist
if greeting_agent and farewell_agent and 'get_weather_stateful' in globals():
    root_agent_model = MODEL_GPT_40

    root_agent = Agent(
        name="weather_agent_v4_stateful",
        model=root_agent_model,
        description=(
            "Main agent: Provides weather (state-aware unit), delegates greetings/farewells, saves report to state."
        ),
        instruction=(
            "You are the main Weather Agent. Your job is to provide weather using 'get_weather_stateful'. "
            "The tool will format the temperature based on user preference stored in state. "
            "Delegate simple greetings to 'greeting_agent' and farewells to 'farewell_agent'. "
            "Handle only weather requests, greetings, and farewells."
        ),
        tools=[get_weather_stateful],
        sub_agents=[greeting_agent, farewell_agent],
        output_key= "last_weather_report"
    )
    print(f"Root Agent {root_agent.name} created using model {root_agent_model} with sub-agents: {[sa.name for sa in root_agent.sub_agents]}")

    runner_root_staterul = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service= session_service_stateful
    )

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
        asyncio.run(create_session())
    except Exception as e:
        print(f"An error occurred: {e}")
