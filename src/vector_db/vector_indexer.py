from typing import List, Literal
from src.vector_db.chroma_client import get_chroma_client
from src.models.jina_embeddings_v3 import embed
from src.core.ai_logger import get_ai_logger

GROUP_COLLECTION = "group-info"
USER_COLLECTION = "user-activity"

ai_logger = get_ai_logger()

def add_documents_to_vector_db(docs: List[dict], collection: Literal["group-info", "user-activity"]) -> None:
    if not docs:
        ai_logger.warning("[AI] 빈 문서 리스트로 인해 벡터DB 추가를 건너뜁니다.")
        return

    try:
        client = get_chroma_client()

        existing = collection in [c.name for c in client.list_collections()]
        if existing:
            col = client.get_collection(name=collection)  # 기존 거 그대로 사용
        else:
            col = client.get_or_create_collection(name=collection, embedding_function=embed)

        ids = [doc["id"] for doc in docs]
        texts = [doc["text"] for doc in docs]
        metadatas = [doc["metadata"] for doc in docs]

        vectors = embed(texts)
        if len(vectors) != len(texts):
            ai_logger.error("[AI] 임베딩 결과 수가 입력 문서 수와 다릅니다.")
            return

        col.delete(ids=ids)
        col.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=vectors)

        ai_logger.info(f"[AI] {collection} 컬렉션에 문서 {len(ids)}개가 성공적으로 추가되었습니다.")
    except Exception as e:
        ai_logger.exception(f"[AI] 문서 추가 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    # 수정된 테스트용 문서 예시
    test_docs = [
        {
            "id": "test-001",
            "text": "이것은 테스트 문서입니다.",
            "metadata": {
                "groupId": "999",
                "name": "테스트 모임",
                "tags": "테스트, 디버그"  # 리스트 → 문자열
            }
        }
    ]

    add_documents_to_vector_db(test_docs, collection="group-info")

