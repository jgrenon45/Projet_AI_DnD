import os
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

CHROMA_PATH = "./chroma_db"
DATA_PATH = "./data/monopoly_EN.pdf"

def main():
    documents = load_documents_from_pdf(DATA_PATH)
    chunks = split_text(documents)
    save_to_chroma(chunks)

def load_documents_from_pdf(file_path: str) -> Any:
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    return documents

def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=500,
        length_function=len,
        add_start_index=True
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks")

    # Print random sample chunk
    document = chunks[10]
    print(document.page_content)
    print(document.metadata)

    return chunks

def save_to_chroma(chunks: list[Document]):

    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    db = Chroma.from_documents(
        chunks,
        OllamaEmbeddings(),
        persist_directory=CHROMA_PATH
    )
    db.persist()
    print(f"Saved {len(chunks)} chunks to Chroma at {CHROMA_PATH}")

if __name__ == "__main__":
    main()