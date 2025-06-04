from typing import List, Dict, Any, Literal, Optional
from src.vector_db.chroma_client import get_chroma_client
from src.vector_db.embedder import embed
# 컬렉션 이름 상수
GROUP_COLLECTION = "group-info"
USER_COLLECTION = "user-activity"

def search_similar_documents(query: str, top_k: int = 5, collection: Literal["group-info", "user-activity"] = "group-info", where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    client = get_chroma_client()
    col = client.get_or_create_collection(name=collection)

    vector = embed(query)[0]

    results = col.query(
        query_embeddings=[vector],
        n_results=top_k,
        where=where or {},
        include=["documents", "metadatas", "distances", "ids"]
    )

    documents = results.get("documents", [])[0]
    metadatas = results.get("metadatas", [])[0]
    ids = results.get("ids", [])[0]
    distances = results.get("distances", [])[0]

    return [
        {
            "id": _id,
            "text": doc,
            "metadata": meta,
            "score": 1 - dist
        }
        for _id, doc, meta, dist in zip(ids, documents, metadatas, distances)
    ]

def get_user_joined_group_ids(user_id: str) -> set[str]:
    client = get_chroma_client()
    col = client.get_or_create_collection(name="user-activity")
    results = col.query(
        query_texts=[f"user-{user_id}"],  # 이건 인덱싱에 따라 조정 가능
        n_results=100,  # 참여 이력이 많은 경우 늘릴 수 있음
        include=["metadatas"]
    )
    return {item.get("group_id") for item in results["metadatas"][0] if "group_id" in item}
