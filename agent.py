from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from tools.model import VirtualAssistant

# Define the model
model = OpenAIChatModel(
    model_name="qwen/qwen3-4b-thinking-2507",
    provider=OpenAIProvider(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")   
)

knowledge_agent = Agent(
    model,
    output_type=VirtualAssistant,
    output_retries=3,
    system_prompt="You are a knowledgeable virtual assistant in the fantasy role-playing game: Dungeons & Dragons." \
    "You help players by providing detailed information about quests, player stats, and game mechanics." \
    "Use the data provided to generate a comprehensive overview of the current game state."
    )

def get_model_response(user_input, environment, quest_type):
    return "t laid"