from src.core.chat_cache import get_cached_response, set_cached_response
from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.models.gemma_3_4b import generate_summary

def build_prompt(user_query: str, results: list[dict]) -> str:
    """
    검색된 모임들을 바탕으로 Gemma에게 추천 이유를 생성하도록 요청하는 프롬프트
    """
    group_summaries = "\n\n".join([
        f"- {doc['text']}" for doc in results
    ])

    return f"""
[사용자 입력]
{user_query}

[추천된 모임 목록]
{group_summaries}

이 사용자에게 위의 모임들이 추천된 이유를 설명해 주세요.
각 모임이 어떤 점에서 적합한지 자연스럽고 간결하게 요약해 주세요.
형식은 부드럽고 말하듯이 해 주세요.
"""

def handle_freeform_chatbot(query: str, user_id: str) -> dict:
    cached = get_cached_response(query)
    if cached:
        return cached

    joined_ids = get_user_joined_group_ids(user_id)  # 참여 중인 모임

    results = search_similar_documents(query, top_k=10)

    filtered = [r for r in results if r["metadata"].get("groupId") not in joined_ids]

    if not filtered:
        return {
            "context": "추천 가능한 새로운 모임이 아직 없어요. 당신이 직접 비슷한 모임을 열어보는 건 어떨까요?",
            "groupId": []
        }

    prompt = build_prompt(query, filtered)
    summary = generate_summary(prompt)

    group_ids = [r["metadata"]["groupId"] for r in filtered]
    response = {"context": summary, "groupId": group_ids}
    set_cached_response(query, response)
    return response
