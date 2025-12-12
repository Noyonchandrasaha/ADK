import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm


def get_weather(city: str)-> dict:
    if city.lower() == 'dhaka':
        return{
            "status": "success",
            "report": (
                "The weather in Dhaka is sunny with a temperature of 25 degress"
                "Celsius (77 degrees Farenheit.)"
            ),
        }
    else:
        return{
            "status":"error",
            "error_message": f"Weather information for {city} is not available."
        }
    

def get_current_time(city: str) -> dict:
    if city.lower() == "dhaka":
        tz_identifier = "Asia/Dhaka"
    else:
        return{
            "status": "error",
            "error_message": (
                f"Sorry, I don't have timezone information for {city}"
            )
        }
    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = (
        f"The current time in  {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}"
    )
    return{
        "status": "success",
        "report": report,
    }

root_agent = Agent(
    model=LiteLlm(
        model="openai/gpt-4o",        # OpenAI model
        temperature=0.1
    ),
    name='root_agent',
    description=(
        "Agents to answer questions about the time and weather in a city."
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about the time and weather in a city."
    ),
    tools=[get_weather, get_current_time],
)
