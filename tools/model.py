"""
LLM Model management for D&D Assistant
Supports both Ollama and LM Studio
"""

import requests
import json
from requests.exceptions import ReadTimeout, ConnectionError, RequestException
from typing import Optional, Dict, List
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """
    Configuration for LLM models.
    Utilisé pour définir les paramètres généraux pour Ollama et LM Studio.
    """
    model_name: str = "llama2"  # Nom du modèle (ex: llama2, mistral)
    temperature: float = 0.7    # Contrôle la créativité / variance des réponses
    max_tokens: int = 8096      # Nombre maximum de tokens générés
    top_p: float = 0.9          # Paramètre nucleus sampling
    top_k: int = 40             # Paramètre top-k sampling


@dataclass
class NPC:
    """Represents a Non-Player Character in D&D 5e"""
    name: str
    race: str
    character_class: str
    personality: str
    quest: str
    npc_type: str = "random"
    raw_description: str = ""  # Stocke la description complète du LLM


@dataclass
class Monster:
    """Represents a monster in an encounter"""
    name: str
    count: int
    challenge_rating: Optional[float] = None
    role: Optional[str] = None  # e.g., "brute", "controller", "leader"


@dataclass
class Encounter:
    """Represents a combat encounter in D&D 5e"""
    monsters: List[Monster] = field(default_factory=list)
    difficulty: str = "medium"
    party_level: int = 1
    description: str = ""
    tactics: str = ""
    total_xp: Optional[int] = None
    raw_description: str = ""  # Stocke la description complète du LLM


@dataclass
class Rule:
    """Represents a D&D 5e rule explanation"""
    query: str
    explanation: str
    source: Optional[str] = None  # e.g., "Player's Handbook", "Basic Rules"
    raw_explanation: str = ""  # Stocke l'explication complète du LLM


class OllamaModel:
    """Interface pour interagir avec Ollama LLM via HTTP API"""
    
    def __init__(self, config: ModelConfig, base_url: str = "http://localhost:11434"):
        """
        Initialise le modèle Ollama.
        
        Args:
            config (ModelConfig): Paramètres du modèle
            base_url (str): URL locale de l'API Ollama
        """
        self.config = config
        self.base_url = base_url
        self.is_available = self.check_availability()  # Vérifie si le serveur Ollama est actif
    
    def check_availability(self) -> bool:
        """Vérifie si Ollama est en fonctionnement via endpoint /api/tags"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False  # Retourne False si le serveur n'est pas joignable
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Génère une réponse textuelle depuis Ollama.
        
        Args:
            prompt (str): Texte d'entrée utilisateur
            system_prompt (Optional[str]): Contexte ou instructions système
        """
        if not self.is_available:
            return "Ollama n'est pas disponible. Assurez-vous qu'il est lancé."
        
        try:
            # Préparation du payload JSON pour la requête
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt  # Ajoute le contexte système si fourni
            
            # Appel POST à l'API Ollama pour générer la réponse
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()["response"]  # Retourne le texte généré
            else:
                return f"Erreur: {response.status_code}"
                
        except ReadTimeout:
            return ("Timeout: Ollama n'a pas repondu dans les delais. "
                    "Verifiez que le service Ollama est lance et accessible.")
        except ConnectionError:
            return "Connexion refusee: Impossible de joindre Ollama sur le port configure."
        except RequestException as e:
            return f"Erreur reseau vers Ollama: {str(e)}"
        except Exception as e:
            return f"Erreur lors de la génération: {str(e)}"
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Génération basée sur le chat (messages structurés).
        
        Args:
            messages (List[Dict[str,str]]): Liste de messages [{role: "user"/"system", content: "..."}, ...]
        """
        if not self.is_available:
            return "Ollama n'est pas disponible."
        
        try:
            payload = {
                "model": self.config.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                # Extraction du contenu de la réponse
                return response.json()["message"]["content"]
            else:
                return f"Erreur: {response.status_code}"
                
        except ReadTimeout:
            return ("Timeout: Ollama n'a pas repondu dans les delais. "
                    "Verifiez que le service Ollama est lance et accessible.")
        except ConnectionError:
            return "Connexion refusee: Impossible de joindre Ollama sur le port configure."
        except RequestException as e:
            return f"Erreur reseau vers Ollama: {str(e)}"
        except ReadTimeout:
            return ("Timeout: LM Studio n'a pas repondu dans les delais (port 1234). "
                    "Verifiez que LM Studio est lance et qu'un modele est charge.")
        except ConnectionError:
            return ("Connexion refusee: Impossible de joindre LM Studio sur "
                    "http://localhost:1234. Assurez-vous que le service est demarre.")
        except RequestException as e:
            return f"Erreur reseau vers LM Studio: {str(e)}"
        except Exception as e:
            return f"Erreur: {str(e)}"


class LMStudioModel:
    """Interface pour interagir avec LM Studio LLM via API OpenAI-compatible"""
    
    def __init__(self, config: ModelConfig, base_url: str = "http://localhost:1234/v1"):
        """
        Initialise le modèle LM Studio.
        
        Args:
            config (ModelConfig): Paramètres du modèle
            base_url (str): URL locale de l'API LM Studio
        """
        self.config = config
        self.base_url = base_url
        self.is_available = self.check_availability()  # Vérifie si le serveur est actif
    
    def check_availability(self) -> bool:
        """Vérifie si LM Studio est en fonctionnement via endpoint /models"""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Génère une réponse depuis LM Studio.
        
        Args:
            prompt (str): Texte utilisateur
            system_prompt (Optional[str]): Instructions système
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.chat(messages)
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Génération basée sur chat (OpenAI-compatible API).
        
        Args:
            messages (List[Dict[str,str]]): Messages structurés
        """
        if not self.is_available:
            return "LM Studio n'est pas disponible. Assurez-vous qu'un modèle est chargé."
        
        try:
            payload = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "top_p": self.config.top_p
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            if response.status_code == 200:
                # Retourne le contenu du message généré
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"Erreur: {response.status_code}"
                
        except Exception as e:
            return f"Erreur: {str(e)}"


