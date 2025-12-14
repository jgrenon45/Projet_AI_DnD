"""
Le Grimoire du Maitre du Donjon v4
Interface complete pour D&D 5e

Nouveautes v4:
- Auto-completion dans les recherches (Monstre, Item, Sort, Regle)
- Generateur de noms enrichi (15+ categories)
- Generateur de tresor
- Suppression du lanceur de des
"""

import customtkinter as ctk
from tkinter import messagebox
import sys
import random
from pathlib import Path
from typing import List, Callable

sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from tools.model_v2 import DnDAssistantModel
    from tools.rag_v2 import RAGSystem
    from tools.db_v2 import MonsterDatabase, SpellDatabase, ItemDatabase
except ImportError as e:
    print(f"Erreur import: {e}")
    try:
        from tools.model import DnDAssistantModel
        from tools.rag import RAGSystem
        from tools.db import MonsterDatabase
        SpellDatabase = None
        ItemDatabase = None
    except ImportError:
        print("Modules introuvables")


class AutocompleteEntry(ctk.CTkFrame):
    """Champ de saisie avec auto-completion"""
    
    def __init__(self, parent, suggestions_source: Callable, placeholder: str, 
                 colors: dict, on_select: Callable = None, **kwargs):
        super().__init__(parent, fg_color="transparent")
        
        self.suggestions_source = suggestions_source
        self.on_select = on_select
        self.colors = colors
        self.suggestions = []
        self.selected_index = -1
        
        # Champ de saisie
        self.entry = ctk.CTkEntry(
            self,
            font=("Courier", 12),
            fg_color=colors['bg_light'],
            text_color=colors['text'],
            placeholder_text=placeholder,
            height=35
        )
        self.entry.pack(fill="x")
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Down>", self._on_down)
        self.entry.bind("<Up>", self._on_up)
        self.entry.bind("<Escape>", self._hide_suggestions)
        
        # Liste de suggestions (cachee par defaut)
        self.listbox_frame = ctk.CTkFrame(self, fg_color=colors['bg_med'])
        self.suggestion_buttons = []
        
    def _on_key_release(self, event):
        if event.keysym in ('Up', 'Down', 'Return', 'Escape'):
            return
        
        query = self.entry.get().strip()
        if len(query) >= 2:
            self._update_suggestions(query)
        else:
            self._hide_suggestions(None)
    
    def _update_suggestions(self, query: str):
        # Obtenir les suggestions
        self.suggestions = self.suggestions_source(query)[:8]  # Max 8 suggestions
        
        # Nettoyer les anciens boutons
        for btn in self.suggestion_buttons:
            btn.destroy()
        self.suggestion_buttons = []
        
        if not self.suggestions:
            self._hide_suggestions(None)
            return
        
        # Afficher le frame de suggestions
        self.listbox_frame.pack(fill="x", pady=(2, 0))
        
        # Creer les boutons de suggestion
        for i, suggestion in enumerate(self.suggestions):
            btn = ctk.CTkButton(
                self.listbox_frame,
                text=suggestion,
                font=("Courier", 10),
                fg_color=self.colors['bg_light'],
                hover_color=self.colors['orange'],
                text_color=self.colors['text'],
                anchor="w",
                height=28,
                corner_radius=0,
                command=lambda s=suggestion: self._select_suggestion(s)
            )
            btn.pack(fill="x", padx=2, pady=1)
            self.suggestion_buttons.append(btn)
        
        self.selected_index = -1
    
    def _select_suggestion(self, suggestion: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, suggestion)
        self._hide_suggestions(None)
        if self.on_select:
            self.on_select()
    
    def _on_enter(self, event):
        if self.selected_index >= 0 and self.selected_index < len(self.suggestions):
            self._select_suggestion(self.suggestions[self.selected_index])
        elif self.on_select:
            self._hide_suggestions(None)
            self.on_select()
    
    def _on_down(self, event):
        if self.suggestions:
            self.selected_index = min(self.selected_index + 1, len(self.suggestions) - 1)
            self._highlight_selection()
    
    def _on_up(self, event):
        if self.suggestions:
            self.selected_index = max(self.selected_index - 1, 0)
            self._highlight_selection()
    
    def _highlight_selection(self):
        for i, btn in enumerate(self.suggestion_buttons):
            if i == self.selected_index:
                btn.configure(fg_color=self.colors['orange'], text_color="#000000")
            else:
                btn.configure(fg_color=self.colors['bg_light'], text_color=self.colors['text'])
    
    def _hide_suggestions(self, event):
        self.listbox_frame.pack_forget()
        for btn in self.suggestion_buttons:
            btn.destroy()
        self.suggestion_buttons = []
        self.suggestions = []
        self.selected_index = -1
    
    def get(self) -> str:
        return self.entry.get()
    
    def delete(self, start, end):
        self.entry.delete(start, end)
    
    def insert(self, index, text):
        self.entry.insert(index, text)
    
    def bind(self, event, callback):
        self.entry.bind(event, callback)


