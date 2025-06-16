from src.vector_db.chroma_client import get_chroma_client
from src.models.jina_embeddings_v3 import embed

def build_user_document(user_id: str, group_id: list[str]) -> list[dict]:
    if not user_id or not group_id:
        raise ValueError("user_id와 group_ids는 반드시 있어야 합니다.")

    docs = []
    for id in group_id:
        docs.append({
            "id": f"user-{user_id}-{id}",  # <-- 개선된 ID 규칙
            "text": f"user-{user_id}",
            "metadata": {
                "user_id": user_id,
                "group_id": id,
            }
        })
    return docs

def remove_user_group_activity(user_id: str, group_id: str) -> None:
    client = get_chroma_client()
    col = client.get_or_create_collection(name="user-activity", embedding_function=embed)
    doc_id = f"user-{user_id}-{group_id}"
    col.delete(ids=[doc_id])
