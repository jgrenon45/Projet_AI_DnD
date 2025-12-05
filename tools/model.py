"""
LLM Model management for D&D Assistant
Supports both Ollama and LM Studio
"""

import requests
import json
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """
    Configuration for LLM models.
    Utilisé pour définir les paramètres généraux pour Ollama et LM Studio.
    """
    model_name: str = "llama2"  # Nom du modèle (ex: llama2, mistral)
    temperature: float = 0.7    # Contrôle la créativité / variance des réponses
    max_tokens: int = 2048      # Nombre maximum de tokens générés
    top_p: float = 0.9          # Paramètre nucleus sampling
    top_k: int = 40             # Paramètre top-k sampling


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
                json=payload,
                timeout=60
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
        if use_ollama and self.ollama.is_available:
            self.active_model = self.ollama
            self.backend = "Ollama"
        elif self.lmstudio.is_available:
            self.active_model = self.lmstudio
            self.backend = "LM Studio"
        else:
            self.active_model = None
            self.backend = "None"
    
    def is_available(self) -> bool:
        """Retourne True si un modèle LLM est disponible"""
        return self.active_model is not None
    
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
    
    def generate_npc(self, npc_type: str = "random") -> str:
        """
        Génère une description de PNJ pour D&D 5e.
        
        Args:
            npc_type (str): Type de PNJ à générer (ex: "méchant", "allié", ou "random")
        """
        prompt = f"Génère un PNJ {npc_type} pour D&D 5e avec: nom, race, classe, personnalité, et une quête potentielle. Sois créatif et concis."
        return self.generate_dm_response(prompt)
    
    def generate_encounter(self, party_level: int, difficulty: str = "medium") -> str:
        """
        Génère une rencontre de combat adaptée au niveau du groupe.
        
        Args:
            party_level (int): Niveau moyen du groupe
            difficulty (str): Difficulté ("easy", "medium", "hard")
        """
        prompt = f"Crée une rencontre de combat {difficulty} pour un groupe de niveau {party_level}. Inclus les monstres, leur nombre, et la tactique recommandée."
        return self.generate_dm_response(prompt)
    
    def explain_rule(self, rule_query: str) -> str:
        """
        Explique une règle de D&D 5e.
        
        Args:
            rule_query (str): Question sur la règle
        """
        prompt = f"Explique cette règle de D&D 5e: {rule_query}"
        return self.generate_dm_response(prompt)