class NameGenerator:
    """Generateur de noms fantasy enrichi"""
    
    # Prenoms masculins par culture
    MALE_NAMES = {
        'humain': ["Aldric", "Bran", "Cedric", "Darius", "Edmund", "Farin", "Gareth", "Harald", 
                   "Ivan", "Jasper", "Klaus", "Leon", "Marcus", "Nolan", "Owen", "Pierce",
                   "Quinn", "Roland", "Stefan", "Theron", "Ulric", "Viktor", "Wilhelm", "Xavier"],
        'elfe': ["Aelindor", "Caelum", "Eldrin", "Faelar", "Galadorn", "Ilthuryn", "Luthien",
                 "Naerion", "Quildor", "Rhistel", "Sylvaris", "Thalion", "Vaeril", "Zephyrus"],
        'nain': ["Balin", "Dain", "Fargrim", "Gimli", "Harbek", "Kildrak", "Morgran",
                 "Orsik", "Rangrim", "Thorin", "Ulfgar", "Vondal", "Werend"],
        'halfelin': ["Alton", "Cade", "Corrin", "Eldon", "Finnan", "Garret", "Lindal",
                     "Merric", "Osborn", "Perrin", "Roscoe", "Wellby"],
        'orc': ["Dench", "Gell", "Henk", "Holg", "Imsh", "Krusk", "Mhurren", "Ront", "Shump", "Thokk"],
        'tiefling': ["Akmenos", "Amnon", "Barakas", "Damakos", "Ekemon", "Iados", "Kairon",
                     "Leucis", "Melech", "Mordai", "Morthos", "Pelaios", "Skamos", "Therai"]
    }
    
    # Prenoms feminins par culture
    FEMALE_NAMES = {
        'humain': ["Alina", "Brynn", "Celeste", "Diana", "Elena", "Freya", "Gwendolyn",
                   "Helena", "Isolde", "Juliana", "Katarina", "Lyra", "Miranda", "Natasha",
                   "Ophelia", "Petra", "Quinn", "Rowena", "Selene", "Thea", "Una", "Vera", "Wren"],
        'elfe': ["Adrie", "Caelynn", "Drusilia", "Enna", "Felosial", "Galinndan", "Irann",
                 "Keyleth", "Lia", "Mialee", "Naivara", "Quelenna", "Sariel", "Thia", "Valanthe"],
        'nain': ["Amber", "Artin", "Bardryn", "Dagnal", "Diesa", "Gunnloda", "Helja",
                 "Kathra", "Kristryd", "Mardred", "Riswynn", "Torgga", "Vistra"],
        'halfelin': ["Andry", "Bree", "Callie", "Cora", "Euphemia", "Jillian", "Kithri",
                     "Lavinia", "Lidda", "Merla", "Nedda", "Paela", "Portia", "Seraphina", "Vani"],
        'orc': ["Baggi", "Emen", "Engong", "Kansif", "Myev", "Neega", "Ovak", "Ownka", "Shautha", "Vola"],
        'tiefling': ["Akta", "Bryseis", "Damaia", "Ea", "Kallista", "Lerissa", "Makaria",
                     "Nemeia", "Orianna", "Phelaia", "Rieta"]
    }
    
    # Noms de famille par culture
    SURNAMES = {
        'humain': ["Forgefeu", "Hautecolline", "Briseciel", "Lameblanche", "Corvinus", "Duval",
                   "Montclair", "Beaumont", "Chevalier", "Dubois", "Lefebvre", "Moreau"],
        'elfe': ["Amastacia", "Galanodel", "Holimion", "Liadon", "Meliamne", "Nailo",
                 "Siannodel", "Xiloscient"],
        'nain': ["Forgepoing", "Brisebranches", "Marteaudore", "Ecubouclier", "Gardehache",
                 "Pieddefer", "Coeudepierre"],
        'noble': ["de Montfort", "von Steinberg", "di Medici", "van der Berg", "le Grand",
                  "d'Aragon", "de Valois", "von Habsburg"]
    }
    
    # Noms de tavernes
    TAVERN_PARTS = {
        'adj': ["Joyeux", "Vieux", "Noir", "Rouge", "Dore", "Argente", "Borgne", "Ivre",
                "Sage", "Fou", "Brave", "Fier", "Sombre", "Blanc", "Vert", "Bleu"],
        'noun': ["Dragon", "Griffon", "Sanglier", "Loup", "Corbeau", "Cerf", "Ours", "Aigle",
                 "Gobelin", "Troll", "Ogre", "Chevalier", "Mage", "Barde", "Nain", "Elfe",
                 "Phoenix", "Licorne", "Hippogriffe", "Chimere", "Basilic", "Wyverne"],
        'prefix': ["Au", "Le", "La", "L'Auberge du", "La Taverne du", "Chez le", "A l'Enseigne du"]
    }
    
    # Noms de boutiques
    SHOP_NAMES = {
        'forge': ["La Forge", "L'Enclume", "Le Marteau", "Les Lames", "L'Acier"],
        'alchimie': ["Le Chaudron", "La Fiole", "L'Alambic", "Les Herbes", "L'Elixir"],
        'magie': ["La Baguette", "Le Grimoire", "L'Arcane", "Le Cristal", "Les Runes"],
        'general': ["Le Bazar", "L'Emporium", "Le Comptoir", "La Boutique", "Le Marche"],
        'armure': ["Le Bouclier", "La Cuirasse", "L'Armurerie", "La Maille"],
        'bijoux': ["Le Joyau", "L'Eclat", "La Gemme", "Le Diamant", "L'Or Fin"]
    }
    
    # Noms de lieux
    PLACE_PARTS = {
        'prefix': ["Fort", "Chateau", "Tour", "Donjon", "Cite", "Village", "Hameau", "Val",
                   "Mont", "Port", "Pont", "Bois", "Lac", "Ile", "Ruines de"],
        'suffix': ["noir", "blanc", "rouge", "ancien", "perdu", "maudit", "sacre", "oublie",
                   "sombre", "lumineux", "eternel", "brise", "gel", "feu", "vent"]
    }
    
    # Noms de guildes
    GUILD_NAMES = {
        'type': ["Guilde", "Ordre", "Confrerie", "Loge", "Cercle", "Alliance", "Compagnie"],
        'theme': ["des Ombres", "du Soleil Levant", "de l'Epee Brisee", "du Dragon d'Or",
                  "des Marchands", "des Artisans", "des Voleurs", "des Assassins",
                  "des Mages", "des Guerriers", "de la Main Noire", "du Serpent",
                  "du Phenix", "de l'Ancre", "du Corbeau", "de la Lune"]
    }
    
    # Noms de navires
    SHIP_NAMES = {
        'prefix': ["Le", "La", "L'"],
        'adj': ["Rapide", "Fier", "Noir", "Rouge", "Dore", "Fantome", "Sombre", "Royal"],
        'noun': ["Sirene", "Triton", "Kraken", "Leviathan", "Tempete", "Eclair", "Vent",
                 "Maree", "Etoile", "Lune", "Soleil", "Dragon", "Serpent", "Requin", "Mouette"]
    }
    
    # Noms de sorts
    SPELL_NAME_PARTS = {
        'possessor': ["Mordenkainen", "Bigby", "Tasha", "Melf", "Otiluke", "Leomund",
                      "Tenser", "Evard", "Nystul", "Rary", "Drawmij"],
        'type': ["Sphere", "Rayon", "Eclair", "Bouclier", "Main", "Chaine", "Prison",
                 "Cage", "Manteau", "Souffle", "Vague", "Tempete", "Lame"],
        'element': ["de Feu", "de Glace", "de Foudre", "d'Acide", "de Force", "de Mort",
                    "de Lumiere", "d'Ombre", "Arcanique", "Divin", "Spectral"]
    }
    
    # Noms de familiers
    FAMILIAR_NAMES = ["Ombre", "Croc", "Plume", "Griffe", "Ecaille", "Poil", "Bec", "Aile",
                      "Nuit", "Lune", "Etoile", "Brume", "Fumee", "Cendre", "Charbon",
                      "Onyx", "Jade", "Rubis", "Saphir", "Emeraude", "Obsidienne"]
    
    # Noms de demons/diables
    DEMON_NAMES = {
        'prefix': ["Bal", "Graz", "Orcus", "Dem", "Yeen", "Zug", "Mol", "Bel", "Asmo", "Dis"],
        'suffix': ["zul", "gor", "oth", "nax", "riel", "khan", "mog", "thar", "zor", "deus"]
    }
    
    # Noms de dragons
    DRAGON_NAMES = {
        'prefix': ["Ald", "Bala", "Cyan", "Drax", "Eryth", "Fafn", "Glau", "Ixen", "Kala", 
                   "Mala", "Nith", "Orm", "Pala", "Rash", "Syr", "Thra", "Vorn", "Xar", "Zeph"],
        'suffix': ["ryx", "thorn", "wing", "scale", "fire", "frost", "storm", "claw", 
                   "fang", "breath", "ax", "ius", "or", "ion", "ath", "yx"]
    }
    
    @classmethod
    def generate(cls, category: str) -> str:
        """Genere un nom selon la categorie"""
        
        if category == "Humain (M)":
            first = random.choice(cls.MALE_NAMES['humain'])
            last = random.choice(cls.SURNAMES['humain'])
            return f"{first} {last}"
        
        elif category == "Humain (F)":
            first = random.choice(cls.FEMALE_NAMES['humain'])
            last = random.choice(cls.SURNAMES['humain'])
            return f"{first} {last}"
        
        elif category == "Elfe (M)":
            first = random.choice(cls.MALE_NAMES['elfe'])
            last = random.choice(cls.SURNAMES['elfe'])
            return f"{first} {last}"
        
        elif category == "Elfe (F)":
            first = random.choice(cls.FEMALE_NAMES['elfe'])
            last = random.choice(cls.SURNAMES['elfe'])
            return f"{first} {last}"
        
        elif category == "Nain (M)":
            first = random.choice(cls.MALE_NAMES['nain'])
            last = random.choice(cls.SURNAMES['nain'])
            return f"{first} {last}"
        
        elif category == "Nain (F)":
            first = random.choice(cls.FEMALE_NAMES['nain'])
            last = random.choice(cls.SURNAMES['nain'])
            return f"{first} {last}"
        
        elif category == "Halfelin (M)":
            first = random.choice(cls.MALE_NAMES['halfelin'])
            return first
        
        elif category == "Halfelin (F)":
            first = random.choice(cls.FEMALE_NAMES['halfelin'])
            return first
        
        elif category == "Orc":
            return random.choice(cls.MALE_NAMES['orc'] + cls.FEMALE_NAMES['orc'])
        
        elif category == "Tiefling (M)":
            return random.choice(cls.MALE_NAMES['tiefling'])
        
        elif category == "Tiefling (F)":
            return random.choice(cls.FEMALE_NAMES['tiefling'])
        
        elif category == "Noble":
            gender = random.choice(['humain'])
            first = random.choice(cls.MALE_NAMES[gender] + cls.FEMALE_NAMES[gender])
            last = random.choice(cls.SURNAMES['noble'])
            return f"{first} {last}"
        
        elif category == "Taverne":
            pattern = random.choice([
                f"{random.choice(cls.TAVERN_PARTS['prefix'])} {random.choice(cls.TAVERN_PARTS['adj'])} {random.choice(cls.TAVERN_PARTS['noun'])}",
                f"Au {random.choice(cls.TAVERN_PARTS['noun'])} {random.choice(cls.TAVERN_PARTS['adj'])}",
                f"L'Auberge du {random.choice(cls.TAVERN_PARTS['noun'])}",
                f"Chez {random.choice(cls.MALE_NAMES['humain'])}"
            ])
            return pattern
        
        elif category == "Boutique (Forge)":
            base = random.choice(cls.SHOP_NAMES['forge'])
            owner = random.choice(cls.MALE_NAMES['nain'] + cls.MALE_NAMES['humain'])
            return f"{base} de {owner}"
        
        elif category == "Boutique (Magie)":
            base = random.choice(cls.SHOP_NAMES['magie'])
            owner = random.choice(cls.MALE_NAMES['elfe'] + cls.FEMALE_NAMES['elfe'])
            return f"{base} d'{owner}" if owner[0] in "AEIOU" else f"{base} de {owner}"
        
        elif category == "Boutique (General)":
            base = random.choice(cls.SHOP_NAMES['general'])
            owner = random.choice(cls.MALE_NAMES['humain'] + cls.MALE_NAMES['halfelin'])
            return f"{base} de {owner}"
        
        elif category == "Lieu/Ville":
            pattern = random.choice([
                f"{random.choice(cls.PLACE_PARTS['prefix'])}-{random.choice(cls.PLACE_PARTS['suffix'])}",
                f"{random.choice(cls.PLACE_PARTS['prefix'])} {random.choice(cls.MALE_NAMES['humain'])}",
                f"{random.choice(cls.PLACE_PARTS['prefix'])} de {random.choice(cls.SURNAMES['humain'])}"
            ])
            return pattern
        
        elif category == "Guilde":
            return f"{random.choice(cls.GUILD_NAMES['type'])} {random.choice(cls.GUILD_NAMES['theme'])}"
        
        elif category == "Navire":
            return f"{random.choice(cls.SHIP_NAMES['prefix'])} {random.choice(cls.SHIP_NAMES['adj'])} {random.choice(cls.SHIP_NAMES['noun'])}"
        
        elif category == "Sort":
            return f"{random.choice(cls.SPELL_NAME_PARTS['type'])} {random.choice(cls.SPELL_NAME_PARTS['element'])} de {random.choice(cls.SPELL_NAME_PARTS['possessor'])}"
        
        elif category == "Familier":
            return random.choice(cls.FAMILIAR_NAMES)
        
        elif category == "Demon/Diable":
            return f"{random.choice(cls.DEMON_NAMES['prefix'])}{random.choice(cls.DEMON_NAMES['suffix'])}"
        
        elif category == "Dragon":
            return f"{random.choice(cls.DRAGON_NAMES['prefix'])}{random.choice(cls.DRAGON_NAMES['suffix'])}"
        
        return "Nom inconnu"


