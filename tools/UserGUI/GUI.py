"""
Retro 8-bit D&D Assistant GUI - Complete Working Version
Interface graphique principale pour l'assistant D&D

Fonctionnalites:
- Chat avec IA pour repondre aux questions D&D
- Recherche de monstres dans la base de donnees
- Recherche de regles via systeme RAG
- Tracker d'initiative pour gerer les combats
- Generateur de donjons via IA
- Outils du maitre (des, rencontres, PNJ, etc.)

Theme visuel: Retro 8-bit avec palette orange/noir/rouge/or
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import sys
import json
import random
from pathlib import Path
from datetime import datetime

# Ajouter le chemin parent pour importer les modules tools
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from tools.model import DnDAssistantModel  # Interface avec LLM (LM Studio/Ollama)
    from tools.rag import RAGSystem  # Systeme de recherche dans les PDFs
    from tools.db import MonsterDatabase  # Base de donnees des monstres
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required files are present")


# ======================== HELPER CLASSES ========================

class InitiativeTracker:
    """
    Gere l'ordre d'initiative pendant les combats
    
    Attributs:
        creatures (list): Liste des creatures en combat avec leur initiative
        current_index (int): Index de la creature dont c'est le tour
        round_number (int): Numero du round actuel
    """
    def __init__(self):
        self.creatures = []  # Liste vide au debut
        self.current_index = 0  # Commence au premier
        self.round_number = 1  # Round 1 au debut
    
    def add(self, name, init):
        """
        Ajoute une creature au tracker d'initiative
        
        Args:
            name (str): Nom de la creature
            init (int): Valeur d'initiative (0-40)
            
        Returns:
            bool: True si ajoute avec succes, False si initiative invalide
        """
        # Valider que l'initiative est entre 0 et 40
        if 0 <= init <= 40:
            # Ajouter la creature a la liste
            self.creatures.append({'name': name, 'initiative': init})
            # Trier par initiative decroissante (plus haute initiative en premier)
            self.creatures.sort(key=lambda x: x['initiative'], reverse=True)
            return True
        return False
    
    def next_turn(self):
        """
        Passe au tour suivant dans l'ordre d'initiative
        Incremente le numero de round quand on revient au debut
        """
        if self.creatures:
            # Passer a la creature suivante (modulo pour boucler)
            self.current_index = (self.current_index + 1) % len(self.creatures)
            # Si on revient au debut, incrementer le round
            if self.current_index == 0:
                self.round_number += 1
    
    def get_current(self):
        """Retourne la creature dont c'est actuellement le tour"""
        return self.creatures[self.current_index] if self.creatures else None
    
    def clear(self):
        """Reinitialise completement le tracker"""
        self.creatures, self.current_index, self.round_number = [], 0, 1
    
    def to_dict(self):
        """Convertit l'etat en dictionnaire pour sauvegarde"""
        return {'creatures': self.creatures, 'current': self.current_index, 'round': self.round_number}
    
    def from_dict(self, data):
        """Restaure l'etat depuis un dictionnaire"""
        self.creatures = data.get('creatures', [])
        self.current_index = data.get('current', 0)
        self.round_number = data.get('round', 1)


class DungeonGenerator:
    """
    Generateur de donjons qui utilise l'IA pour creer des descriptions
    
    Note: La generation reelle est faite par l'IA via le chat.
    Cette classe prepare juste les parametres.
    """
    THEMES = ['undead', 'goblin', 'dragon', 'elemental', 'construct']
    
    def __init__(self, model=None):
        self.model = model  # Reference au modele LLM (optionnel)
    
    def generate(self, rooms=10, difficulty='medium', theme='undead'):
        """
        Prepare les parametres pour la generation par IA
        
        Args:
            rooms (int): Nombre de salles desirees
            difficulty (str): Niveau de difficulte
            theme (str): Theme du donjon
            
        Returns:
            dict: Parametres du donjon (sera traite par l'IA)
        """
        return {
            'name': f"The {theme.title()} Lair",
            'difficulty': difficulty,
            'theme': theme,
            'rooms': rooms,
            'status': 'use_ai'  # Indique que l'IA doit generer
        }


class SessionManager:
    """
    Gere la sauvegarde et le chargement des sessions de jeu
    Sauvegarde en format JSON dans data/sessions/
    """
    def __init__(self, dir="data/sessions"):
        self.dir = Path(dir)
        # Creer le dossier s'il n'existe pas
        self.dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, data):
        """
        Sauvegarde une session au format JSON
        
        Args:
            data (dict): Donnees a sauvegarder (chat, initiative, donjon, etc.)
            
        Returns:
            str: Chemin du fichier sauvegarde
        """
        # Nom de fichier avec timestamp
        file = self.dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        # Ajouter le timestamp aux donnees
        data['timestamp'] = datetime.now().isoformat()
        # Ecrire en JSON avec indentation pour lisibilite
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(file)
    
    def load(self, path):
        """
        Charge une session depuis un fichier JSON
        
        Args:
            path (str): Chemin du fichier a charger
            
        Returns:
            dict: Donnees de la session
        """
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


