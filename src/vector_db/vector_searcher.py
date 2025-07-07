from typing import List, Dict, Any, Literal, Optional
from src.vector_db.chroma_client import get_chroma_client
from src.models.jina_embeddings_v3 import embed
from src.core.ai_logger import get_ai_logger
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

GROUP_COLLECTION = "group-info"
SYN_COLLECTION = "group-synthetic"
USER_COLLECTION = "user-activity"
RECOMMENDATION_THRESHOLD = 0.0
logger = get_ai_logger()

def search_similar_documents(
    query: str,
    top_k: int = 5,
    collection: Literal["group-info", "user-activity", "group-synthetic"] = "group-info",
    where: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=collection, embedding_function=embed)

        vector = embed(query)[0]
        results = col.query(
            query_embeddings=[vector],
            n_results=top_k * 2,
            include=["documents", "metadatas", "distances"],
            where=where,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        joined_ids: set[str] = set()
        if user_id:
            joined_ids = get_user_joined_group_ids(user_id)

        filtered = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            score = 1 - dist
            group_id = meta.get("groupId")
            if score < RECOMMENDATION_THRESHOLD:
                continue
            if user_id and group_id in joined_ids:
                continue
            filtered.append({
                "id": meta.get("id"),
                "text": doc,
                "metadata": meta,
                "score": score,
            })
            if len(filtered) >= top_k:
                break

        return filtered
    except Exception as e:
        logger.exception(f"[AI] search_similar_documents 실패: {str(e)}")
        return []


def keyword_search_documents(
    query: str,
    top_k: int = 5,
    collection: Literal["group-info", "group-synthetic"] = "group-info",
    where: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Simple keyword/BM25 style search using TF-IDF."""
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=collection, embedding_function=embed)

        result = col.get(where=where, include=["documents", "metadatas"])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        ids = result.get("ids", [])

        if not documents:
            return []

        vectorizer = TfidfVectorizer()
        doc_vectors = vectorizer.fit_transform(documents)
        query_vec = vectorizer.transform([query])
        scores = (doc_vectors @ query_vec.T).toarray().ravel()

        joined_ids: set[str] = set()
        if user_id:
            joined_ids = get_user_joined_group_ids(user_id)

        order = list(np.argsort(scores)[::-1])
        results: List[Dict[str, Any]] = []
        for idx in order:
            meta = metadatas[idx]
            group_id = meta.get("groupId")
            if user_id and group_id in joined_ids:
                continue
            results.append({
                "id": ids[idx],
                "text": documents[idx],
                "metadata": meta,
                "score": float(scores[idx]),
            })
            if len(results) >= top_k:
                break
        return results
    except Exception as e:
        logger.exception(f"[AI] keyword_search_documents 실패: {str(e)}")
        return []

def get_user_joined_group_ids(user_id: str) -> set[str]:
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=USER_COLLECTION, embedding_function=embed)

        result = col.get(where={"userId": user_id}, include=["metadatas"])
        return {
            meta.get("groupId")
            for meta in result.get("metadatas", [])
            if meta.get("groupId")
        }
    except Exception as e:
        logger.warning(f"[AI] 유저 참여 그룹 조회 실패: {str(e)}")
        return set()

if __name__ == "__main__":
    from pprint import pprint

    user_id = "u2"
    joined_ids = get_user_joined_group_ids(user_id)
    print("유저가 참여 중인 group_id 리스트:")
    pprint(joined_ids)

    query = "조용한 모임이 좋아요"
    results = search_similar_documents(query, top_k=4)
    print("유사한 그룹 검색 결과:")
    for r in results:
        print("ID:", r["id"])
        print("GroupID in Metadata:", r["metadata"].get("groupId"))
        print("Score:", r["score"])
        print("-" * 50)