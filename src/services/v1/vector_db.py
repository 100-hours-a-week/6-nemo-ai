import chromadb
# from chromadb.api.types import Documents, Embeddings
# from chromadb.utils.embedding_functions import EmbeddingFunction
from src.services.v1.embed import embed
import numpy as np
from typing import Callable
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

def pick_best_by_vector_similarity(
    candidates: list[list[str]],
    base_text: str,
    embed_fn: Callable[[list[str] | str], list[list[float]]]
) -> list[str]:

    candidate_texts = [" ".join(tags) for tags in candidates]
    all_texts = [base_text] + candidate_texts
    embeddings = embed_fn(all_texts)

    base_vec = np.array(embeddings[0])
    candidate_vecs = [np.array(vec) for vec in embeddings[1:]]

    similarities = [
        np.dot(base_vec, vec) / (np.linalg.norm(base_vec) * np.linalg.norm(vec) + 1e-8)
        for vec in candidate_vecs
    ]

    best_idx = int(np.argmax(similarities))
    return candidates[best_idx]

if __name__ == "__main__":
    print(collection.peek())