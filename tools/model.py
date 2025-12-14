"""
LLM Model management v2 pour D&D Assistant
Support Ollama et LM Studio avec prompt systeme ameliore
"""

import requests
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration du modele LLM"""
    model_name: str = "llama2"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40


class OllamaModel:
    """Interface Ollama"""
    
    def __init__(self, config: ModelConfig, base_url: str = "http://localhost:11434"):
        self.config = config
        self.base_url = base_url
        self.is_available = self._check_availability()
    
    def _check_availability(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.is_available:
            return "Ollama non disponible."
        
        try:
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
                payload["system"] = system_prompt
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["response"]
            return f"Erreur: {response.status_code}"
            
        except Exception as e:
            return f"Erreur: {str(e)}"
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.is_available:
            return "Ollama non disponible."
        
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
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["message"]["content"]
            return f"Erreur: {response.status_code}"
            
        except Exception as e:
            return f"Erreur: {str(e)}"


class LMStudioModel:
    """Interface LM Studio (API OpenAI-compatible)"""
    
    def __init__(self, config: ModelConfig, base_url: str = "http://localhost:1234/v1"):
        self.config = config
        self.base_url = base_url
        self.is_available = self._check_availability()
    
    def _check_availability(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/models", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages)
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.is_available:
            return "LM Studio non disponible."
        
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
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            return f"Erreur: {response.status_code}"
            
        except Exception as e:
            return f"Erreur: {str(e)}"


class DnDAssistantModel:
    """Gestionnaire principal LLM pour l'assistant D&D"""
    
    # Prompt systeme professionnel, sans emoji
    SYSTEM_PROMPT = """Tu es un Maitre du Donjon expert en Dungeons & Dragons 5e.

Ton role:
- Repondre aux questions sur les regles D&D 5e de maniere precise et concise
- Aider a la preparation et gestion des sessions de jeu
- Generer du contenu creatif (PNJ, rencontres, donjons, quetes)
- Fournir des conseils tactiques et narratifs

Style de reponse:
- Ton serieux et immersif, digne d'un vrai Maitre du Donjon
- Reponses structurees mais pas trop longues
- Cite les sources quand tu mentionnes des regles (PHB, DMG, etc.)
- Pas d'emoji ni de formulations excessivement enthousiastes

Si tu utilises du contexte fourni, base-toi dessus mais n'hesite pas a completer avec tes connaissances."""

    def __init__(self, use_ollama: bool = True, model_name: str = "llama2"):
        self.config = ModelConfig(model_name=model_name)
        
        self.ollama = OllamaModel(self.config)
        self.lmstudio = LMStudioModel(self.config)
        
        if use_ollama and self.ollama.is_available:
            self.active_model = self.ollama
            self.backend = "Ollama"
        elif self.lmstudio.is_available:
            self.active_model = self.lmstudio
            self.backend = "LM Studio"
        else:
            self.active_model = None
            self.backend = "Aucun"
    
    def is_available(self) -> bool:
        return self.active_model is not None
    
    def generate_dm_response(self, query: str, context: str = "") -> str:
        """Genere une reponse de Maitre du Donjon"""
        if not self.is_available():
            return "Aucun modele LLM disponible. Lancez Ollama ou LM Studio."
        
        if context:
            full_query = f"Contexte de reference:\n{context}\n\n---\n\nQuestion: {query}"
        else:
            full_query = query
        
        return self.active_model.generate(full_query, self.SYSTEM_PROMPT)
    
    def generate_npc(self, npc_type: str = "aleatoire") -> str:
        """Genere un PNJ"""
        prompt = f"Genere un PNJ de type {npc_type} pour D&D 5e. "
        prompt += "Inclus: nom, race, classe ou profession, apparence, personnalite, et motivation."
        return self.generate_dm_response(prompt)
    
    def generate_encounter(self, party_level: int, difficulty: str = "moyenne") -> str:
        """Genere une rencontre"""
        prompt = f"Cree une rencontre de difficulte {difficulty} pour un groupe de niveau {party_level}. "
        prompt += "Inclus: monstres, nombre, tactiques, et description de la scene."
        return self.generate_dm_response(prompt)
    
    def explain_rule(self, rule_query: str) -> str:
        """Explique une regle"""
        prompt = f"Explique cette regle de D&D 5e: {rule_query}"
        return self.generate_dm_response(prompt)
