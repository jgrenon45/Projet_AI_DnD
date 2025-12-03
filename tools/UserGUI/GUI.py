import tkinter as tk
from tkinter import *
from tkinter.ttk import Separator

from cohere import environment

root = Tk()
envVar = tk.StringVar()
questVar = tk.StringVar()

mainFrame = Frame(root)
leftFrame = Frame(mainFrame)

# Frame des environnements
envFrame = LabelFrame(leftFrame, text="Environnements")
envDict = {
    "Arctique": "Arctique",
    "Côte": "Côte",
    "Désert": "Désert",
    "Forêt": "Forêt",
    "Prairie": "Prairie",
    "Montagne": "Montagne",
    "Marais": "Marais",
    "Profondeurs": "Profondeurs",
}

for key, value in envDict.items():
    Radiobutton(envFrame, text=key, variable=envVar, value=value).pack(anchor="w")
envFrame.pack()

# Frame des quêtes
questFrame = LabelFrame(leftFrame, text="Quests")
questDict = {
    "Puzzle": "Puzzle",
    "Exploration": "Exploration",
    "Infiltration": "Infiltration",
    "Enquête": "Enquête",
    "Guerre": "Guerre",
    "Protection de Château": "Protection de Forteresse",
    "Attaque de Château": "Attaque de Château",
}

for key, value in questDict.items():
    Radiobutton(questFrame, text=key, variable=questVar, value=value).pack(anchor="w")
questFrame.pack(side="left")
leftFrame.pack(side="left")

# Middle frame where the results of the LLM will be displayed
middleFrame = Frame(mainFrame, borderwidth=1, relief="solid")
# resultFrame = Scrollbar(middleFrame)

Label(middleFrame,
      text="Hi! I am a Dnd tool to help you build a quest for your next session as a Dongeon Master. What type of quest do you want me to create for you?").pack(
    anchor="w")

# resultFrame.pack()

promptFrame = Frame(middleFrame)
promptText = Text(promptFrame, width=50, height=1)
promptText.pack(side="left")

def get_response(user_input, environment, quest_type):
    response = "t laid"
    return response

def sendPrompt():
    userPromptText = promptText.get("1.0", "end-1c")
    userPrompt = Label(middleFrame, text=userPromptText)
    userPrompt.pack(anchor="e")
    promptText.delete(1.0, "end")

    environment = envVar.get()
    quest_type = questVar.get()
    LLMResultText = get_response(userPromptText, environment, quest_type)
    LLMResult = Label(middleFrame, text=LLMResultText)
    LLMResult.pack(anchor="w")

sendPromptButton = Button(promptFrame, text="Enter", bg="blue", fg="white", command=sendPrompt)
sendPromptButton.pack(side="left")
promptFrame.pack(side="bottom")
middleFrame.pack(side="left", fill="y", expand=True)
mainFrame.pack()

root.mainloop()
