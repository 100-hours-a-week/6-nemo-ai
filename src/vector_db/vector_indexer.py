from typing import List, Literal
from src.vector_db.chroma_client import get_chroma_client
from src.vector_db.embedder import embed

# 컬렉션 이름 상수화
GROUP_COLLECTION = "group-info"
USER_COLLECTION = "user-activity"

def add_documents_to_vector_db(docs: List[dict], collection: Literal["group-info", "user-activity"]) -> None:
    if not docs:
        return

    client = get_chroma_client()
    col = client.get_or_create_collection(name=collection)

    ids = [doc["id"] for doc in docs]
    texts = [doc["text"] for doc in docs]
    metadatas = [doc["metadata"] for doc in docs]

    vectors = embed(texts)

    col.delete(ids=ids)

    col.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=vectors
    )

