from src.vector_db.chroma_client import get_chroma_client
from src.models.jina_embeddings_v3 import embed

def build_user_document(userId: str, groupId: str) -> list[dict]:
    """
    단일 유저-그룹 참여 문서를 생성합니다.
    """
    if not userId or not groupId:
        raise ValueError("userId와 groupId는 반드시 있어야 합니다.")

    doc = {
        "id": f"user-{userId}-{groupId}",
        "text": f"user-{userId}",
        "metadata": {
            "user_id": userId,
            "group_id": groupId,
        }
    }
    return [doc]

def remove_user_group_activity(userId: str, groupId: str) -> None:
    """
    특정 유저-그룹 참여 기록을 벡터 DB에서 제거합니다.
    """
    client = get_chroma_client()
    col = client.get_or_create_collection(name="user-activity", embedding_function=embed)
    doc_id = f"user-{userId}-{groupId}"
    col.delete(ids=[doc_id])
