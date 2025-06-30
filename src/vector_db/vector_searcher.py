from typing import List, Dict, Any, Literal, Optional
from src.vector_db.chroma_client import get_chroma_client
from src.models.jina_embeddings_v3 import embed
from src.core.ai_logger import get_ai_logger

GROUP_COLLECTION = "group-info"
USER_COLLECTION = "user-activity"
RECOMMENDATION_THRESHOLD = 0.5
logger = get_ai_logger()

def search_similar_documents(
    query: str,
    top_k: int = 5,
    collection: Literal["group-info", "user-activity"] = "group-info",
    where: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=collection, embedding_function=embed)

        vector = embed(query)[0]
        results = col.query(
            query_embeddings=[vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        return [
            {
                "id": meta.get("id"),
                "text": doc,
                "metadata": meta,
                "score": 1 - dist
            }
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]
    except Exception as e:
        logger.exception(f"[AI] search_similar_documents 실패: {str(e)}")
        return []

def get_user_joined_group_ids(user_id: str) -> set[str]:
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=USER_COLLECTION, embedding_function=embed)

        user_doc_id = f"user-{user_id}"
        all_ids = col.get().get("ids", [])
        if user_doc_id not in all_ids:
            return set()

        result = col.get(ids=[user_doc_id], include=["metadatas"])
        return {
            item.get("group_id")
            for item in result.get("metadatas", [[]])[0]
            if "group_id" in item
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