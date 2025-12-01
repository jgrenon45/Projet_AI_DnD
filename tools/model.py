from pydantic import BaseModel, Field

class Quest(BaseModel):
    title: str = Field(description="The title of the quest.")
    description: str = Field(description="A detailed description of the quest.")
    difficulty: str = Field(description="The difficulty level of the quest (e.g., Easy, Medium, Hard).")
    rewards: list[str] = Field(description="A list of rewards for completing the quest.")
    experience_points: int = Field(description="The experience points awarded for completing the quest.")

class Player(BaseModel):
    name: str = Field(description="The name of the player.")
    level: int = Field(description="The current level of the player.")
    health: int = Field(description="The current health points of the player.")
    mana: int = Field(description="The current mana points of the player.")
    inventory: list[str] = Field(description="A list of items in the player's inventory.")
    quests: list[Quest] = Field(description="A list of quests assigned to the player.")

class VirtualAssistant(BaseModel):
    quest: Quest = Field(description="The main quest or objective the assistant is focused on.")
    current_time: str = Field(description="The current in-game time.")
    players: list[Player] = Field(description="A list of players interacting with the assistant.")
    