import tkinter as tk
from tkinter import *
from tkinter.ttk import Separator

from agent import get_model_response

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

questDict = {
    "Puzzle": "Puzzle",
    "Exploration": "Exploration",
    "Infiltration": "Infiltration",
    "Enquête": "Enquête",
    "Guerre": "Guerre",
    "Protection de Château": "Protection de Forteresse",
    "Attaque de Château": "Attaque de Château",
}

root = Tk()
envVar = tk.StringVar()
envVar.set(envDict["Arctique"])
questVar = tk.StringVar()
questVar.set(questDict["Puzzle"])

mainFrame = Frame(root)
leftFrame = Frame(mainFrame)

# Frame des environnements
envFrame = LabelFrame(leftFrame, text="Environnements")

for key, value in envDict.items():
    Radiobutton(envFrame, text=key, variable=envVar, value=value).pack(anchor="w")
envFrame.pack()

# Frame des quêtes
questFrame = LabelFrame(leftFrame, text="Quests")

for key, value in questDict.items():
    Radiobutton(questFrame, text=key, variable=questVar, value=value).pack(anchor="w")
questFrame.pack(side="left")
leftFrame.pack(side="left", fill="y")

# Middle frame with scroll
middleFrame = Frame(mainFrame, borderwidth=1, relief="solid")

# --- Scrollable system ---
canvas = Canvas(middleFrame)
scrollbar = Scrollbar(middleFrame, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

# Frame inside the canvas (where messages will be added)
messagesFrame = Frame(canvas)
canvas.create_window((0, 0), window=messagesFrame, anchor="nw")


def update_scroll_region(event=None):
    canvas.configure(scrollregion=canvas.bbox("all"))


messagesFrame.bind("<Configure>", update_scroll_region)
# -----------------------------------


# Initial system text
Label(
    messagesFrame,
    text="Hi! I am a DnD tool to help you build a quest for your next session as a Dungeon Master. What type of quest do you want me to create for you?",
    anchor="w",
    justify="left",
    wraplength=400
).pack(anchor="w")

# Prompt system
promptFrame = Frame(mainFrame)

promptText = Text(promptFrame, width=50, height=1)
promptText.pack(side="left", fill="x", expand=True)


def get_response(user_input, environment, quest_type):
    response = get_model_response(user_input, environment, quest_type)
    return response


def sendPrompt():
    userPromptText = promptText.get("1.0", "end").strip()
    promptText.delete(1.0, "end")

    # User message
    userPrompt = Label(messagesFrame, text=userPromptText, anchor="e", fg="blue", justify="right", wraplength=400)
    userPrompt.pack(anchor="e")

    # LLM response
    environment = envVar.get()
    quest_type = questVar.get()
    LLMResultText = get_response(userPromptText, environment, quest_type)
    LLMResult = Label(messagesFrame, text=LLMResultText, anchor="w", justify="left", wraplength=400)
    LLMResult.pack(anchor="w")

    # Auto-scroll to bottom
    canvas.update_idletasks()
    canvas.yview_moveto(1.0)  # scroll to bottom


sendPromptButton = Button(promptFrame, text="Enter", bg="blue", fg="white", command=sendPrompt)
sendPromptButton.pack(side="left")
promptFrame.pack(side="bottom", fill="x")
middleFrame.pack(side="left", fill="both", expand=True)
mainFrame.pack()

root.mainloop()
