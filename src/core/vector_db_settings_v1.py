import chromadb
# from chromadb.api.types import Documents, Embeddings
# from chromadb.utils.embedding_functions import EmbeddingFunction
from src.core.hf_api_setup_v1 import embed
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
persist_dir = os.path.join(project_root, "data/chroma")

client = chromadb.PersistentClient(path=persist_dir)

collection = client.get_or_create_collection(name="nemo_vector_store")

def add_to_chroma(doc_id: str, text: str):
    vec = embed([text])
    collection.add(documents=[text], ids=[doc_id], embeddings=vec)

def search_chroma(query: str, k=3):
    vec = embed([query])
    return collection.query(query_embeddings=vec, n_results=k)

if __name__ == "__main__":
    print(collection.peek())