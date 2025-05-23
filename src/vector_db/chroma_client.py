import os
import chromadb
from chromadb import Client
from chromadb.config import Settings
from src.config import CHROMA_DB_PATH

def get_chroma_client():
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client