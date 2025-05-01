import chromadb
from chromadb.config import Settings
from src.core.hf_api_setup_v1 import embed

client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./data/chroma"
))

collection = client.get_or_create_collection(name="my_collection")

def add_to_chroma(doc_id: str, text: str):
    vec = embed([text])
    collection.add(documents=[text], ids=[doc_id], embeddings=vec)

def search_chroma(query: str, k=3):
    vec = embed([query])
    return collection.query(query_embeddings=vec, n_results=k)