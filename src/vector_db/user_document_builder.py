from src.vector_db.chroma_client import get_chroma_client
from src.models.jina_embeddings_v3 import embed

def build_user_document(userId: str, groupId: str) -> list[dict]:
    if not userId or not groupId:
        raise ValueError("userId와 groupId는 반드시 있어야 합니다.")

    return [
        {
            "id": f"user-{userId}-{groupId}",
            "text": f"user-{userId}",
            "metadata": {
                "userId": userId,
                "groupId": groupId,
            }
        }
    ]

def remove_user_group_activity(user_id: str, group_id: str) -> None:
    client = get_chroma_client()
    col = client.get_or_create_collection(name="user-activity", embedding_function=embed)
    doc_id = f"user-{user_id}-{group_id}"
    col.delete(ids=[doc_id])
