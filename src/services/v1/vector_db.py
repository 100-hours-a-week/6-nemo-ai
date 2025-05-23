import chromadb
from src.services.v1.embed import embed
import numpy as np
from typing import Callable
import os
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
persist_dir = os.path.join(project_root, "data/chroma")

client = chromadb.PersistentClient(path=persist_dir)
collection = client.get_or_create_collection(name="nemo_vector_store")

def add_to_chroma(doc_id: str, text: str):
    try:
        ai_logger.info(f"[AI] [벡터 추가] ID: {doc_id}")
        vec = embed([text])
        if not vec or not vec[0]:
            ai_logger.error(f"[AI] [벡터 생성 실패] ID: {doc_id}")
            return
        collection.add(documents=[text], ids=[doc_id], embeddings=vec)
        ai_logger.info(f"[AI] [벡터 저장 완료] ID: {doc_id}")
    except Exception:
        ai_logger.exception(f"[AI] [ChromaDB 추가 실패] ID: {doc_id}")

def search_chroma(query: str, k=3):
    try:
        ai_logger.info(f"[AI] [벡터 검색] 쿼리 길이: {len(query)}")
        vec = embed([query])
        results = collection.query(query_embeddings=vec, n_results=k)
        ai_logger.info(f"[AI] [검색 결과] {len(results.get('ids', [[]])[0])}건 반환됨")
        return results
    except Exception:
        ai_logger.exception("[AI] [벡터 검색 실패]")
        return {}

def pick_best_by_vector_similarity(
    candidates: list[list[str]],
    base_text: str,
    embed_fn: Callable[[list[str] | str], list[list[float]]]
) -> list[str]:
    try:
        ai_logger.info(f"[AI] [유사도 비교 시작] 후보 수: {len(candidates)}")
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
        ai_logger.info(f"[AI] [유사도 최고] idx={best_idx}, 점수={similarities[best_idx]:.4f}")
        return candidates[best_idx]
    except Exception:
        ai_logger.exception("[AI] [유사도 계산 실패]")
        return []

if __name__ == "__main__":
    print(collection.peek())
