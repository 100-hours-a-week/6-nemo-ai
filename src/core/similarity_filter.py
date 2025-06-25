from typing import List
from src.models.jina_embeddings_v3 import embed
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def is_similar_to_any(new_text: str, past_texts: List[str], threshold: float = 0.9) -> bool:
    if not past_texts:
        return False

    try:
        all_texts = past_texts + [new_text]
        vectors = embed(all_texts)
        if len(vectors) != len(all_texts):
            return False

        similarities = cosine_similarity([vectors[-1]], vectors[:-1])[0]
        return any(score > threshold for score in similarities)
    except Exception:
        return False