class TreasureGenerator:
    """Generateur de tresor D&D"""
    
    # Pieces par niveau de tresor
    COINS = {
        'faible': {'cp': (5, 30), 'sp': (3, 18), 'gp': (1, 6)},
        'moyen': {'sp': (10, 60), 'gp': (5, 30), 'pp': (0, 3)},
        'eleve': {'gp': (20, 120), 'pp': (2, 12)},
        'epique': {'gp': (100, 600), 'pp': (10, 60)}
    }
    
    # Gemmes par valeur
    GEMS = {
        10: ["Azurite", "Agate", "Quartz bleu", "Hematite", "Lapis-lazuli", "Malachite",
             "Obsidienne", "Rhodochrosite", "Oeil-de-tigre", "Turquoise"],
        50: ["Jaspe sanguin", "Cornaline", "Calcedoine", "Chrysoprase", "Citrine",
             "Cristal de roche", "Jade", "Onyx", "Zircon"],
        100: ["Ambre", "Amethyste", "Chrysoberyl", "Corail", "Grenat", "Jais",
              "Perle", "Spinelle", "Tourmaline"],
        500: ["Alexandrite", "Aigue-marine", "Perle noire", "Topaze bleue", "Peridot"],
        1000: ["Emeraude", "Opale noire", "Saphir bleu", "Opale de feu", "Saphir jaune"],
        5000: ["Diamant", "Jacynthe", "Rubis", "Saphir etoile", "Emeraude etoile"]
    }
    
    # Objets d'art par valeur
    ART_OBJECTS = {
        25: ["Statuette en os sculpte", "Bracelet en or simple", "Vetements en tissu dore",
             "Masque de velours brode", "Calice en argent", "Des en os incrustes"],
        250: ["Anneau en or avec gemme", "Coupe en argent gravee", "Harpe en bois precieux",
              "Statuette en ivoire", "Pendentif en or massif", "Couronne en argent"],
        750: ["Coffret en argent incrusté de gemmes", "Portrait peint d'un noble",
              "Collier de perles fines", "Sceptre en or plaque", "Calice en or grave"],
        2500: ["Tapisserie brodee de fil d'or", "Couronne en or avec gemmes",
               "Statuette en or massif", "Armure de parade ouvragee"],
        7500: ["Coffret en or avec rubis", "Couronne royale ornee", "Sceptre imperial",
               "Trone miniature en or massif"]
    }
    
    # Items magiques par rarete
    MAGIC_ITEMS = {
        'commun': [
            "Potion de soins", "Parchemin de sort (niveau 1)", "Munitions +1 (10)",
            "Potion d'escalade", "Bougie de verite", "Cape de billowing"
        ],
        'peu commun': [
            "Potion de soins superieurs", "Parchemin de sort (niveau 2-3)",
            "Arme +1", "Armure +1", "Baguette de detection de la magie",
            "Bottes elfiques", "Cape elfique", "Sac sans fond", 
            "Lunettes de nuit", "Pierre ioun (sustentation)", "Anneau de nage",
            "Amulette de preuve contre la detection", "Gants de voleur"
        ],
        'rare': [
            "Potion de soins excellents", "Parchemin de sort (niveau 4-5)",
            "Arme +2", "Armure +2", "Anneau de protection", "Cape de protection",
            "Ceinture de force de geant des collines", "Baguette de boules de feu",
            "Epee ardente", "Bottes ailees", "Collier de boules de feu",
            "Bracelets de defense", "Corde d'enchevêtrement"
        ],
        'tres rare': [
            "Potion de soins supremes", "Parchemin de sort (niveau 6-8)",
            "Arme +3", "Armure +3", "Ceinture de force de geant du feu",
            "Tapis volant", "Baguette de polymorphie", "Baton de feu",
            "Epee vorpale", "Anneau de regeneration", "Cape de deplacement"
        ],
        'legendaire': [
            "Parchemin de sort (niveau 9)", "Armure d'invulnerabilite",
            "Ceinture de force de geant des tempetes", "Baton du mage",
            "Epee de reponse", "Cube de force", "Sphere d'annihilation",
            "Anneau des trois souhaits", "Manuel des golems"
        ]
    }
    
    @classmethod
    def generate(cls, level: str, include_magic: bool = True) -> dict:
        """Genere un tresor complet"""
        result = {
            'coins': {},
            'gems': [],
            'art': [],
            'magic_items': []
        }
        
        # Pieces
        coin_tier = {
            'Faible (CR 0-4)': 'faible',
            'Moyen (CR 5-10)': 'moyen',
            'Eleve (CR 11-16)': 'eleve',
            'Epique (CR 17+)': 'epique'
        }.get(level, 'moyen')
        
        for coin, (min_val, max_val) in cls.COINS[coin_tier].items():
            amount = random.randint(min_val, max_val)
            if amount > 0:
                result['coins'][coin] = amount
        
        # Gemmes (chance variable selon niveau)
        gem_chance = {'faible': 0.2, 'moyen': 0.4, 'eleve': 0.6, 'epique': 0.8}[coin_tier]
        if random.random() < gem_chance:
            gem_values = {'faible': [10, 50], 'moyen': [50, 100], 
                         'eleve': [100, 500], 'epique': [500, 1000, 5000]}[coin_tier]
            num_gems = random.randint(1, 4)
            for _ in range(num_gems):
                value = random.choice(gem_values)
                gem = random.choice(cls.GEMS[value])
                result['gems'].append(f"{gem} ({value} po)")
        
        # Objets d'art
        art_chance = {'faible': 0.1, 'moyen': 0.3, 'eleve': 0.5, 'epique': 0.7}[coin_tier]
        if random.random() < art_chance:
            art_values = {'faible': [25], 'moyen': [25, 250], 
                         'eleve': [250, 750], 'epique': [750, 2500, 7500]}[coin_tier]
            num_art = random.randint(1, 2)
            for _ in range(num_art):
                value = random.choice(art_values)
                art = random.choice(cls.ART_OBJECTS[value])
                result['art'].append(f"{art} ({value} po)")
        
        # Items magiques
        if include_magic:
            magic_chance = {'faible': 0.15, 'moyen': 0.35, 'eleve': 0.55, 'epique': 0.75}[coin_tier]
            if random.random() < magic_chance:
                rarities = {
                    'faible': ['commun', 'peu commun'],
                    'moyen': ['peu commun', 'rare'],
                    'eleve': ['rare', 'tres rare'],
                    'epique': ['tres rare', 'legendaire']
                }[coin_tier]
                
                num_items = random.randint(1, 2)
                for _ in range(num_items):
                    rarity = random.choice(rarities)
                    item = random.choice(cls.MAGIC_ITEMS[rarity])
                    result['magic_items'].append(f"{item} ({rarity})")
        
        return result
    
    @classmethod
    def format_treasure(cls, treasure: dict) -> str:
        """Formate le tresor pour l'affichage"""
        lines = ["=" * 40, "TRESOR GENERE", "=" * 40, ""]
        
        # Pieces
        if treasure['coins']:
            lines.append("PIECES:")
            coin_names = {'cp': 'cuivre', 'sp': 'argent', 'gp': 'or', 'pp': 'platine'}
            for coin, amount in treasure['coins'].items():
                lines.append(f"  {amount} pieces de {coin_names[coin]}")
            lines.append("")
        
        # Gemmes
        if treasure['gems']:
            lines.append("GEMMES:")
            for gem in treasure['gems']:
                lines.append(f"  {gem}")
            lines.append("")
        
        # Objets d'art
        if treasure['art']:
            lines.append("OBJETS D'ART:")
            for art in treasure['art']:
                lines.append(f"  {art}")
            lines.append("")
        
        # Items magiques
        if treasure['magic_items']:
            lines.append("ITEMS MAGIQUES:")
            for item in treasure['magic_items']:
                lines.append(f"  {item}")
            lines.append("")
        
        # Total approximatif
        total = 0
        coin_values = {'cp': 0.01, 'sp': 0.1, 'gp': 1, 'pp': 10}
        for coin, amount in treasure['coins'].items():
            total += amount * coin_values[coin]
        
        lines.append("-" * 40)
        lines.append(f"Valeur pieces: ~{int(total)} po")
        
        return "\n".join(lines)