class DnDAssistantModel:
    """Gestionnaire principal de LLM pour l'assistant D&D"""
    
    def __init__(self, use_ollama: bool = True, model_name: str = "qwen/qwen3-vl-8b"):
        """
        Initialise le gestionnaire et choisit le backend disponible.
        
        Args:
            use_ollama (bool): Priorise Ollama si disponible
            model_name (str): Nom du modèle à utiliser
        """
        self.config = ModelConfig(model_name=model_name)
        
        # Création des objets backend
        self.ollama = OllamaModel(self.config)
        self.lmstudio = LMStudioModel(self.config)
        
        # Sélection du backend disponible
        if self.lmstudio.is_available:
            self.active_model = self.lmstudio
            self.backend = "LM Studio"
        else:
            self.active_model = None
            self.backend = "None"
    
    def is_available(self) -> bool:
        """Retourne True si un modèle LLM est disponible"""
        return self.active_model is not None
    
    def _parse_npc_response(self, response: str) -> NPC:
        """
        Parse LLM response into NPC object.
        
        Args:
            response (str): Raw response from LLM
            npc_type (str): Type of NPC generated
            
        Returns:
            NPC: Parsed NPC object
        """
        # Extract structured fields from response
        lines = response.split('\n')
        npc_data = {
            'name': 'Unknown',
            'race': 'Unknown',
            'character_class': 'Unknown',
            'personality': '',
            'quest': '',
            'npc_type': "Unknown",
            'raw_description': response
        }
        
        for line in lines:
            line_lower = line.lower()
            if 'nom' in line_lower or 'name' in line_lower:
                npc_data['name'] = line.split(':', 1)[-1].strip()
            elif 'race' in line_lower:
                npc_data['race'] = line.split(':', 1)[-1].strip()
            elif 'classe' in line_lower or 'class' in line_lower:
                npc_data['character_class'] = line.split(':', 1)[-1].strip()
            elif 'personnalité' in line_lower or 'personality' in line_lower:
                npc_data['personality'] = line.split(':', 1)[-1].strip()
            elif 'quête' in line_lower or 'quest' in line_lower:
                npc_data['quest'] = line.split(':', 1)[-1].strip()
            elif 'type' in line_lower:
                npc_data['npc_type'] = line.split(':', 1)[-1].strip()
        
        return NPC(**npc_data)
    
    def _parse_encounter_response(self, response: str, party_level: int, difficulty: str) -> Encounter:
        """
        Parse LLM response into Encounter object.
        
        Args:
            response (str): Raw response from LLM
            party_level (int): Party level for encounter
            difficulty (str): Difficulty level
            
        Returns:
            Encounter: Parsed Encounter object
        """
        encounter = Encounter(
            difficulty=difficulty,
            party_level=party_level,
            raw_description=response
        )
        
        # Basic parsing of monsters from response
        lines = response.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['monstres', 'monsters', 'créatures', 'creatures', 'ennemis', 'enemies']):
                # This is a section header, next lines contain monsters
                continue
            
            # Try to extract monster information (name, count, CR)
            if any(char.isdigit() for char in line):
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        # Simple extraction: "Monster Name x Count"
                        name_part = parts[0].strip()
                        count = 1
                        
                        # Try to extract count (e.g., "x 3" or "3x")
                        for i, part in enumerate(parts):
                            if 'x' in part.lower():
                                try:
                                    count = int(''.join(filter(str.isdigit, part)))
                                    break
                                except:
                                    pass
                        
                        monster = Monster(name=name_part, count=count)
                        encounter.monsters.append(monster)
                    except:
                        pass
        
        # Extract tactics and description
        if 'tactique' in response.lower() or 'tactics' in response.lower():
            parts = response.split('tactique' if 'tactique' in response.lower() else 'tactics', 1)
            if len(parts) > 1:
                encounter.tactics = parts[1].strip()
        
        encounter.description = response[:300] + "..." if len(response) > 300 else response
        
        return encounter
    
    def _parse_rule_response(self, response: str, rule_query: str) -> Rule:
        """
        Parse LLM response into Rule object.
        
        Args:
            response (str): Raw response from LLM
            rule_query (str): Original rule query
            
        Returns:
            Rule: Parsed Rule object
        """
        rule_data = {
            'query': rule_query,
            'explanation': response,
            'source': None,
            'raw_explanation': response
        }
        
        # Try to extract source from response
        sources = ["Player's Handbook", "Basic Rules", "Monster Manual", "Xanathar's", "Tasha's", "DMG"]
        for source in sources:
            if source.lower() in response.lower():
                rule_data['source'] = source
                break
        
        return Rule(**rule_data)
    
    
    def generate_dm_response(self, query: str, context: str = "") -> str:
        """
        Génère une réponse de type Dungeon Master (DM).
        
        Args:
            query (str): Question ou demande
            context (str): Contexte additionnel pour la question
        """
        if not self.is_available():
            return "Aucun modèle LLM n'est disponible. Lancez Ollama ou LM Studio."
        
        # Prompt système pour guider le style de réponse
        system_prompt = """Tu es un assistant Maître du Donjon expert en D&D 5e.
Tu aides les DM avec les règles, les monstres, les idées de scénarios et la gestion des sessions.
Réponds de manière concise et précise.
Si tu cites les règles, mentionne la source (Player's Handbook, Basic Rules, etc.)."""
        
        if context:
            query = f"Contexte:\n{context}\n\nQuestion: {query}"
        
        return self.active_model.generate(query, system_prompt)
    
    def generate_npc(self, prompt: str) -> NPC:
        """
        Génère une description de PNJ pour D&D 5e.
        
        Args:
            prompt (str): Prompt personnalisé pour le PNJ
            npc_type (str): Type de PNJ à générer (ex: "méchant", "allié", ou "random")
            
        Returns:
            NPC: Parsed NPC object
        """ 
        response = self.generate_dm_response(prompt)
        return self._parse_npc_response(response)

    def generate_encounter(self, prompt: str, party_level: int, difficulty: str = "medium") -> Encounter:
        """
        Génère une rencontre de combat adaptée au niveau du groupe.
        
        Args:
            party_level (int): Niveau moyen du groupe
            difficulty (str): Difficulté ("easy", "medium", "hard")
            
        Returns:
            Encounter: Parsed Encounter object
        """    

        response = self.generate_dm_response(prompt)
        return self._parse_encounter_response(response, party_level, difficulty)

    def explain_rule(self, rule_query: str) -> Rule:
        """
        Explique une règle de D&D 5e.
        
        Args:
            rule_query (str): Question sur la règle
            
        Returns:
            Rule: Parsed Rule object with explanation and source
        """
        prompt = f"Explique cette règle de D&D 5e: {rule_query}"
        response = self.generate_dm_response(prompt)
        return self._parse_rule_response(response, rule_query)