# ======================== MAIN GUI CLASS ========================

class DnDAssistantGUI:
    """
    Classe principale de l'interface graphique
    
    Gere tous les onglets et fonctionnalites:
    - Chat avec l'IA
    - Recherche de monstres
    - Recherche de regles
    - Outils du maitre
    - Tracker d'initiative
    - Generateur de donjons
    
    Attributs:
        root: Fenetre principale CustomTkinter
        model: Interface avec le modele LLM
        rag: Systeme de recherche RAG
        monster_db: Base de donnees des monstres
        init_tracker: Tracker d'initiative
        dungeon_gen: Generateur de donjons
        session_mgr: Gestionnaire de sessions
        chat_history: Historique des messages du chat
        colors: Palette de couleurs du theme
    """
    def __init__(self):
        # Initialisation des composants backend
        self.model = None  # Sera initialise plus tard
        self.rag = None
        self.monster_db = None
        self.init_tracker = InitiativeTracker()
        self.dungeon_gen = DungeonGenerator()
        self.session_mgr = SessionManager()
        self.chat_history = []  # Historique vide au debut
        self.current_dungeon = None  # Pas de donjon au debut
        
        # Configuration et creation de l'interface
        self.setup_window()
        self.create_widgets()
        
        # Initialiser les systemes backend apres 100ms (pour que la GUI soit prete)
        self.root.after(100, self.initialize_systems)
    
    def setup_window(self):
        """
        Configure la fenetre principale
        Definit les couleurs du theme et les parametres de base
        """
        ctk.set_appearance_mode("dark")  # Mode sombre
        self.root = ctk.CTk()
        self.root.title("Le Grimoire du Maitre du Donjon")
        self.root.geometry("1400x900")  # Taille de la fenetre
        
        # Palette de couleurs retro 8-bit
        self.colors = {
            'bg_dark': '#1a0a00',    # Fond tres sombre (noir-brun)
            'bg_med': '#2d1810',     # Fond moyen (brun sombre)
            'bg_light': '#4a2511',   # Fond clair (brun)
            'orange': '#FF8C00',     # Orange vif (boutons) 
            'red': '#8B0000',
            'text': '#FFB366', 
            'gold': '#DAA520'  # Goldenrod - couleur or
        }
        self.root.configure(fg_color=self.colors['bg_dark'])
    
    def create_widgets(self):
        # Header
        hdr = ctk.CTkFrame(self.root, fg_color=self.colors['red'], height=70)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="LE GRIMOIRE DU MAITRE DU DONJON", font=("Courier", 26, "bold"),
                    text_color=self.colors['gold']).pack(pady=5)
        ctk.CTkLabel(hdr, text="Assistant IA pour D&D 5e", font=("Courier", 9),
                    text_color=self.colors['orange']).pack()
        
        # Toolbar
        toolbar = ctk.CTkFrame(self.root, fg_color=self.colors['bg_med'], height=45)
        toolbar.pack(fill="x", padx=5, pady=2)
        
        self.status = ctk.CTkLabel(toolbar, text="Initialisation...", font=("Courier", 9),
                                  text_color=self.colors['orange'])
        self.status.pack(side="right", padx=10)
        
        # Tabs
        self.tabs = ctk.CTkTabview(
            self.root, 
            fg_color=self.colors['bg_dark'],
            segmented_button_fg_color=self.colors['bg_med'],
            segmented_button_selected_color=self.colors['orange'],
            segmented_button_selected_hover_color=self.colors['orange'],
            text_color=self.colors['text']
        )
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tab_chat = self.tabs.add("Chat")
        self.tab_monsters = self.tabs.add("Monstres")
        self.tab_rules = self.tabs.add("Regles")
        self.tab_tools = self.tabs.add("Outils")
        self.tab_init = self.tabs.add("Initiative")
        self.tab_dung = self.tabs.add("Donjon")
        
        self.setup_chat()
        self.setup_monsters()
        self.setup_rules()
        self.setup_tools()
        self.setup_initiative()
        self.setup_dungeon()
        
        # Footer
        ftr = ctk.CTkFrame(self.root, fg_color=self.colors['red'], height=25)
        ftr.pack(fill="x")
        ctk.CTkLabel(ftr, text="Powered by LM Studio & Ollama", font=("Courier", 8, "bold"),
                    text_color=self.colors['gold']).pack(pady=3)
    
    def setup_chat(self):
        self.chat_box = ctk.CTkTextbox(
            self.tab_chat, 
            font=("Courier", 11),
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text'],
            wrap="word"
        )
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.chat_box.insert("end", "Bienvenue, Maitre du Donjon!\n\nPose tes questions sur D&D 5e.\n\n")
        
        inp_frame = ctk.CTkFrame(self.tab_chat, fg_color=self.colors['bg_med'])
        inp_frame.pack(fill="x", padx=10, pady=5)
        
        self.chat_input = ctk.CTkEntry(
            inp_frame, 
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text'], 
            height=35
        )
        self.chat_input.pack(side="left", fill="x", expand=True, padx=5)
        self.chat_input.bind("<Return>", lambda e: self.send_msg())
        
        self.create_button(inp_frame, "ENVOYER", self.send_msg, 100).pack(side="right", padx=5)
        
        # Quick actions
        actions_frame = ctk.CTkFrame(self.tab_chat, fg_color=self.colors['bg_med'])
        actions_frame.pack(fill="x", padx=10, pady=5)
        
        self.create_button(actions_frame, "Lancer Des", 
                self.dice_roller_prompt, 130).pack(side="left", padx=3, pady=5)
        self.create_button(actions_frame, "Generer Rencontre", 
                self.encounter_generator_prompt, 180).pack(side="left", padx=3, pady=5)
        self.create_button(actions_frame, "Creer PNJ", 
                self.npc_generator_prompt, 130).pack(side="left", padx=3, pady=5)
        self.create_button(actions_frame, "Aide Combat", 
                lambda: self.quick_action("Explique les regles de combat"), 140).pack(side="left", padx=3, pady=5)
    
    def setup_monsters(self):
        search_frame = ctk.CTkFrame(self.tab_monsters, fg_color=self.colors['bg_med'])
        search_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            search_frame, 
            text="BESTIAIRE", 
            font=("Courier", 18, "bold"),
            text_color=self.colors['gold']
        ).pack(pady=5)
        
        search_input_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_input_frame.pack(fill="x", padx=5, pady=5)
        
        self.monster_search = ctk.CTkEntry(
            search_input_frame, 
            placeholder_text="Chercher monstre...",
            font=("Courier", 12), 
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text']
        )
        self.monster_search.pack(side="left", fill="x", expand=True, padx=5)
        
        self.create_button(search_input_frame, "CHERCHER", self.search_monster, 120).pack(side="right", padx=5)
        
        self.monster_display = ctk.CTkTextbox(
            self.tab_monsters, 
            font=("Courier", 11),
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text']
        )
        self.monster_display.pack(fill="both", expand=True, padx=10, pady=10)
    
    def setup_rules(self):
        search_frame = ctk.CTkFrame(self.tab_rules, fg_color=self.colors['bg_med'])
        search_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            search_frame, 
            text="REGLES D&D 5e", 
            font=("Courier", 18, "bold"),
            text_color=self.colors['gold']
        ).pack(pady=5)
        
        search_input_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_input_frame.pack(fill="x", padx=5, pady=5)
        
        self.rule_search = ctk.CTkEntry(
            search_input_frame, 
            placeholder_text="Chercher regle...",
            font=("Courier", 12), 
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text']
        )
        self.rule_search.pack(side="left", fill="x", expand=True, padx=5)
        
        self.create_button(search_input_frame, "CHERCHER", self.search_rules, 120).pack(side="right", padx=5)
        
        self.rules_display = ctk.CTkTextbox(
            self.tab_rules, 
            font=("Courier", 11),
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text']
        )
        self.rules_display.pack(fill="both", expand=True, padx=10, pady=10)
    
    def setup_tools(self):
        tools_frame = ctk.CTkFrame(self.tab_tools, fg_color=self.colors['bg_med'])
        tools_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            tools_frame, 
            text="OUTILS DU MAITRE", 
            font=("Courier", 18, "bold"),
            text_color=self.colors['gold']
        ).pack(pady=10)
        
        tools = [
            ("Lanceur de Des", self.dice_roller),
            ("Generateur Rencontre", self.encounter_generator),
            ("Generateur PNJ", self.npc_generator),
            ("Generateur Donjon", self.dungeon_generator_tool),
            ("Calculateur XP", self.xp_calculator),
            ("Tracker Initiative", self.initiative_tracker_tool)
        ]
        
        for text, command in tools:
            self.create_button(tools_frame, text, command, 300, 50).pack(pady=5)
    
    def setup_initiative(self):
        form = ctk.CTkFrame(self.tab_init, fg_color=self.colors['bg_med'])
        form.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            form, 
            text="INITIATIVE TRACKER", 
            font=("Courier", 16, "bold"),
            text_color=self.colors['gold']
        ).pack(pady=5)
        
        ent = ctk.CTkFrame(form, fg_color="transparent")
        ent.pack(pady=5)
        
        self.i_name = self.create_entry(ent, "Nom:", 0, 0, 200)
        self.i_init = self.create_entry(ent, "Initiative (0-40):", 0, 2, 80)
        self.create_button(ent, "Ajouter", self.add_init, 100).grid(row=0, column=4, padx=10)
        
        ctrl = ctk.CTkFrame(form, fg_color="transparent")
        ctrl.pack(pady=5)
        self.create_button(ctrl, "Lancer Init (1d20)", self.roll_init, 150).pack(side="left", padx=3)
        self.create_button(ctrl, "Tour Suivant", self.next_turn, 120).pack(side="left", padx=3)
        self.create_button(ctrl, "Effacer", self.clear_init, 100).pack(side="left", padx=3)
        
        self.init_box = ctk.CTkTextbox(
            self.tab_init, 
            font=("Courier", 12),
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text']
        )
        self.init_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.update_init()
    
    def setup_dungeon(self):
        ctrl = ctk.CTkFrame(self.tab_dung, fg_color=self.colors['bg_med'])
        ctrl.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            ctrl, 
            text="GENERATEUR DE DONJON IA", 
            font=("Courier", 16, "bold"),
            text_color=self.colors['gold']
        ).pack(pady=5)
        
        ctk.CTkLabel(
            ctrl,
            text="Demande a l'IA de generer un donjon dans l'onglet Chat!",
            font=("Courier", 10),
            text_color=self.colors['text']
        ).pack(pady=5)
        
        opts = ctk.CTkFrame(ctrl, fg_color="transparent")
        opts.pack(pady=5)
        
        self.d_rooms = self.create_entry(opts, "Salles:", 0, 0, 50)
        self.d_rooms.insert(0, "5")
        
        ctk.CTkLabel(opts, text="Difficulte:", text_color=self.colors['text']).grid(row=0, column=2, padx=5)
        self.d_diff = ctk.CTkOptionMenu(
            opts, 
            values=["easy", "medium", "hard"], 
            fg_color=self.colors['orange'], 
            button_color=self.colors['orange'],
            button_hover_color=self.colors['red'],
            width=90
        )
        self.d_diff.set("medium")
        self.d_diff.grid(row=0, column=3, padx=5)
        
        ctk.CTkLabel(opts, text="Theme:", text_color=self.colors['text']).grid(row=0, column=4, padx=5)
        self.d_theme = ctk.CTkOptionMenu(
            opts, 
            values=DungeonGenerator.THEMES,
            fg_color=self.colors['orange'], 
            button_color=self.colors['orange'],
            button_hover_color=self.colors['red'],
            width=100
        )
        self.d_theme.set("undead")
        self.d_theme.grid(row=0, column=5, padx=5)
        
        self.create_button(opts, "Demander a l'IA", self.gen_dungeon, 150).grid(row=0, column=6, padx=10)
        
        self.dung_box = ctk.CTkTextbox(
            self.tab_dung, 
            font=("Courier", 10),
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text']
        )
        self.dung_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.dung_box.insert("end", "Les donjons seront generes par l'IA.\nUtilise les parametres ci-dessus et clique sur 'Demander a l'IA'.\n\nExemple de requete:\n'Genere un donjon de 5 salles, difficulte medium, theme undead'\n")
    
    def setup_sessions(self):
        pass  # Removed
    
    # Helper methods
    def create_button(self, parent, text, cmd, w, h=None):
        if h is None:
            return ctk.CTkButton(
                parent, text=text, command=cmd, width=w,
                fg_color=self.colors['orange'], hover_color=self.colors['red'],
                text_color="#000000", font=("Courier", 11, "bold"),
                corner_radius=0, border_width=3, border_color="#8B4513"
            )
        else:
            return ctk.CTkButton(
                parent, text=text, command=cmd, width=w, height=h,
                fg_color=self.colors['orange'], hover_color=self.colors['red'],
                text_color="#000000", font=("Courier", 11, "bold"),
                corner_radius=0, border_width=3, border_color="#8B4513"
            )
    
    def create_entry(self, parent, label, row, col, w):
        ctk.CTkLabel(parent, text=label, text_color=self.colors['text']).grid(row=row, column=col, padx=5)
        e = ctk.CTkEntry(parent, width=w, fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        e.grid(row=row, column=col+1, padx=5)
        return e
    
    def update_status(self, msg):
        self.status.configure(text=msg)
        self.root.update()
    
    # System initialization
    def initialize_systems(self):
        self.update_status("Chargement...")
        try:
            self.model = DnDAssistantModel(use_ollama=False, model_name="qwen3-4b-thinking")
            
            if not self.model.is_available():
                self.model = DnDAssistantModel(use_ollama=True, model_name="llama2")
            
            self.rag = RAGSystem()
            self.monster_db = MonsterDatabase()
            
            if self.rag.collection.count() == 0:
                self.update_status("Indexation PDFs...")
                self.rag.index_documents()
            
            status_msg = f"{self.model.backend} Pret!" if self.model.is_available() else "Pas de LLM"
            self.update_status(status_msg)
        except Exception as e:
            self.update_status(f"Erreur: {str(e)}")
            print(f"Erreur initialisation: {str(e)}")
    
    # Chat functions
    def send_msg(self):
        msg = self.chat_input.get().strip()
        if not msg: 
            return
        
        self.chat_box.insert("end", f"\nVous: {msg}\n")
        self.chat_input.delete(0, "end")
        self.chat_history.append({'role': 'user', 'content': msg})
        self.chat_box.see("end")
        
        self.update_status("Reflexion...")
        self.root.update()
        
        try:
            ctx = self.rag.get_context_for_query(msg) if self.rag else ""
            resp = self.model.generate_dm_response(msg, ctx) if self.model and self.model.is_available() \
                   else "LLM non disponible. Verifiez que LM Studio ou Ollama est lance."
            
            self.chat_box.insert("end", f"IA: {resp}\n")
            self.chat_history.append({'role': 'assistant', 'content': resp})
            self.chat_box.see("end")
            self.update_status("Termine")
        except Exception as e:
            self.chat_box.insert("end", f"Erreur: {str(e)}\n")
            self.update_status("Erreur")
            print(f"Erreur chat: {str(e)}")
    
    def quick_action(self, text):
        self.chat_input.delete(0, "end")
        self.chat_input.insert(0, text)
        self.send_msg()
    
    # Monster search
    def search_monster(self):
        query = self.monster_search.get().strip()
        if not query:
            return
        
        self.update_status("Recherche monstre...")
        
        try:
            monster = self.monster_db.search_monster(query)
            
            self.monster_display.delete("1.0", "end")
            
            if monster:
                # Format the display nicely
                name = monster.get('name', 'Inconnu')
                self.monster_display.insert("end", f"{'='*60}\n", "title")
                self.monster_display.insert("end", f"{name.upper()}\n", "title")
                self.monster_display.insert("end", f"{'='*60}\n\n", "title")
                
                # Key stats first
                if 'size' in monster and monster['size'] != 'nan':
                    self.monster_display.insert("end", f"Taille: {monster['size']}\n")
                if 'type' in monster and monster['type'] != 'nan':
                    self.monster_display.insert("end", f"Type: {monster['type']}\n")
                if 'alignment' in monster and monster['alignment'] != 'nan':
                    self.monster_display.insert("end", f"Alignement: {monster['alignment']}\n")
                
                self.monster_display.insert("end", "\n")
                
                # Combat stats
                if 'cr' in monster:
                    self.monster_display.insert("end", f"CR: {monster['cr']}\n")
                if 'ac' in monster:
                    self.monster_display.insert("end", f"AC: {monster['ac']}\n")
                if 'hp' in monster:
                    self.monster_display.insert("end", f"HP: {monster['hp']}\n")
                if 'initiative' in monster:
                    self.monster_display.insert("end", f"Initiative: +{monster['initiative']}\n")
                if 'speed' in monster and monster['speed'] != 'nan':
                    self.monster_display.insert("end", f"Vitesse: {monster['speed']}\n")
                
                self.monster_display.insert("end", "\n")
                
                # Ability scores
                self.monster_display.insert("end", "CARACTERISTIQUES:\n")
                if 'str' in monster:
                    self.monster_display.insert("end", f"  FOR: {monster['str']}\n")
                if 'dex' in monster:
                    self.monster_display.insert("end", f"  DEX: {monster['dex']}\n")
                if 'con' in monster:
                    self.monster_display.insert("end", f"  CON: {monster['con']}\n")
                if 'int' in monster:
                    self.monster_display.insert("end", f"  INT: {monster['int']}\n")
                if 'wis' in monster:
                    self.monster_display.insert("end", f"  SAG: {monster['wis']}\n")
                if 'cha' in monster:
                    self.monster_display.insert("end", f"  CHA: {monster['cha']}\n")
                
                self.monster_display.insert("end", "\n")
                
                # Skills and special abilities
                if 'skills' in monster and monster['skills'] != 'nan':
                    self.monster_display.insert("end", f"Competences: {monster['skills']}\n")
                if 'senses' in monster and monster['senses'] != 'nan':
                    self.monster_display.insert("end", f"Sens: {monster['senses']}\n")
                if 'languages' in monster and monster['languages'] != 'nan':
                    self.monster_display.insert("end", f"Langues: {monster['languages']}\n")
                
                self.monster_display.insert("end", "\n")
                
                # Resistances/Immunities
                if 'resistances' in monster and monster['resistances'] != 'nan':
                    self.monster_display.insert("end", f"Resistances: {monster['resistances']}\n")
                if 'immunities' in monster and monster['immunities'] != 'nan':
                    self.monster_display.insert("end", f"Immunites: {monster['immunities']}\n")
                if 'vulnerabilities' in monster and monster['vulnerabilities'] != 'nan':
                    self.monster_display.insert("end", f"Vulnerabilites: {monster['vulnerabilities']}\n")
                
                # Full text if available (contains all abilities and actions)
                if 'full_text' in monster and monster['full_text'] != 'nan':
                    self.monster_display.insert("end", f"\n{'='*60}\n")
                    self.monster_display.insert("end", "DETAILS COMPLETS:\n")
                    self.monster_display.insert("end", f"{'='*60}\n\n")
                    self.monster_display.insert("end", str(monster['full_text']))
                
            else:
                self.monster_display.insert("end", "Aucun monstre trouve.\n")
                self.monster_display.insert("end", "\nEssayez un autre nom ou verifiez l'orthographe.")
            
            self.update_status("Recherche terminee")
        except Exception as e:
            self.monster_display.delete("1.0", "end")
            self.monster_display.insert("end", f"Erreur: {str(e)}\n")
            self.update_status("Erreur")
            print(f"Erreur recherche monstre: {str(e)}")
    
    # Rules search
    def search_rules(self):
        query = self.rule_search.get().strip()
        if not query:
            return
        
        self.update_status("Recherche regles...")
        
        try:
            results = self.rag.search_rule(query) if self.rag else "RAG non disponible"
            
            self.rules_display.delete("1.0", "end")
            self.rules_display.insert("end", results)
            
            self.update_status("Recherche terminee")
        except Exception as e:
            self.rules_display.delete("1.0", "end")
            self.rules_display.insert("end", f"Erreur: {str(e)}\n")
            self.update_status("Erreur")
            print(f"Erreur recherche regles: {str(e)}")
    
    # Tool functions
    def dice_roller(self):
        self.dice_roller_prompt()
    
    def dice_roller_prompt(self):
        # Create popup dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Lancer des Des")
        dialog.geometry("400x250")
        dialog.configure(fg_color=self.colors['bg_dark'])
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Lancer des Des", 
                    font=("Courier", 14, "bold"), text_color=self.colors['gold']).pack(pady=20)
        
        # Number of dice
        num_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        num_frame.pack(pady=10)
        
        ctk.CTkLabel(num_frame, text="Nombre de des:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        num_entry = ctk.CTkEntry(num_frame, width=60, font=("Courier", 12),
                                fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        num_entry.pack(side="left", padx=5)
        num_entry.insert(0, "1")
        num_entry.focus()
        
        # Type of dice
        type_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        type_frame.pack(pady=10)
        
        ctk.CTkLabel(type_frame, text="Type de de:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        dice_type = ctk.CTkOptionMenu(type_frame, values=["d4", "d6", "d8", "d10", "d12", "d20", "d100"],
                                      fg_color=self.colors['orange'], button_color=self.colors['orange'],
                                      button_hover_color=self.colors['red'], width=100)
        dice_type.set("d20")
        dice_type.pack(side="left", padx=5)
        
        # Modifier (optional)
        mod_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        mod_frame.pack(pady=10)
        
        ctk.CTkLabel(mod_frame, text="Modificateur (optionnel):", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        mod_entry = ctk.CTkEntry(mod_frame, width=80, font=("Courier", 12),
                                fg_color=self.colors['bg_light'], text_color=self.colors['text'],
                                placeholder_text="+0")
        mod_entry.pack(side="left", padx=5)
        
        def submit():
            num = num_entry.get().strip()
            dtype = dice_type.get()
            mod = mod_entry.get().strip()
            
            if num:
                dice_str = f"{num}{dtype}"
                if mod and mod not in ["+0", "0", ""]:
                    dice_str += mod if mod.startswith(('+', '-')) else f"+{mod}"
                
                self.quick_action(f"Lance les des suivants: {dice_str}")
                dialog.destroy()
        
        num_entry.bind("<Return>", lambda e: submit())
        mod_entry.bind("<Return>", lambda e: submit())
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        self.create_button(btn_frame, "Lancer", submit, 100).pack(side="left", padx=5)
        self.create_button(btn_frame, "Annuler", dialog.destroy, 100).pack(side="left", padx=5)
    
    def encounter_generator(self):
        self.encounter_generator_prompt()
    
    def encounter_generator_prompt(self):
        """Dialogue pour generer une rencontre personnalisee"""
        # Create popup dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Generer Rencontre")
        dialog.geometry("450x400")
        dialog.configure(fg_color=self.colors['bg_dark'])
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Generer une Rencontre", 
                    font=("Courier", 14, "bold"), text_color=self.colors['gold']).pack(pady=15)
        
        # Level input
        level_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        level_frame.pack(pady=8)
        
        ctk.CTkLabel(level_frame, text="Niveau du groupe:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        level_entry = ctk.CTkEntry(level_frame, width=60, font=("Courier", 12),
                                   fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        level_entry.pack(side="left", padx=5)
        level_entry.insert(0, "5")
        level_entry.focus()
        
        # Difficulty
        diff_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        diff_frame.pack(pady=8)
        
        ctk.CTkLabel(diff_frame, text="Difficulte:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        difficulty = ctk.CTkOptionMenu(diff_frame, values=["Facile", "Moyenne", "Difficile", "Mortelle"],
                                       fg_color=self.colors['orange'], button_color=self.colors['orange'],
                                       button_hover_color=self.colors['red'], width=120)
        difficulty.set("Moyenne")
        difficulty.pack(side="left", padx=5)
        
        # Terrain type
        terrain_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        terrain_frame.pack(pady=8)
        
        ctk.CTkLabel(terrain_frame, text="Terrain:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        terrain = ctk.CTkOptionMenu(terrain_frame, 
                                    values=["Foret", "Montagne", "Desert", "Marais", "Plaine", "Underdark", 
                                           "Urbain", "Cote", "Toundra", "Jungle", "Ruines", "Grotte",
                                           "Feywild", "Shadowfell", "Abyss", "Nine Hells", "Astral Plane",
                                           "Ethereal Plane", "Elemental Plane"],
                                    fg_color=self.colors['orange'], button_color=self.colors['orange'],
                                    button_hover_color=self.colors['red'], width=130,
                                    command=lambda choice: self.toggle_elemental_options(choice, elemental_frame))
        terrain.set("Foret")
        terrain.pack(side="left", padx=5)
        
        # Elemental plane options (hidden by default)
        elemental_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        
        ctk.CTkLabel(elemental_frame, text="Element:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        elemental = ctk.CTkOptionMenu(elemental_frame, 
                                      values=["Feu", "Eau", "Terre", "Air"],
                                      fg_color=self.colors['orange'], button_color=self.colors['orange'],
                                      button_hover_color=self.colors['red'], width=100)
        elemental.set("Feu")
        elemental.pack(side="left", padx=5)
        
        # Encounter type
        type_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        type_frame.pack(pady=8)
        
        ctk.CTkLabel(type_frame, text="Type:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        enc_type = ctk.CTkOptionMenu(type_frame, 
                                     values=["Combat", "Piege", "Exploration", "Social", "Mystere", 
                                            "Poursuite", "Embuscade", "Rencontre Amicale", "Evenement Aleatoire",
                                            "Decouverte", "Puzzle", "Negociation"],
                                     fg_color=self.colors['orange'], button_color=self.colors['orange'],
                                     button_hover_color=self.colors['red'], width=150)
        enc_type.set("Combat")
        enc_type.pack(side="left", padx=5)
        
        # Moral alignment
        moral_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        moral_frame.pack(pady=8)
        
        ctk.CTkLabel(moral_frame, text="Alignement:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        moral = ctk.CTkOptionMenu(moral_frame, 
                                  values=["Hostile", "Neutre", "Amical", "Mixte"],
                                  fg_color=self.colors['orange'], button_color=self.colors['orange'],
                                  button_hover_color=self.colors['red'], width=120)
        moral.set("Hostile")
        moral.pack(side="left", padx=5)
        
        def submit():
            level = level_entry.get().strip()
            diff = difficulty.get()
            terr = terrain.get()
            etype = enc_type.get()
            mor = moral.get()
            
            if level:
                # Construire un prompt detaille
                prompt = f"Genere une rencontre {diff} de type '{etype}' pour un groupe de niveau {level}. "
                
                # Ajouter element si plan elementaire
                if terr == "Elemental Plane":
                    elem = elemental.get()
                    prompt += f"Terrain: Plan Elementaire de {elem}. "
                else:
                    prompt += f"Terrain: {terr}. "
                
                prompt += f"Alignement: {mor}. "
                prompt += "Inclus: description, creatures/PNJ impliques, tactiques, recompenses potentielles et consequences."
                
                self.quick_action(prompt)
                dialog.destroy()
        
        level_entry.bind("<Return>", lambda e: submit())
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        self.create_button(btn_frame, "Generer", submit, 100).pack(side="left", padx=5)
        self.create_button(btn_frame, "Annuler", dialog.destroy, 100).pack(side="left", padx=5)
    
    def toggle_elemental_options(self, choice, elemental_frame):
        """Affiche les options elementaires si plan elementaire selectionne"""
        if choice == "Elemental Plane":
            elemental_frame.pack(pady=8)
        else:
            elemental_frame.pack_forget()
    
    def npc_generator(self):
        """Generateur de PNJ avec dialogue de personnalisation"""
        self.npc_generator_prompt()
    
    def npc_generator_prompt(self):
        """Dialogue pour creer un PNJ personnalise"""
        # Creer fenetre popup
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Generer PNJ")
        dialog.geometry("400x300")
        dialog.configure(fg_color=self.colors['bg_dark'])
        
        # Centrer le dialogue
        dialog.transient(self.root)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Generer un PNJ", 
                    font=("Courier", 14, "bold"), text_color=self.colors['gold']).pack(pady=20)
        
        # Type de PNJ
        type_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        type_frame.pack(pady=10)
        
        ctk.CTkLabel(type_frame, text="Type de PNJ:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        npc_type = ctk.CTkOptionMenu(type_frame, 
                                     values=["Mysterieux", "Marchand", "Noble", "Guerrier", "Mage", "Voleur", "Pretre", "Aubergiste",
                                            "Forgeron", "Alchimiste", "Barde", "Ermite", "Garde", "Assassin", "Druide", "Pirate",
                                            "Mendiant", "Sage", "Artisan", "Espion", "Cultiste", "Paladin", "Necromancien", "Chasseur"],
                                     fg_color=self.colors['orange'], button_color=self.colors['orange'],
                                     button_hover_color=self.colors['red'], width=150)
        npc_type.set("Mysterieux")
        npc_type.pack(side="left", padx=5)
        
        # Alignement
        align_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        align_frame.pack(pady=10)
        
        ctk.CTkLabel(align_frame, text="Alignement:", 
                    font=("Courier", 11), text_color=self.colors['text']).pack(side="left", padx=5)
        
        alignment = ctk.CTkOptionMenu(align_frame, 
                                      values=["Bon", "Neutre", "Mauvais", "Aleatoire"],
                                      fg_color=self.colors['orange'], button_color=self.colors['orange'],
                                      button_hover_color=self.colors['red'], width=120)
        alignment.set("Aleatoire")
        alignment.pack(side="left", padx=5)
        
        # Avec quete?
        quest_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        quest_frame.pack(pady=10)
        
        quest_var = ctk.BooleanVar(value=True)
        quest_check = ctk.CTkCheckBox(quest_frame, text="Inclure une quete",
                                      variable=quest_var, fg_color=self.colors['orange'],
                                      hover_color=self.colors['red'], text_color=self.colors['text'])
        quest_check.pack()
        
        def submit():
            """Envoyer la requete au chat"""
            npc_t = npc_type.get()
            align = alignment.get()
            has_quest = quest_var.get()
            
            # Construire le prompt
            prompt = f"Cree un PNJ {npc_t} avec alignement {align}"
            if has_quest:
                prompt += " et donne-lui une quete interessante a proposer aux joueurs"
            prompt += ". Inclus: nom, race, classe, personnalite, background et motivation."
            
            self.quick_action(prompt)
            dialog.destroy()
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        self.create_button(btn_frame, "Generer", submit, 100).pack(side="left", padx=5)
        self.create_button(btn_frame, "Annuler", dialog.destroy, 100).pack(side="left", padx=5)
    
    def dungeon_generator_tool(self):
        self.tabs.set("Donjon")
    
    def xp_calculator(self):
        self.quick_action("Calcule l'XP pour vaincre 3 gobelins et 1 hobgobelin")
    
    def initiative_tracker_tool(self):
        self.tabs.set("Initiative")
    
    # Initiative functions
    def add_init(self):
        try:
            init_value = int(self.i_init.get())
            if self.init_tracker.add(self.i_name.get(), init_value):
                self.i_name.delete(0, "end")
                self.i_init.delete(0, "end")
                self.update_init()
            else:
                messagebox.showerror("Erreur", "L'initiative doit etre entre 0 et 40")
        except Exception as e:
            messagebox.showerror("Erreur", f"Entree invalide: {str(e)}")
    
    def roll_init(self):
        for c in self.init_tracker.creatures:
            c['initiative'] = random.randint(1, 20)
        self.init_tracker.creatures.sort(key=lambda x: x['initiative'], reverse=True)
        self.update_init()
    
    def next_turn(self):
        self.init_tracker.next_turn()
        self.update_init()
    
    def clear_init(self):
        self.init_tracker.clear()
        self.update_init()
    
    def update_init(self):
        self.init_box.delete("1.0", "end")
        self.init_box.insert("end", f"ROUND {self.init_tracker.round_number}\n{'='*50}\n\n")
        curr = self.init_tracker.get_current()
        for c in self.init_tracker.creatures:
            marker = ">>> " if c == curr else "    "
            self.init_box.insert("end", f"{marker}{c['name']:30} Initiative: {c['initiative']:2}\n")
    
    # Dungeon functions
    def gen_dungeon(self):
        try:
            rooms = int(self.d_rooms.get())
            difficulty = self.d_diff.get()
            theme = self.d_theme.get()
            
            # Create AI prompt
            prompt = f"Genere un donjon de {rooms} salles avec difficulte {difficulty} et theme {theme}. Pour chaque salle, donne: numero, type (entrance/chamber/corridor/treasure/boss/trap), description detaillee, monstres presents, et tresors eventuels."
            
            # Switch to chat tab and send the prompt
            self.tabs.set("Chat")
            self.chat_input.delete(0, "end")
            self.chat_input.insert(0, prompt)
            self.send_msg()
            
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
    
    # Session functions removed
    def save_sess(self):
        pass
    
    def load_sess(self):
        pass
    
    def refresh_sess(self):
        pass
    
    def run(self):
        self.root.mainloop()


def main():
    app = DnDAssistantGUI()
    app.run()

if __name__ == "__main__":
    main()