class InitiativeTracker:
    """Gestionnaire d'initiative pour les combats"""
    
    def __init__(self):
        self.creatures = []
        self.current_index = 0
        self.round_number = 1
    
    def add(self, name: str, init: int) -> bool:
        if 0 <= init <= 40 and name.strip():
            self.creatures.append({'name': name.strip(), 'initiative': init})
            self.creatures.sort(key=lambda x: x['initiative'], reverse=True)
            return True
        return False
    
    def remove(self, index: int) -> bool:
        if 0 <= index < len(self.creatures):
            self.creatures.pop(index)
            if self.current_index >= len(self.creatures):
                self.current_index = max(0, len(self.creatures) - 1)
            return True
        return False
    
    def next_turn(self):
        if self.creatures:
            self.current_index = (self.current_index + 1) % len(self.creatures)
            if self.current_index == 0:
                self.round_number += 1
    
    def prev_turn(self):
        if self.creatures:
            if self.current_index == 0 and self.round_number > 1:
                self.round_number -= 1
                self.current_index = len(self.creatures) - 1
            elif self.current_index > 0:
                self.current_index -= 1
    
    def get_current(self):
        return self.creatures[self.current_index] if self.creatures else None
    
    def clear(self):
        self.creatures = []
        self.current_index = 0
        self.round_number = 1


