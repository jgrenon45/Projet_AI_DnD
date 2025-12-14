"""
RAG System v2 - Retrieval-Augmented Generation optimise pour D&D
Ameliorations:
- Chunks plus petits (250 mots) pour une meilleure precision
- Overlap plus grand (75 mots) pour la continuite semantique
- Reformulation automatique des requetes
- Meilleur scoring et filtrage des resultats
"""

import os
from pathlib import Path
from typing import List, Optional, Dict
import re

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

import chromadb
from sentence_transformers import SentenceTransformer


class DocumentProcessor:
    """Processeur de documents PDF optimise pour D&D"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.documents = []
    
    def load_pdf(self, pdf_path: str) -> List[Dict]:
        """Charge un PDF et extrait le texte page par page"""
        texts = []
        try:
            reader = PdfReader(pdf_path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    # Nettoyage du texte
                    text = self._clean_text(text)
                    if len(text) > 50:  # Ignorer pages quasi-vides
                        texts.append({
                            'text': text,
                            'source': Path(pdf_path).name,
                            'page': page_num + 1
                        })
            print(f"[RAG] Charge {len(texts)} pages depuis {Path(pdf_path).name}")
        except Exception as e:
            print(f"[RAG] Erreur chargement {pdf_path}: {e}")
        return texts
    
    def _clean_text(self, text: str) -> str:
        """Nettoie le texte extrait du PDF"""
        # Normaliser les espaces
        text = re.sub(r'\s+', ' ', text)
        # Supprimer caracteres speciaux problematiques
        text = re.sub(r'[^\w\s.,;:!?\'"-]', '', text)
        return text.strip()
    
    def load_all_pdfs(self) -> List[Dict]:
        """Charge tous les PDFs et documents texte du repertoire data"""
        all_texts = []
        
        # PDFs
        pdf_files = [
            self.data_dir / "DnD_BasicRules_2018.pdf",
            self.data_dir / "PlayerHandbook.pdf"
        ]
        
        for pdf_path in pdf_files:
            if pdf_path.exists():
                texts = self.load_pdf(str(pdf_path))
                all_texts.extend(texts)
            else:
                print(f"[RAG] PDF non trouve: {pdf_path}")
        
        # Document de reference texte
        ref_file = self.data_dir / "DnD_Reference_Guide.txt"
        if ref_file.exists():
            texts = self.load_text_file(str(ref_file))
            all_texts.extend(texts)
        
        self.documents = all_texts
        return all_texts
    
    def load_text_file(self, file_path: str) -> List[Dict]:
        """Charge un fichier texte et le decoupe en sections"""
        texts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Decouper par chapitres (lignes avec ===)
            sections = content.split('=' * 80)
            
            for i, section in enumerate(sections):
                section = section.strip()
                if section and len(section) > 100:
                    # Nettoyer
                    section = self._clean_text(section)
                    texts.append({
                        'text': section,
                        'source': Path(file_path).name,
                        'page': i + 1
                    })
            
            print(f"[RAG] Charge {len(texts)} sections depuis {Path(file_path).name}")
        except Exception as e:
            print(f"[RAG] Erreur chargement {file_path}: {e}")
        
        return texts
    
    def chunk_text(self, text: str, chunk_size: int = 250, overlap: int = 75) -> List[str]:
        """
        Decoupe le texte en chunks avec chevauchement
        
        Args:
            chunk_size: Nombre de mots par chunk (250 = optimal pour D&D)
            overlap: Chevauchement entre chunks (75 = 30% du chunk)
        """
        words = text.split()
        chunks = []
        
        if len(words) <= chunk_size:
            return [text] if text.strip() else []
        
        step = chunk_size - overlap
        for i in range(0, len(words), step):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks


class RAGSystem:
    """Systeme RAG optimise pour les documents D&D"""
    
    # Mots-cles D&D pour enrichir les recherches
    DND_SYNONYMS = {
        'attaque': ['attack', 'hit', 'strike', 'damage', 'melee', 'ranged'],
        'defense': ['armor', 'ac', 'shield', 'protection', 'defense'],
        'magie': ['magic', 'spell', 'spellcasting', 'arcane', 'divine', 'magical'],
        'sort': ['spell', 'cantrip', 'magic', 'incantation'],
        'monstre': ['monster', 'creature', 'beast', 'enemy', 'foe'],
        'combat': ['combat', 'battle', 'fight', 'initiative', 'round', 'turn'],
        'jet': ['roll', 'check', 'save', 'saving throw', 'dice'],
        'sauvegarde': ['save', 'saving throw', 'constitution', 'dexterity', 'wisdom'],
        'competence': ['skill', 'ability', 'proficiency', 'check'],
        'niveau': ['level', 'tier', 'class level'],
        'classe': ['class', 'fighter', 'wizard', 'rogue', 'cleric', 'barbarian', 'bard', 'druid', 'monk', 'paladin', 'ranger', 'sorcerer', 'warlock'],
        'race': ['race', 'species', 'elf', 'dwarf', 'human', 'halfling', 'gnome', 'dragonborn', 'tiefling', 'half-orc', 'half-elf'],
        'equipement': ['equipment', 'gear', 'weapon', 'armor', 'item'],
        'arme': ['weapon', 'sword', 'bow', 'axe', 'dagger', 'mace', 'staff'],
        'degat': ['damage', 'harm', 'hurt', 'hit points', 'hp'],
        'soin': ['heal', 'healing', 'cure', 'restore', 'hit points', 'recovery'],
        'mouvement': ['movement', 'speed', 'move', 'walk', 'dash', 'disengage'],
        'action': ['action', 'bonus action', 'reaction', 'free action'],
        'repos': ['rest', 'short rest', 'long rest', 'recovery'],
        'condition': ['condition', 'status', 'blinded', 'charmed', 'frightened', 'paralyzed', 'poisoned', 'prone', 'stunned', 'unconscious', 'exhaustion'],
        'avantage': ['advantage', 'disadvantage'],
        'concentration': ['concentration', 'maintain', 'spell concentration'],
        'opportunite': ['opportunity', 'opportunity attack', 'reaction'],
        'couverture': ['cover', 'half cover', 'three-quarters cover', 'total cover'],
        'lumiere': ['light', 'darkness', 'dim light', 'bright light', 'darkvision', 'blindsight'],
        'alignement': ['alignment', 'lawful', 'chaotic', 'good', 'evil', 'neutral'],
        'mort': ['death', 'dying', 'death save', 'unconscious', 'stabilize'],
        'critique': ['critical', 'critical hit', 'natural 20', 'crit'],
        'resistance': ['resistance', 'immunity', 'vulnerability'],
        'multiclasse': ['multiclass', 'multiclassing', 'multi-class'],
        'caracteristique': ['ability', 'ability score', 'strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma', 'stat'],
        'pv': ['hit points', 'hp', 'health', 'life'],
        'ca': ['armor class', 'ac', 'defense'],
        'initiative': ['initiative', 'turn order', 'combat order'],
        'terrain': ['terrain', 'difficult terrain', 'movement'],
        'vision': ['vision', 'sight', 'darkvision', 'blindsight', 'truesight'],
    }
    
    def __init__(self, persist_directory: str = "data/chroma_db_v2"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        print("[RAG] Chargement du modele d'embeddings...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        try:
            self.collection = self.client.get_collection("dnd_docs_v2")
            print(f"[RAG] Collection existante chargee ({self.collection.count()} chunks)")
        except:
            self.collection = self.client.create_collection(
                name="dnd_docs_v2",
                metadata={"description": "D&D 5e documents - optimized chunks"}
            )
            print("[RAG] Nouvelle collection creee")
        
        self.doc_processor = DocumentProcessor()
    
    def _expand_query(self, query: str) -> str:
        """
        Enrichit la requete avec des synonymes D&D
        Ameliore la recherche semantique
        """
        query_lower = query.lower()
        expanded_terms = [query]
        
        for french_term, english_terms in self.DND_SYNONYMS.items():
            if french_term in query_lower:
                expanded_terms.extend(english_terms[:2])  # Max 2 synonymes
        
        return ' '.join(expanded_terms)
    
    def index_documents(self, force_reindex: bool = False):
        """Indexe les documents avec des chunks optimises"""
        if self.collection.count() > 0 and not force_reindex:
            print(f"[RAG] Collection deja indexee ({self.collection.count()} chunks)")
            return
        
        print("[RAG] Indexation des documents D&D...")
        documents = self.doc_processor.load_all_pdfs()
        
        if not documents:
            print("[RAG] Aucun document trouve")
            return
        
        texts, metadatas, ids = [], [], []
        
        for idx, doc in enumerate(documents):
            chunks = self.doc_processor.chunk_text(doc['text'])
            
            for chunk_idx, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append({
                    'source': doc['source'],
                    'page': doc['page'],
                    'chunk': chunk_idx
                })
                ids.append(f"{doc['source']}_p{doc['page']}_c{chunk_idx}")
        
        # Indexation par batch
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            
            embeddings = self.embedding_model.encode(batch_texts).tolist()
            
            self.collection.add(
                documents=batch_texts,
                embeddings=embeddings,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            print(f"[RAG] Indexe {min(i + batch_size, len(texts))}/{len(texts)}")
        
        print(f"[RAG] Indexation terminee: {len(texts)} chunks")
    
    def search(self, query: str, n_results: int = 5, min_score: float = 0.3) -> List[Dict]:
        """
        Recherche semantique avec filtrage par score
        
        Args:
            query: Texte de recherche
            n_results: Nombre de resultats max
            min_score: Score minimum de pertinence (0-1, plus bas = plus pertinent)
        """
        if self.collection.count() == 0:
            print("[RAG] Aucun document indexe")
            return []
        
        # Enrichir la requete
        expanded_query = self._expand_query(query)
        query_embedding = self.embedding_model.encode([expanded_query])[0].tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 2  # Recuperer plus pour filtrer ensuite
        )
        
        formatted = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i] if results.get('distances') else 0
                
                # Filtrer par score (distance < min_score = pertinent)
                if distance < min_score or len(formatted) < 3:  # Garder au moins 3
                    formatted.append({
                        'text': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'score': round(1 - distance, 3)  # Convertir en score (plus haut = mieux)
                    })
                
                if len(formatted) >= n_results:
                    break
        
        return formatted
    
    def get_context_for_query(self, query: str, n_results: int = 4) -> str:
        """
        Genere un contexte textuel pour le LLM
        """
        results = self.search(query, n_results)
        
        if not results:
            return ""
        
        context_parts = []
        for result in results:
            source = result['metadata'].get('source', 'Source inconnue')
            page = result['metadata'].get('page', '?')
            score = result.get('score', 0)
            text = result['text']
            
            # Format compact pour le contexte
            context_parts.append(f"[{source} p.{page}] (pertinence: {score})\n{text}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def search_rule(self, rule_query: str) -> str:
        """Recherche une regle specifique"""
        context = self.get_context_for_query(rule_query, n_results=4)
        
        if not context:
            return "Aucune regle trouvee. Verifie que les documents sont indexes."
        
        return f"Regles trouvees:\n\n{context}"
