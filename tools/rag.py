"""
RAG (Retrieval-Augmented Generation) system for D&D documents
Processes PDFs and enables semantic search
"""

import os
from pathlib import Path
from typing import List, Optional
import shutil
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from typing import Any

# PDF processing
try:
    from pypdf import PdfReader  # PyPDF moderne
except ImportError:
    from PyPDF2 import PdfReader  # Compatibilité avec PyPDF2

# Vector store
from chromadb import Client
from chromadb.config import Settings as ChromaSettings
import chromadb

# Embeddings
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "./chroma_db"


class DocumentProcessor:
    """Process D&D PDF documents and prepare them for indexing"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Args:
            data_dir (str): Répertoire contenant les PDF
        """
        self.data_dir = Path(data_dir)
        self.documents = []  # Liste des documents chargés
    
    def load_pdf(self, pdf_path: str) -> List[str]:
        """
        Charge un PDF et extrait le texte de chaque page.
        
        Args:
            pdf_path (str): Chemin du fichier PDF
        
        Returns:
            List[dict]: Liste de dictionnaires contenant 'text', 'source', 'page'
        """
        texts = []
        try:
            reader = PdfReader(pdf_path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():  # Ignorer les pages vides
                    texts.append({
                        'text': text,
                        'source': Path(pdf_path).name,
                        'page': page_num + 1
                    })
            print(f"Loaded {len(texts)} pages from {Path(pdf_path).name}")
        except Exception as e:
            print(f"Error loading {pdf_path}: {e}")
        
        return texts
    
    def load_all_pdfs(self) -> List[dict]:
        """
        Charge tous les PDFs du répertoire data_dir.
        
        Returns:
            List[dict]: Liste de toutes les pages extraites de tous les PDFs
        """
        all_texts = []
        
        # Liste des PDFs à charger
        pdf_files = [
            self.data_dir / "DnD_BasicRules_2018.pdf",
            self.data_dir / "PlayerHandbook.pdf"
        ]
        
        for pdf_path in pdf_files:
            if pdf_path.exists():
                texts = self.load_pdf(str(pdf_path))
                all_texts.extend(texts)
            else:
                print(f"PDF not found: {pdf_path}")
        
        self.documents = all_texts
        return all_texts
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Découpe un texte en morceaux (chunks) avec chevauchement.
        
        Args:
            text (str): Texte à découper
            chunk_size (int): Nombre de mots par chunk
            overlap (int): Nombre de mots chevauchés entre chunks
        
        Returns:
            List[str]: Liste de chunks de texte
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks


class RAGSystem:
    """Retrieval-Augmented Generation system for D&D documents"""
    
    def __init__(self, persist_directory: str = "data/chroma_db"):
        """
        Initialise le système RAG avec embeddings et ChromaDB.
        
        Args:
            persist_directory (str): Répertoire pour stocker la base vectorielle
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Charger le modèle d'embeddings
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialiser ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        try:
            # Essayer de charger la collection existante
            self.collection = self.client.get_collection("dnd_documents")
            print("Loaded existing document collection")
        except:
            # Sinon créer une nouvelle collection
            self.collection = self.client.create_collection(
                name="dnd_documents",
                metadata={"description": "D&D 5e rules and handbook"}
            )
            print("Created new document collection")
        
        # Initialiser le processeur de documents PDF
        self.doc_processor = DocumentProcessor()
    
    def index_documents(self, force_reindex: bool = False):
        """
        Indexe tous les documents D&D en utilisant embeddings.
        
        Args:
            force_reindex (bool): Reindexe même si des documents existent déjà
        """
        # Vérifier si la collection contient déjà des documents
        if self.collection.count() > 0 and not force_reindex:
            print(f"Collection already contains {self.collection.count()} documents")
            return
        
        print("Indexing D&D documents...")
        
        # Charger tous les PDFs
        documents = self.doc_processor.load_all_pdfs()
        
        if not documents:
            print("No documents found to index")
            return
        
        # Préparer les données pour l'indexation
        texts = []
        metadatas = []
        ids = []
        
        for idx, doc in enumerate(documents):
            # Découper le texte en chunks
            chunks = self.doc_processor.chunk_text(doc['text'])
            
            for chunk_idx, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append({
                    'source': doc['source'],
                    'page': doc['page'],
                    'chunk': chunk_idx
                })
                ids.append(f"{doc['source']}_p{doc['page']}_c{chunk_idx}")
        
        # Ajouter les chunks à la collection en batch
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            
            # Générer les embeddings pour le batch
            embeddings = self.embedding_model.encode(batch_texts).tolist()
            
            self.collection.add(
                documents=batch_texts,
                embeddings=embeddings,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            
            print(f"  Indexed {min(i + batch_size, len(texts))}/{len(texts)} chunks")
        
        print(f"Indexed {len(texts)} document chunks")
    
    def search(self, query: str, n_results: int = 5) -> List[dict]:
        """
        Recherche les documents les plus pertinents pour une requête.
        
        Args:
            query (str): Texte de recherche
            n_results (int): Nombre de résultats souhaités
        
        Returns:
            List[dict]: Résultats contenant texte, metadata, distance
        """
        if self.collection.count() == 0:
            print("No documents indexed. Run index_documents() first.")
            return []
        
        # Générer l'embedding de la requête
        query_embedding = self.embedding_model.encode([query])[0].tolist()
        
        # Effectuer la recherche dans la collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Formater les résultats
        formatted_results = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'text': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results.get('distances') else 0
                })
        
        return formatted_results
    
    def get_context_for_query(self, query: str, n_results: int = 3) -> str:
        """
        Récupère un contexte textuel pour une requête, en concaténant les meilleurs résultats.
        
        Args:
            query (str): Question ou mot-clé
            n_results (int): Nombre de documents à inclure
        
        Returns:
            str: Concaténation des textes pertinents avec référence source/page
        """
        results = self.search(query, n_results)
        
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result['metadata'].get('source', 'Unknown')
            page = result['metadata'].get('page', '?')
            text = result['text']
            
            context_parts.append(f"[{source}, p.{page}]\n{text}")
        
        return "\n\n".join(context_parts)
    
    def search_rule(self, rule_query: str) -> str:
        """
        Recherche une règle spécifique de D&D dans les documents.
        
        Args:
            rule_query (str): Question ou nom de la règle
        
        Returns:
            str: Contexte trouvé ou message d'erreur si aucun document n'est indexé
        """
        context = self.get_context_for_query(rule_query, n_results=3)
        
        if not context:
            return "Aucune règle trouvée. Assure-toi que les documents sont indexés."
        
        return f"Règles trouvées:\n\n{context}"


# Class de Jer pour le rag
class RagAgent:

    def __init__(self, file_path: str):
        documents = self._load_documents_from_pdf(file_path)
        chunks = self._split_text(documents)
        self._save_to_chroma(chunks)

    def _get_embedding_function(self):
        embeddings = OpenAIEmbeddings(
            base_url="http://127.0.0.1:1234/v1",
            api_key="lm-studio",
            check_embedding_ctx_length=False
        )
        return embeddings

    def _load_documents_from_pdf(self, file_path: str) -> Any:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        return documents

    def _split_text(self, documents: list[Document]):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            length_function=len,
            add_start_index=True
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Split {len(documents)} documents into {len(chunks)} chunks")

        return chunks

    def _save_to_chroma(self, chunks: list[Document]):

        if os.path.exists(CHROMA_PATH):
            shutil.rmtree(CHROMA_PATH)
        self.db = Chroma(
            embedding_function=self._get_embedding_function(),
            persist_directory=CHROMA_PATH
        )
        self.db.add_documents(chunks)
        print(f"Saved {len(chunks)} chunks to Chroma at {CHROMA_PATH}")

    def query(self, query_text: str):
        results = self.db.similarity_search_with_relevance_scores(query_text, k=3)
        if len(results) == 0:
            print("No relevant results found.")
            return
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        return context_text