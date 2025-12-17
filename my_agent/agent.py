import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.genai import types
from typing import Optional, Dict, Any
import warnings
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Change to DEBUG for more detailed logs

# Filter warnings if necessary
warnings.filterwarnings("default")
warnings.filterwarnings("ignore")

print("Libraries imported successfully")

MODEL_GPT_40 = 'openai/gpt-4o'

session_service_stateful = InMemorySessionService()
print("New InMemorySessionService created for state demonstration.")

SESSION_ID_STATEFUL = "session_state-demo_001"
USER_ID_STATEFUL = "user_state_demo"

APP_NAME = "muliagent"

initial_state = {
    "user_preference_temperature_unit": "Celsius"
}

# Wrap the session creation in an async function
async def create_session():
    try:
        session_stateful = await session_service_stateful.create_session(
            app_name=APP_NAME,
            user_id=USER_ID_STATEFUL,
            session_id=SESSION_ID_STATEFUL,
            state=initial_state
        )
        print(f"Session {SESSION_ID_STATEFUL} created for user {USER_ID_STATEFUL}")

        retrieved_session = await session_service_stateful.get_session(app_name=APP_NAME, user_id=USER_ID_STATEFUL, session_id=SESSION_ID_STATEFUL)

        print("\n --- Initial Session State ---")
        if retrieved_session:
            print(retrieved_session.state)
        else:
            print("Error: Could not retrieve session.")
    except Exception as e:
        print(f"Error during session creation: {e}")

def bloack_paris_tool_guardrail(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
    """
    Checks if 'get_weather_stateful' is called for 'Chandpur'.
    If so, blocks the tool execution and returns a specific error dictionary.
    Otherwise, allows the tool call to proceed by returing None.
    """

    tool_name= tool.name
    agent_name = tool_context.agent_name
    print(f"--- Callback: block_chandpur_tool_guardrail running for tool {tool_name} in agent {agent_name}")
    print(f"--- Callback: Inspecting args: {args} ---")

    # --Guardrail Logic ---
    target_toll_name = "get_weather_stateful"
    blocked_city = "chandpur"

    # Check if it's the correct tool and the city argument matches the blocked city
    if tool_name == target_toll_name:
        city_argument = args.get("city", "")
        if city_argument and city_argument.lower() == blocked_city:
            print()


def block_keyword_guardrail(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """Inspects the latest user message for 'BLOCK'. If found, blocks the LLM call and returns a predefined LlmResponse, Otherwise, returns None to proceed."""
    
    # Ensure both arguments are passed properly
    if callback_context is None or llm_request is None:
        print("Error: callback_context or llm_request is None.")
        return None
    
    agent_name = callback_context.agent_name
    print(f"--- Callback: block_keyword_guardrail running for agent:  {agent_name} ---")

    last_user_message_text = ""
    
    # Check if the llm_request contains the necessary content
    if llm_request.contents:
        # Find the most recent message with role 'user'
        for content in reversed(llm_request.contents):
            if content.role == 'user' and content.parts:
                if content.parts[0].text:
                    last_user_message_text = content.parts[0].text
                    break
    
    print(f"--- Callback: Inspecting last user message: {last_user_message_text[:100]}")

    # --- Guardrail Logic ---
    keyword_to_block = 'BLOCK'
    if keyword_to_block in last_user_message_text.upper():
        print(f"--- Callback: Found {keyword_to_block}. Blocking LLM call! ---")
        callback_context.state["guardrail_block_keyword_triggered"] = True
        print(f"--- Callback: Set state 'guardrail_block_keyword_triggered': True ---")

        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"I cannot process this request because it contains the blocked keyword {keyword_to_block}")],
            )
        )
    else:
        # Keyword not found, allow the request to proceed to the LLM
        print(f"--- Callback: Keyword not found. Allowing LLM call for {agent_name}. ---")
        return None

print("block_keyword_guardrail function defined.")

# Weather Tool
def get_weather_stateful(city: str, tool_context: ToolContext) -> dict:
    """Retrieves weather, converts temp unit based on session state."""
    print(f"--- Tool: get_weather called for {city}")

    # --- Read preference from state ---
    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "Celsius")
    print(f" --- Tool: Reading state 'user_preference_temperature_unit': {preferred_unit}")
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

        if preferred_unit == "Fahrenheit":
            temp_value = (temp_c * 9/5) + 32
            temp_unit = "°F"
        else:
            temp_value = temp_c
            temp_unit = "°C"

        report = f"The weather in {city.capitalize()} is {condition} with a temperature of {temp_value:.0f} {temp_unit}."
        result = {
            "status": "success",
            "report": report
        }
        print(f"--- Tool: Generated report in {preferred_unit}. Result: {result} ---")

        tool_context.state["last_city_checked_stateful"] = city
        print(f" --- Tool: Update state 'last_city_checked_stateful': {city} ---")
        return result

    else:
        error_msg = f"Sorry, I don't have weather information for '{city}'."
        print(f"---- Tool: City {city} not found ----")
        return {
            "status": "error",
            "error_message": error_msg
        }

print("State-aware 'get_weather_stateful' tool defined.")

# Greeting Tool
def say_hello(name: Optional[str] = None) -> str:
    """Provides a simple greeting. If a name is provided, it will be used."""
    if name:
        greeting = f"Hello, {name}!"
        print(f"--- Tool: say_hello called with name: {name} ---")
    else:
        greeting = "Hello there!"
        print(f"--- Tool: say_hello called without a specific name (name_arg_value: {name}) ---")
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

# ---- Redefine Farewell Agent ----
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

# --- Define the Root Agent with the Callback ---
root_agent = None
runner_root_model_guardrail = None 

# Create root agent if sub-agents exist
if greeting_agent and farewell_agent and 'get_weather_stateful' in globals() and 'block_keyword_guardrail' in globals():
    root_agent_model = MODEL_GPT_40

    root_agent = Agent(
        name="weather_agent_v5_model_guardrail",
        model=root_agent_model,
        description=(
            "Main agent: Handles weather, delegates greetings/farewells, includes input keyword guardrail."
        ),
        instruction=(
            "You are the main Weather Agent. Provide weather using 'get_weather_stateful'. "
            "Delegate simple greetings to 'greeting_agent' and farewells to 'farewell_agent'. "
            "Handle only weather requests, greetings, and farewells."
        ),
        tools=[get_weather_stateful],
        sub_agents=[greeting_agent, farewell_agent],
        output_key="last_weather_report",
        before_model_callback=block_keyword_guardrail   
    )
    print(f"✅ Root Agent '{root_agent.name}' created with before_model_callback.")

    if 'session_service_stateful' in globals():
        runner_root_model_guardrail = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service_stateful 
        )
        print(f"✅ Runner created for guardrail agent '{runner_root_model_guardrail.agent.name}', using stateful session service.")
    else:
        print("❌ Cannot create runner. 'session_service_stateful' from Step 4 is missing.")

else:
    print("❌ Cannot create root agent with model guardrail. One or more prerequisites are missing or failed initialization:")
    if not greeting_agent: print("   - Greeting Agent")
    if not farewell_agent: print("   - Farewell Agent")
    if 'get_weather_stateful' not in globals(): print("   - 'get_weather_stateful' tool")
    if 'block_keyword_guardrail' not in globals(): print("   - 'block_keyword_guardrail' callback")

# Main execution
if __name__ == "__main__":
    try:
        asyncio.run(create_session())
    except Exception as e:
        print(f"An error occurred: {e}")
