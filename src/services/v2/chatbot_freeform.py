from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.models.gemma_3_4b import generate_summary
from src.core.chat_cache import get_session_history, chat_history_to_string  # 새로 추가한 인메모리 캐시

def build_prompt(user_query: str, results: list[dict]) -> str:
    group_summaries = "\n\n".join([
        f"- {doc['text']}" for doc in results
    ])

    return f"""
[사용자 입력]
{user_query}

[추천된 모임 목록]
{group_summaries}

이 사용자에게 위의 모임들이 추천된 이유를 설명해 주세요.
각 모임이 어떤 점에서 적합한지 자연스럽고 말하듯이 요약해 주세요.
"""

def handle_freeform_chatbot(query: str, user_id: str) -> dict:
    if not query.strip():
        return {
            "context": "질문을 이해할 수 없어요. 조금만 더 구체적으로 말씀해 주세요!",
            "groupId": []
        }

    history = get_session_history(user_id)
    history.add_user_message(query)

    try:
        joined_ids = get_user_joined_group_ids(user_id)
    except Exception:
        joined_ids = set()

    results = search_similar_documents(query, top_k=10)
    filtered = [r for r in results if r["metadata"].get("groupId") not in joined_ids]

    if not filtered:
        msg = "추천 가능한 새로운 모임이 아직 없어요. 당신이 직접 비슷한 모임을 열어보는 건 어떨까요?"
        history.add_ai_message(msg)
        return {"context": msg, "groupId": []}

    prompt = build_prompt(query, filtered)

    try:
        summary = generate_summary(prompt)
    except Exception:
        summary = "추천 사유를 생성하는 데 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."

    history.add_ai_message(summary)

    return {
        "context": summary,
        "groupId": [r["metadata"]["groupId"] for r in filtered]
    }

if __name__ == "__main__":
    import json
    result = handle_freeform_chatbot("사람 많은 곳은 불편해서 조용한 모임이 좋아요", "u1")
    print("📦 최종 챗봇 응답:")
    print(json.dumps(result, ensure_ascii=False, indent=2))