class DnDAssistantGUI:
    """Interface principale du Grimoire du Maitre du Donjon"""
    
    def __init__(self):
        self.model = None
        self.rag = None
        self.monster_db = None
        self.spell_db = None
        self.item_db = None
        self.init_tracker = InitiativeTracker()
        self.chat_history = []
        
        # Caches pour l'auto-completion
        self.monster_names = []
        self.spell_names = []
        self.item_names = []
        self.rule_keywords = [
            "combat", "attaque", "action", "mouvement", "initiative", "round",
            "repos court", "repos long", "concentration", "avantage", "desavantage",
            "sauvegarde", "jet", "competence", "classe armure", "couverture",
            "attaque opportunite", "condition", "aveugle", "charme", "effraye",
            "paralyse", "empoisonne", "prone", "etourdi", "inconscient",
            "magie", "sort", "cantrip", "emplacement", "composante", "rituel",
            "degats", "resistance", "immunite", "vulnerabilite",
            "force", "dexterite", "constitution", "intelligence", "sagesse", "charisme",
            "multiclasse", "niveau", "experience", "alignement", "langue",
            "equipement", "arme", "armure", "bouclier", "lumiere", "vision",
            "terrain difficile", "saut", "escalade", "nage"
        ]
        
        self.setup_window()
        self.create_layout()
        self.root.after(100, self.initialize_systems)
    
    def setup_window(self):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("Le Grimoire du Maitre du Donjon")
        self.root.geometry("1500x950")
        self.root.minsize(1300, 800)
        
        self.colors = {
            'bg_dark': '#1a0a00',
            'bg_med': '#2d1810',
            'bg_light': '#4a2511',
            'orange': '#FF8C00',
            'red': '#8B0000',
            'text': '#FFB366',
            'gold': '#DAA520',
            'text_dim': '#996633'
        }
        self.root.configure(fg_color=self.colors['bg_dark'])
    
    def create_layout(self):
        self._create_header()
        
        main_container = ctk.CTkFrame(self.root, fg_color=self.colors['bg_dark'])
        main_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.main_panel = ctk.CTkFrame(main_container, fg_color=self.colors['bg_dark'])
        self.main_panel.pack(side="left", fill="both", expand=True)
        
        self.side_panel = ctk.CTkFrame(main_container, fg_color=self.colors['bg_med'], width=280)
        self.side_panel.pack(side="right", fill="y", padx=(5, 0))
        self.side_panel.pack_propagate(False)
        
        self._create_tabs()
        self._create_initiative_panel()
        self._create_footer()
    
    def _create_header(self):
        header = ctk.CTkFrame(self.root, fg_color=self.colors['red'], height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="LE GRIMOIRE DU MAITRE DU DONJON",
            font=("Courier", 22, "bold"),
            text_color=self.colors['gold']
        ).pack(pady=(8, 0))
        
        self.status = ctk.CTkLabel(
            header,
            text="Initialisation...",
            font=("Courier", 9),
            text_color=self.colors['orange']
        )
        self.status.pack()
    
    def _create_tabs(self):
        self.tabs = ctk.CTkTabview(
            self.main_panel,
            fg_color=self.colors['bg_dark'],
            segmented_button_fg_color=self.colors['bg_med'],
            segmented_button_selected_color=self.colors['orange'],
            segmented_button_selected_hover_color=self.colors['orange'],
            segmented_button_unselected_color=self.colors['bg_med'],
            text_color=self.colors['text']
        )
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_chat = self.tabs.add("Chat")
        self.tab_npc = self.tabs.add("PNJ")
        self.tab_monster = self.tabs.add("Monstre")
        self.tab_building = self.tabs.add("Batiment")
        self.tab_magic_item = self.tabs.add("Item Magique")
        self.tab_spell = self.tabs.add("Sort")
        self.tab_rules = self.tabs.add("Regle")
        self.tab_tools = self.tabs.add("Outil")
        
        self._setup_chat_tab()
        self._setup_npc_tab()
        self._setup_monster_tab()
        self._setup_building_tab()
        self._setup_magic_item_tab()
        self._setup_spell_tab()
        self._setup_rules_tab()
        self._setup_tools_tab()
    
    def _setup_chat_tab(self):
        self.chat_box = ctk.CTkTextbox(
            self.tab_chat,
            font=("Courier", 11),
            fg_color=self.colors['bg_light'],
            text_color=self.colors['text'],
            wrap="word"
        )
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        self.chat_box.insert("end", "Bienvenue, Maitre du Donjon.\n\nPose tes questions sur D&D 5e.\n\n")
        
        input_frame = ctk.CTkFrame(self.tab_chat, fg_color=self.colors['bg_med'])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        self.chat_input = ctk.CTkEntry(
            input_frame,
            font=("Courier", 12),
            fg_color=self.colors['bg_light'],
            text_color=self.colors['text'],
            placeholder_text="Pose ta question...",
            height=40
        )
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(5, 10), pady=5)
        self.chat_input.bind("<Return>", lambda e: self.send_message())
        
        self._create_button(input_frame, "Envoyer", self.send_message, 100).pack(side="right", padx=5, pady=5)
    
    def _setup_npc_tab(self):
        header = ctk.CTkFrame(self.tab_npc, fg_color=self.colors['bg_med'])
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="GENERATEUR DE PNJ", font=("Courier", 16, "bold"),
                    text_color=self.colors['gold']).pack(pady=10)
        
        options_frame = ctk.CTkFrame(header, fg_color="transparent")
        options_frame.pack(pady=10)
        
        ctk.CTkLabel(options_frame, text="Type:", text_color=self.colors['text']).grid(row=0, column=0, padx=5, pady=5)
        self.npc_type = ctk.CTkOptionMenu(
            options_frame,
            values=["Marchand", "Noble", "Guerrier", "Mage", "Voleur", "Pretre", 
                    "Aubergiste", "Forgeron", "Garde", "Paysan", "Mendiant", "Sage", 
                    "Assassin", "Barde", "Druide", "Pirate", "Chasseur", "Artisan"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=140
        )
        self.npc_type.set("Marchand")
        self.npc_type.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(options_frame, text="Race:", text_color=self.colors['text']).grid(row=0, column=2, padx=5, pady=5)
        self.npc_race = ctk.CTkOptionMenu(
            options_frame,
            values=["Humain", "Elfe", "Nain", "Halfelin", "Demi-Elfe", "Demi-Orc", 
                    "Gnome", "Tiefling", "Dragonborn", "Aleatoire"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=120
        )
        self.npc_race.set("Aleatoire")
        self.npc_race.grid(row=0, column=3, padx=5, pady=5)
        
        ctk.CTkLabel(options_frame, text="Alignement:", text_color=self.colors['text']).grid(row=1, column=0, padx=5, pady=5)
        self.npc_align = ctk.CTkOptionMenu(
            options_frame,
            values=["Loyal Bon", "Neutre Bon", "Chaotique Bon", "Loyal Neutre", 
                    "Neutre", "Chaotique Neutre", "Loyal Mauvais", "Neutre Mauvais", 
                    "Chaotique Mauvais", "Aleatoire"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=140
        )
        self.npc_align.set("Aleatoire")
        self.npc_align.grid(row=1, column=1, padx=5, pady=5)
        
        self.npc_quest = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(options_frame, text="Avec quete", variable=self.npc_quest,
                       fg_color=self.colors['orange'], hover_color=self.colors['red'],
                       text_color=self.colors['text']).grid(row=1, column=2, columnspan=2, padx=5, pady=5)
        
        self._create_button(header, "Generer PNJ", self.generate_npc, 150).pack(pady=10)
        
        self.npc_display = ctk.CTkTextbox(self.tab_npc, font=("Courier", 11),
                                          fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        self.npc_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _setup_monster_tab(self):
        search_frame = ctk.CTkFrame(self.tab_monster, fg_color=self.colors['bg_med'])
        search_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(search_frame, text="BESTIAIRE", font=("Courier", 16, "bold"),
                    text_color=self.colors['gold']).pack(pady=5)
        
        input_row = ctk.CTkFrame(search_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=10, pady=5)
        
        # Auto-completion pour monstres
        self.monster_search = AutocompleteEntry(
            input_row,
            suggestions_source=self._get_monster_suggestions,
            placeholder="Nom du monstre...",
            colors=self.colors,
            on_select=self.search_monster
        )
        self.monster_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self._create_button(input_row, "Chercher", self.search_monster, 100).pack(side="right")
        
        self.monster_display = ctk.CTkTextbox(self.tab_monster, font=("Courier", 11),
                                              fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        self.monster_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.monster_display.insert("end", "Recherche un monstre par son nom.\nCommence a taper pour voir les suggestions.\n\nExemples: Goblin, Dragon, Beholder...")
    
    def _setup_building_tab(self):
        header = ctk.CTkFrame(self.tab_building, fg_color=self.colors['bg_med'])
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="GENERATEUR DE BATIMENTS", font=("Courier", 16, "bold"),
                    text_color=self.colors['gold']).pack(pady=10)
        
        options_frame = ctk.CTkFrame(header, fg_color="transparent")
        options_frame.pack(pady=10)
        
        ctk.CTkLabel(options_frame, text="Type:", text_color=self.colors['text']).grid(row=0, column=0, padx=5, pady=5)
        self.building_type = ctk.CTkOptionMenu(
            options_frame,
            values=["Taverne", "Forge", "Temple", "Bibliotheque", "Chateau", "Tour de mage",
                    "Prison", "Guildes", "Marche", "Manoir", "Ruines", "Donjon",
                    "Auberge", "Echoppe", "Caserne", "Cimetiere"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=150
        )
        self.building_type.set("Taverne")
        self.building_type.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(options_frame, text="Etat:", text_color=self.colors['text']).grid(row=0, column=2, padx=5, pady=5)
        self.building_state = ctk.CTkOptionMenu(
            options_frame,
            values=["Neuf", "Bon etat", "Use", "Delabre", "Ruine", "Hante"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=120
        )
        self.building_state.set("Bon etat")
        self.building_state.grid(row=0, column=3, padx=5, pady=5)
        
        ctk.CTkLabel(options_frame, text="Ambiance:", text_color=self.colors['text']).grid(row=1, column=0, padx=5, pady=5)
        self.building_mood = ctk.CTkOptionMenu(
            options_frame,
            values=["Accueillante", "Mysterieuse", "Sinistre", "Animee", "Calme", "Luxueuse", "Pauvre"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=150
        )
        self.building_mood.set("Accueillante")
        self.building_mood.grid(row=1, column=1, padx=5, pady=5)
        
        self.building_secret = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_frame, text="Avec secret cache", variable=self.building_secret,
                       fg_color=self.colors['orange'], hover_color=self.colors['red'],
                       text_color=self.colors['text']).grid(row=1, column=2, columnspan=2, padx=5, pady=5)
        
        self._create_button(header, "Generer Batiment", self.generate_building, 160).pack(pady=10)
        
        self.building_display = ctk.CTkTextbox(self.tab_building, font=("Courier", 11),
                                               fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        self.building_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _setup_magic_item_tab(self):
        header = ctk.CTkFrame(self.tab_magic_item, fg_color=self.colors['bg_med'])
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="ITEMS MAGIQUES", font=("Courier", 16, "bold"),
                    text_color=self.colors['gold']).pack(pady=5)
        
        search_row = ctk.CTkFrame(header, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=5)
        
        # Auto-completion pour items
        self.item_search = AutocompleteEntry(
            search_row,
            suggestions_source=self._get_item_suggestions,
            placeholder="Rechercher un item...",
            colors=self.colors,
            on_select=self.search_item
        )
        self.item_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self._create_button(search_row, "Chercher", self.search_item, 100).pack(side="right", padx=5)
        self._create_button(search_row, "Generer", self.generate_magic_item, 100).pack(side="right")
        
        gen_frame = ctk.CTkFrame(header, fg_color="transparent")
        gen_frame.pack(pady=5)
        
        ctk.CTkLabel(gen_frame, text="Rarete:", text_color=self.colors['text']).pack(side="left", padx=5)
        self.item_rarity = ctk.CTkOptionMenu(
            gen_frame, values=["Uncommon", "Rare", "Very Rare", "Legendary", "Aleatoire"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=120
        )
        self.item_rarity.set("Aleatoire")
        self.item_rarity.pack(side="left", padx=5)
        
        ctk.CTkLabel(gen_frame, text="Type:", text_color=self.colors['text']).pack(side="left", padx=5)
        self.item_type = ctk.CTkOptionMenu(
            gen_frame, values=["Arme", "Armure", "Anneau", "Baguette", "Potion", "Parchemin", "Amulette", "Aleatoire"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=120
        )
        self.item_type.set("Aleatoire")
        self.item_type.pack(side="left", padx=5)
        
        self.item_display = ctk.CTkTextbox(self.tab_magic_item, font=("Courier", 11),
                                           fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        self.item_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _setup_spell_tab(self):
        header = ctk.CTkFrame(self.tab_spell, fg_color=self.colors['bg_med'])
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="GRIMOIRE DES SORTS", font=("Courier", 16, "bold"),
                    text_color=self.colors['gold']).pack(pady=5)
        
        search_row = ctk.CTkFrame(header, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=5)
        
        # Auto-completion pour sorts
        self.spell_search = AutocompleteEntry(
            search_row,
            suggestions_source=self._get_spell_suggestions,
            placeholder="Nom du sort...",
            colors=self.colors,
            on_select=self.search_spell
        )
        self.spell_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self._create_button(search_row, "Chercher", self.search_spell, 100).pack(side="right")
        
        filter_frame = ctk.CTkFrame(header, fg_color="transparent")
        filter_frame.pack(pady=5)
        
        ctk.CTkLabel(filter_frame, text="Niveau:", text_color=self.colors['text']).pack(side="left", padx=5)
        self.spell_level = ctk.CTkOptionMenu(
            filter_frame, values=["Tous", "Cantrip", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=100
        )
        self.spell_level.set("Tous")
        self.spell_level.pack(side="left", padx=5)
        
        ctk.CTkLabel(filter_frame, text="Classe:", text_color=self.colors['text']).pack(side="left", padx=5)
        self.spell_class = ctk.CTkOptionMenu(
            filter_frame, values=["Toutes", "Wizard", "Cleric", "Druid", "Bard", "Sorcerer", "Warlock", "Paladin", "Ranger"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=100
        )
        self.spell_class.set("Toutes")
        self.spell_class.pack(side="left", padx=5)
        
        self.spell_display = ctk.CTkTextbox(self.tab_spell, font=("Courier", 11),
                                            fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        self.spell_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.spell_display.insert("end", "Recherche un sort par son nom.\nCommence a taper pour voir les suggestions.\n\nExemples: Fireball, Magic Missile, Cure Wounds...")
    
    def _setup_rules_tab(self):
        search_frame = ctk.CTkFrame(self.tab_rules, fg_color=self.colors['bg_med'])
        search_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(search_frame, text="REGLES D&D 5e", font=("Courier", 16, "bold"),
                    text_color=self.colors['gold']).pack(pady=5)
        
        input_row = ctk.CTkFrame(search_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=10, pady=5)
        
        # Auto-completion pour regles
        self.rule_search = AutocompleteEntry(
            input_row,
            suggestions_source=self._get_rule_suggestions,
            placeholder="Rechercher une regle...",
            colors=self.colors,
            on_select=self.search_rules
        )
        self.rule_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self._create_button(input_row, "Chercher", self.search_rules, 100).pack(side="right")
        
        self.rules_display = ctk.CTkTextbox(self.tab_rules, font=("Courier", 11),
                                            fg_color=self.colors['bg_light'], text_color=self.colors['text'])
        self.rules_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.rules_display.insert("end", "Recherche dans les regles officielles.\nCommence a taper pour voir les suggestions.\n\nExemples: combat, magie, repos, concentration...")
    
    def _setup_tools_tab(self):
        # Frame principale avec scroll
        tools_scroll = ctk.CTkScrollableFrame(self.tab_tools, fg_color=self.colors['bg_dark'])
        tools_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # ========== GENERATEUR DE NOMS ==========
        names_frame = ctk.CTkFrame(tools_scroll, fg_color=self.colors['bg_med'])
        names_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(names_frame, text="GENERATEUR DE NOMS", font=("Courier", 14, "bold"),
                    text_color=self.colors['gold']).pack(pady=8)
        
        name_options = ctk.CTkFrame(names_frame, fg_color="transparent")
        name_options.pack(pady=5)
        
        ctk.CTkLabel(name_options, text="Type:", text_color=self.colors['text']).pack(side="left", padx=5)
        self.name_type = ctk.CTkOptionMenu(
            name_options,
            values=[
                "Humain (M)", "Humain (F)", "Elfe (M)", "Elfe (F)", 
                "Nain (M)", "Nain (F)", "Halfelin (M)", "Halfelin (F)",
                "Orc", "Tiefling (M)", "Tiefling (F)", "Noble",
                "Taverne", "Boutique (Forge)", "Boutique (Magie)", "Boutique (General)",
                "Lieu/Ville", "Guilde", "Navire", "Sort", "Familier", "Demon/Diable", "Dragon"
            ],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=180
        )
        self.name_type.set("Humain (M)")
        self.name_type.pack(side="left", padx=5)
        
        self._create_button(name_options, "Generer", self.generate_name, 100).pack(side="left", padx=10)
        
        self.name_result = ctk.CTkLabel(names_frame, text="", font=("Courier", 16, "bold"),
                                        text_color=self.colors['orange'])
        self.name_result.pack(pady=10)
        
        # Historique des noms
        self.name_history = ctk.CTkTextbox(names_frame, font=("Courier", 10),
                                           fg_color=self.colors['bg_light'], text_color=self.colors['text'],
                                           height=120)
        self.name_history.pack(fill="x", padx=10, pady=(0, 10))
        self.name_history.insert("end", "Historique des noms generes:\n" + "-"*40 + "\n")
        
        # ========== GENERATEUR DE TRESOR ==========
        treasure_frame = ctk.CTkFrame(tools_scroll, fg_color=self.colors['bg_med'])
        treasure_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(treasure_frame, text="GENERATEUR DE TRESOR", font=("Courier", 14, "bold"),
                    text_color=self.colors['gold']).pack(pady=8)
        
        treasure_options = ctk.CTkFrame(treasure_frame, fg_color="transparent")
        treasure_options.pack(pady=5)
        
        ctk.CTkLabel(treasure_options, text="Niveau:", text_color=self.colors['text']).pack(side="left", padx=5)
        self.treasure_level = ctk.CTkOptionMenu(
            treasure_options,
            values=["Faible (CR 0-4)", "Moyen (CR 5-10)", "Eleve (CR 11-16)", "Epique (CR 17+)"],
            fg_color=self.colors['orange'], button_color=self.colors['orange'],
            button_hover_color=self.colors['red'], width=150
        )
        self.treasure_level.set("Moyen (CR 5-10)")
        self.treasure_level.pack(side="left", padx=5)
        
        self.treasure_magic = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(treasure_options, text="Inclure items magiques", variable=self.treasure_magic,
                       fg_color=self.colors['orange'], hover_color=self.colors['red'],
                       text_color=self.colors['text']).pack(side="left", padx=10)
        
        self._create_button(treasure_options, "Generer", self.generate_treasure, 100).pack(side="left", padx=10)
        
        self.treasure_display = ctk.CTkTextbox(treasure_frame, font=("Courier", 10),
                                               fg_color=self.colors['bg_light'], text_color=self.colors['text'],
                                               height=250)
        self.treasure_display.pack(fill="x", padx=10, pady=(5, 10))
        self.treasure_display.insert("end", "Generateur de tresor D&D 5e\n\nSelectionne un niveau de tresor et clique sur Generer.")
    
    def _create_initiative_panel(self):
        ctk.CTkLabel(self.side_panel, text="INITIATIVE", font=("Courier", 14, "bold"),
                    text_color=self.colors['gold']).pack(pady=10)
        
        add_frame = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        add_frame.pack(fill="x", padx=10)
        
        self.init_name = ctk.CTkEntry(add_frame, font=("Courier", 10),
                                      fg_color=self.colors['bg_light'], text_color=self.colors['text'],
                                      placeholder_text="Nom", width=120, height=28)
        self.init_name.pack(side="left", padx=(0, 3))
        
        self.init_value = ctk.CTkEntry(add_frame, font=("Courier", 10),
                                       fg_color=self.colors['bg_light'], text_color=self.colors['text'],
                                       placeholder_text="Init", width=45, height=28)
        self.init_value.pack(side="left", padx=(0, 3))
        
        self._create_button(add_frame, "+", self.add_to_initiative, 30, 28).pack(side="left")
        
        ctrl_frame = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=8)
        
        self._create_button(ctrl_frame, "Prec", lambda: (self.init_tracker.prev_turn(), self.update_initiative_display()), 60, 26).pack(side="left", padx=2)
        self._create_button(ctrl_frame, "Suiv", self.next_initiative, 60, 26).pack(side="left", padx=2)
        self._create_button(ctrl_frame, "Clear", self.clear_initiative, 55, 26).pack(side="left", padx=2)
        self._create_button(ctrl_frame, "d20", self.roll_all_initiative, 45, 26).pack(side="left", padx=2)
        
        self.init_display = ctk.CTkTextbox(self.side_panel, font=("Courier", 10),
                                           fg_color=self.colors['bg_light'], text_color=self.colors['text'], width=260)
        self.init_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.update_initiative_display()
    
    def _create_footer(self):
        footer = ctk.CTkFrame(self.root, fg_color=self.colors['red'], height=22)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        ctk.CTkLabel(footer, text="LM Studio / Ollama", font=("Courier", 9),
                    text_color=self.colors['gold']).pack(pady=2)
    
    def _create_button(self, parent, text, command, width, height=None):
        kwargs = {
            'master': parent, 'text': text, 'command': command, 'width': width,
            'fg_color': self.colors['orange'], 'hover_color': self.colors['red'],
            'text_color': "#000000", 'font': ("Courier", 10, "bold"),
            'corner_radius': 0, 'border_width': 2, 'border_color': "#8B4513"
        }
        if height:
            kwargs['height'] = height
        return ctk.CTkButton(**kwargs)
    
    # ============== Auto-completion ==============
    
    def _get_monster_suggestions(self, query: str) -> List[str]:
        query = query.lower()
        return [n for n in self.monster_names if query in n.lower()][:8]
    
    def _get_spell_suggestions(self, query: str) -> List[str]:
        query = query.lower()
        return [n for n in self.spell_names if query in n.lower()][:8]
    
    def _get_item_suggestions(self, query: str) -> List[str]:
        query = query.lower()
        return [n for n in self.item_names if query in n.lower()][:8]
    
    def _get_rule_suggestions(self, query: str) -> List[str]:
        query = query.lower()
        return [k for k in self.rule_keywords if query in k.lower()][:8]
    
    # ============== Systeme ==============
    
    def initialize_systems(self):
        self.update_status("Chargement...")
        try:
            self.model = DnDAssistantModel(use_ollama=False, model_name="qwen3-4b-thinking")
            if not self.model.is_available():
                self.model = DnDAssistantModel(use_ollama=True, model_name="llama2")
            
            self.rag = RAGSystem()
            self.monster_db = MonsterDatabase()
            
            if SpellDatabase:
                self.spell_db = SpellDatabase()
            if ItemDatabase:
                self.item_db = ItemDatabase()
            
            # Charger les noms pour l'auto-completion
            if self.monster_db and self.monster_db.df is not None:
                self.monster_names = self.monster_db.df['name'].dropna().tolist()
            if self.spell_db and self.spell_db.df is not None:
                self.spell_names = self.spell_db.df['name'].dropna().tolist()
            if self.item_db and self.item_db.df is not None:
                self.item_names = self.item_db.df['name'].dropna().tolist()
            
            if self.rag.collection.count() == 0:
                self.update_status("Indexation documents...")
                self.rag.index_documents()
            
            status = f"{self.model.backend}" if self.model and self.model.is_available() else "Pas de LLM"
            self.update_status(status)
        except Exception as e:
            self.update_status(f"Erreur: {str(e)[:25]}")
            print(f"[INIT] Erreur: {e}")
    
    def update_status(self, msg):
        self.status.configure(text=msg)
        self.root.update()
    
    # ============== Chat ==============
    
    def send_message(self):
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
            context = self.rag.get_context_for_query(msg) if self.rag else ""
            if self.model and self.model.is_available():
                response = self.model.generate_dm_response(msg, context)
            else:
                response = "LLM non disponible."
            
            self.chat_box.insert("end", f"\nMaitre du Donjon: {response}\n")
            self.chat_history.append({'role': 'assistant', 'content': response})
            self.chat_box.see("end")
            self.update_status("Pret")
        except Exception as e:
            self.chat_box.insert("end", f"\nErreur: {str(e)}\n")
            self.update_status("Erreur")
    
    def _send_to_display(self, display, prompt: str):
        self.update_status("Generation...")
        self.root.update()
        
        try:
            if self.model and self.model.is_available():
                response = self.model.generate_dm_response(prompt)
            else:
                response = "LLM non disponible."
            
            display.delete("1.0", "end")
            display.insert("end", response)
            self.update_status("Pret")
        except Exception as e:
            display.delete("1.0", "end")
            display.insert("end", f"Erreur: {str(e)}")
            self.update_status("Erreur")
    
    # ============== Generateurs ==============
    
    def generate_npc(self):
        npc_t = self.npc_type.get()
        race = self.npc_race.get()
        align = self.npc_align.get()
        with_quest = self.npc_quest.get()
        
        prompt = f"Genere un PNJ detaille pour D&D 5e.\nType: {npc_t}\n"
        prompt += f"Race: {race}\n" if race != "Aleatoire" else ""
        prompt += f"Alignement: {align}\n" if align != "Aleatoire" else ""
        prompt += "\nInclus: nom complet, age, apparence physique, personnalite, historique, motivations, et manieres de parler."
        if with_quest:
            prompt += "\nAjoute une quete ou mission qu'il pourrait proposer aux aventuriers."
        
        self._send_to_display(self.npc_display, prompt)
    
    def generate_building(self):
        btype = self.building_type.get()
        state = self.building_state.get()
        mood = self.building_mood.get()
        secret = self.building_secret.get()
        
        prompt = f"Genere une description detaillee d'un batiment pour D&D 5e.\n"
        prompt += f"Type: {btype}\nEtat: {state}\nAmbiance: {mood}\n"
        prompt += "\nInclus: nom du lieu, description exterieure, description interieure, occupants ou proprietaires, details interessants."
        if secret:
            prompt += "\nAjoute un secret cache ou un passage derobe."
        
        self._send_to_display(self.building_display, prompt)
    
    def generate_magic_item(self):
        rarity = self.item_rarity.get()
        itype = self.item_type.get()
        
        prompt = f"Genere un item magique unique pour D&D 5e.\n"
        prompt += f"Rarete: {rarity}\n" if rarity != "Aleatoire" else ""
        prompt += f"Type: {itype}\n" if itype != "Aleatoire" else ""
        prompt += "\nInclus: nom evocateur, rarete, type, description physique, proprietes magiques, conditions d'utilisation, et histoire/origine."
        
        self._send_to_display(self.item_display, prompt)
    
    def generate_name(self):
        category = self.name_type.get()
        result = NameGenerator.generate(category)
        self.name_result.configure(text=result)
        self.name_history.insert("end", f"[{category}] {result}\n")
        self.name_history.see("end")
    
    def generate_treasure(self):
        level = self.treasure_level.get()
        include_magic = self.treasure_magic.get()
        
        treasure = TreasureGenerator.generate(level, include_magic)
        formatted = TreasureGenerator.format_treasure(treasure)
        
        self.treasure_display.delete("1.0", "end")
        self.treasure_display.insert("end", formatted)
    
    # ============== Recherches ==============
    
    def search_monster(self):
        query = self.monster_search.get().strip()
        if not query:
            return
        
        self.update_status("Recherche...")
        self.monster_display.delete("1.0", "end")
        
        try:
            if not self.monster_db:
                self.monster_display.insert("end", "Base non chargee.")
                return
            
            monster = self.monster_db.search(query)
            if monster:
                self._display_monster(monster)
            else:
                self.monster_display.insert("end", f"Aucun monstre trouve pour '{query}'.")
            
            self.update_status("Pret")
        except Exception as e:
            self.monster_display.insert("end", f"Erreur: {str(e)}")
    
    def _display_monster(self, m: dict):
        name = m.get('name', 'Inconnu')
        self.monster_display.insert("end", f"{'='*50}\n  {name.upper()}\n{'='*50}\n\n")
        
        for key, label in [('size', 'Taille'), ('type', 'Type'), ('alignment', 'Alignement'),
                           ('cr', 'CR'), ('ac', 'CA'), ('hp', 'PV'), ('speed', 'Vitesse')]:
            if key in m and str(m[key]) != 'nan':
                self.monster_display.insert("end", f"{label}: {m[key]}\n")
        
        self.monster_display.insert("end", "\n")
        
        stats = ['str', 'dex', 'con', 'int', 'wis', 'cha']
        names = ['FOR', 'DEX', 'CON', 'INT', 'SAG', 'CHA']
        line = "  ".join(f"{names[i]}: {m.get(s, '-')}" for i, s in enumerate(stats) if s in m)
        if line:
            self.monster_display.insert("end", f"{line}\n\n")
        
        for key, label in [('skills', 'Competences'), ('senses', 'Sens'), ('languages', 'Langues'),
                           ('resistances', 'Resistances'), ('immunities', 'Immunites')]:
            if key in m and str(m[key]) != 'nan':
                self.monster_display.insert("end", f"{label}: {m[key]}\n")
        
        if 'full_text' in m and str(m['full_text']) != 'nan':
            self.monster_display.insert("end", f"\n{'='*50}\nDETAILS\n{'='*50}\n\n{m['full_text']}")
    
    def search_item(self):
        query = self.item_search.get().strip()
        if not query:
            return
        
        self.update_status("Recherche...")
        self.item_display.delete("1.0", "end")
        
        try:
            if self.item_db:
                item = self.item_db.search(query)
                if item:
                    self._display_item(item)
                    self.update_status("Pret")
                    return
            
            self.item_display.insert("end", f"Item '{query}' non trouve.\nUtilisez 'Generer' pour creer un item magique.")
            self.update_status("Pret")
        except Exception as e:
            self.item_display.insert("end", f"Erreur: {str(e)}")
    
    def _display_item(self, item: dict):
        name = item.get('name', 'Inconnu')
        self.item_display.insert("end", f"{'='*50}\n  {name.upper()}\n{'='*50}\n\n")
        
        for key, label in [('category', 'Categorie'), ('rarity', 'Rarete'), 
                           ('classification', 'Type'), ('ac', 'CA'), 
                           ('damage', 'Degats'), ('damage_type', 'Type degats'),
                           ('properties', 'Proprietes'), ('cost', 'Cout')]:
            if key in item and str(item[key]) != 'nan' and item[key]:
                self.item_display.insert("end", f"{label}: {item[key]}\n")
        
        if 'description' in item and str(item['description']) != 'nan':
            self.item_display.insert("end", f"\n{item['description']}")
    
    def search_spell(self):
        query = self.spell_search.get().strip()
        if not query:
            return
        
        self.update_status("Recherche...")
        self.spell_display.delete("1.0", "end")
        
        try:
            if self.spell_db:
                spell = self.spell_db.search(query)
                if spell:
                    self._display_spell(spell)
                    self.update_status("Pret")
                    return
            
            self.spell_display.insert("end", f"Sort '{query}' non trouve.")
            self.update_status("Pret")
        except Exception as e:
            self.spell_display.insert("end", f"Erreur: {str(e)}")
    
    def _display_spell(self, spell: dict):
        name = spell.get('name', 'Inconnu')
        self.spell_display.insert("end", f"{'='*50}\n  {name.upper()}\n{'='*50}\n\n")
        
        for key, label in [('level', 'Niveau'), ('school', 'Ecole'), ('classes', 'Classes'),
                           ('casting_time', 'Temps incantation'), ('range', 'Portee'), ('duration', 'Duree')]:
            if key in spell and str(spell[key]) != 'nan':
                self.spell_display.insert("end", f"{label}: {spell[key]}\n")
        
        comps = []
        if spell.get('component_v'): comps.append('V')
        if spell.get('component_s'): comps.append('S')
        if spell.get('component_m'): comps.append('M')
        if comps:
            self.spell_display.insert("end", f"Composantes: {', '.join(comps)}\n")
        if spell.get('materials') and str(spell['materials']) != 'nan':
            self.spell_display.insert("end", f"Materiaux: {spell['materials']}\n")
        
        if spell.get('ritual'):
            self.spell_display.insert("end", "Rituel: Oui\n")
        
        if 'description' in spell and str(spell['description']) != 'nan':
            desc = str(spell['description']).replace('<br />', '\n').replace('<br/>', '\n')
            self.spell_display.insert("end", f"\n{desc}")
        
        if 'higher_levels' in spell and str(spell['higher_levels']) != 'nan':
            self.spell_display.insert("end", f"\n\nA plus haut niveau: {spell['higher_levels']}")
    
    def search_rules(self):
        query = self.rule_search.get().strip()
        if not query:
            return
        
        self.update_status("Recherche...")
        self.rules_display.delete("1.0", "end")
        
        try:
            if self.rag:
                result = self.rag.search_rule(query)
                self.rules_display.insert("end", result)
            else:
                self.rules_display.insert("end", "Systeme RAG non charge.")
            
            self.update_status("Pret")
        except Exception as e:
            self.rules_display.insert("end", f"Erreur: {str(e)}")
    
    # ============== Initiative ==============
    
    def add_to_initiative(self):
        name = self.init_name.get().strip()
        try:
            init = int(self.init_value.get().strip())
        except ValueError:
            messagebox.showerror("Erreur", "Initiative invalide")
            return
        
        if self.init_tracker.add(name, init):
            self.init_name.delete(0, "end")
            self.init_value.delete(0, "end")
            self.update_initiative_display()
        else:
            messagebox.showerror("Erreur", "Nom vide ou initiative hors limites")
    
    def next_initiative(self):
        self.init_tracker.next_turn()
        self.update_initiative_display()
    
    def clear_initiative(self):
        self.init_tracker.clear()
        self.update_initiative_display()
    
    def roll_all_initiative(self):
        for c in self.init_tracker.creatures:
            c['initiative'] = random.randint(1, 20)
        self.init_tracker.creatures.sort(key=lambda x: x['initiative'], reverse=True)
        self.update_initiative_display()
    
    def update_initiative_display(self):
        self.init_display.delete("1.0", "end")
        self.init_display.insert("end", f"ROUND {self.init_tracker.round_number}\n{'-'*28}\n\n")
        
        current = self.init_tracker.get_current()
        for c in self.init_tracker.creatures:
            marker = "> " if c == current else "  "
            name = c['name'][:18].ljust(18)
            init = str(c['initiative']).rjust(2)
            self.init_display.insert("end", f"{marker}{name} [{init}]\n")
        
        if not self.init_tracker.creatures:
            self.init_display.insert("end", "Aucune creature\n")
    
    def run(self):
        self.root.mainloop()


def main():
    app = DnDAssistantGUI()
    app.run()


if __name__ == "__main__":
    main()
