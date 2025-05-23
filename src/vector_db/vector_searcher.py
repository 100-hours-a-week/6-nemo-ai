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
