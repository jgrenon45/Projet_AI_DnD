"""
Main agent for D&D Assistant
Orchestrates RAG, LLM, and database components
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

from tools.model import DnDAssistantModel
from tools.rag import RAGSystem
from tools.db import MonsterDatabase, CampaignDatabase


class DnDAgent:
    """Main agent that coordinates all systems"""
    
    def __init__(self, use_ollama: bool = True, model_name: str = "llama2"):
        """
        Initialize the D&D Agent
        
        Args:
            use_ollama: Use Ollama (True) or LM Studio (False)
            model_name: Name of the model to use
        """
        print(" Initializing D&D Assistant Agent...")
        
        # Initialize components
        self.model = DnDAssistantModel(use_ollama=use_ollama, model_name=model_name)
        self.rag = RAGSystem()
        self.monster_db = MonsterDatabase()
        self.campaign_db = CampaignDatabase()
        
        # Check system status
        self.check_system_status()
        
        # Index documents if needed
        if self.rag.collection.count() == 0:
            print("\n Indexing D&D documents for the first time...")
            print("This may take a few minutes...")
            self.rag.index_documents()
    
    def check_system_status(self):
        """Check status of all systems"""
        print("\n" + "="*60)
        print("SYSTEM STATUS")
        print("="*60)
        
        # LLM Model
        if self.model.is_available():
            print(f" LLM Model: {self.model.backend} - Ready")
        else:
            print(" LLM Model: Not available")
            print("   Please start Ollama or LM Studio")
        
        # RAG System
        doc_count = self.rag.collection.count()
        if doc_count > 0:
            print(f" RAG System: {doc_count} document chunks indexed")
        else:
            print("  RAG System: No documents indexed yet")
        
        # Monster Database
        if self.monster_db.df is not None and not self.monster_db.df.empty:
            print(f" Monster Database: {len(self.monster_db.df)} monsters loaded")
        else:
            print("  Monster Database: No monsters loaded")
        
        print("="*60 + "\n")
    
    def query(self, user_query: str, use_rag: bool = True) -> str:
        """
        Process user query
        
        Args:
            user_query: The user's question
            use_rag: Whether to use RAG for context
            
        Returns:
            Agent's response
        """
        if not self.model.is_available():
            return " No LLM model available. Please start Ollama or LM Studio."
        
        # Determine if query needs RAG context
        context = ""
        if use_rag and self._should_use_rag(user_query):
            print(" Searching documents...")
            context = self.rag.get_context_for_query(user_query, n_results=3)
        
        # Generate response
        print(" Generating response...")
        response = self.model.generate_dm_response(user_query, context)
        
        return response
    
    def _should_use_rag(self, query: str) -> bool:
        """Determine if query should use RAG"""
        rag_keywords = [
            'rule', 'règle', 'how', 'comment',
            'what', 'quoi', 'explain', 'explique',
            'spell', 'sort', 'class', 'classe',
            'feature', 'ability', 'capacité'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in rag_keywords)
    
    def search_monster(self, monster_name: str) -> Optional[Dict]:
        """Search for a monster"""
        return self.monster_db.search_monster(monster_name)
    
    def get_monsters_by_cr(self, cr_min: float, cr_max: float) -> List[Dict]:
        """Get monsters by CR range"""
        return self.monster_db.get_monsters_by_cr(cr_min, cr_max)
    
    def search_rule(self, rule_query: str) -> str:
        """Search for a rule in documents"""
        return self.rag.search_rule(rule_query)
    
    def generate_encounter(self, party_level: int, difficulty: str = "medium") -> str:
        """Generate combat encounter"""
        return self.model.generate_encounter(party_level, difficulty)
    
    def generate_npc(self, npc_type: str = "random") -> str:
        """Generate NPC"""
        return self.model.generate_npc(npc_type)
    
    def add_session_notes(self, title: str, notes: str) -> int:
        """Add session notes to campaign database"""
        return self.campaign_db.add_session(title, notes)
    
    def interactive_mode(self):
        """Run in interactive command-line mode"""
        print("\n" + "="*60)
        print("  D&D ASSISTANT - Interactive Mode  ")
        print("="*60)
        print("\nCommands:")
        print("  /monster <name>  - Search for a monster")
        print("  /rule <query>    - Search rules")
        print("  /npc             - Generate NPC")
        print("  /encounter <lvl> - Generate encounter")
        print("  /quit            - Exit")
        print("\nOr just ask any question!")
        print("="*60 + "\n")
        
        while True:
            try:
                user_input = input("\n You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    self._handle_command(user_input)
                else:
                    # Regular query
                    response = self.query(user_input)
                    print(f"\n🐉 DM Assistant: {response}")
                    
            except KeyboardInterrupt:
                print("\n\n Farewell, Dungeon Master!")
                break
            except Exception as e:
                print(f"\n Error: {str(e)}")
    
    def _handle_command(self, command: str):
        """Handle special commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd == '/quit' or cmd == '/exit':
            print("\n Farewell, Dungeon Master!")
            sys.exit(0)
        
        elif cmd == '/monster':
            if not arg:
                print("Usage: /monster <name>")
                return
            
            monster = self.search_monster(arg)
            if monster:
                print(f"\n  {monster['name']}")
                for key, value in monster.items():
                    if key != 'name':
                        print(f"   {key}: {value}")
            else:
                print(f"Monster '{arg}' not found")
        
        elif cmd == '/rule':
            if not arg:
                print("Usage: /rule <query>")
                return
            
            result = self.search_rule(arg)
            print(f"\n{result}")
        
        elif cmd == '/npc':
            npc_type = arg if arg else "random"
            npc = self.generate_npc(npc_type)
            print(f"\n Generated NPC:\n{npc}")
        
        elif cmd == '/encounter':
            try:
                level = int(arg) if arg else 5
                encounter = self.generate_encounter(level)
                print(f"\n  Encounter:\n{encounter}")
            except ValueError:
                print("Usage: /encounter <level>")
        
        else:
            print(f"Unknown command: {cmd}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="D&D Assistant Agent")
    parser.add_argument('--backend', choices=['ollama', 'lmstudio'], 
                       default='ollama', help='LLM backend to use')
    parser.add_argument('--model', default='llama2', 
                       help='Model name to use')
    parser.add_argument('--gui', action='store_true',
                       help='Launch GUI instead of CLI')
    parser.add_argument('--reindex', action='store_true',
                       help='Force reindex of documents')
    
    args = parser.parse_args()
    
    # Launch GUI if requested
    if args.gui:
        from tools.UserGUI.GUI import main as gui_main
        gui_main()
        return
    
    # Create agent
    use_ollama = args.backend == 'ollama'
    agent = DnDAgent(use_ollama=use_ollama, model_name=args.model)
    
    # Reindex if requested
    if args.reindex:
        print("\n Reindexing documents...")
        agent.rag.index_documents(force_reindex=True)
    
    # Run interactive mode
    agent.interactive_mode()


if __name__ == "__main__":
    main()