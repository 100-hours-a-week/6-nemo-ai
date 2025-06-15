from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.models.gemma_3_4b import generate_explaination
from src.core.chat_cache import get_session_history
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

def handle_freeform_chatbot(query: str, user_id: str, debug: bool = False, return_context: bool = False) -> dict:
    if not query.strip():
        ai_logger.warning("[Chatbot] 비어 있는 질문 수신", extra={"user_id": user_id})
        return {
            "reason": "질문을 이해할 수 없어요. 조금만 더 구체적으로 말씀해 주세요!",
            "groupId": -1
        }

    ai_logger.info("[Chatbot] 유저 쿼리 수신", extra={"query": query, "user_id": user_id})
    history = get_session_history(user_id)
    history.add_user_message(query)

    try:
        joined_ids = get_user_joined_group_ids(user_id)
        ai_logger.info("[Chatbot] 유저 참여 모임 조회 완료", extra={"user_id": user_id, "joined_ids": list(joined_ids)})
        if debug:
            print("✅ [1] 유저 참여 중인 groupId:", joined_ids)
    except Exception:
        joined_ids = set()
        ai_logger.warning("[Chatbot] 유저 참여 모임 조회 실패", extra={"user_id": user_id})

    results = search_similar_documents(query, top_k=10)
    ai_logger.info("[Chatbot] 유사한 모임 검색 완료", extra={"result_count": len(results)})
    if debug:
        print("✅ [2] 검색된 모임 수:", len(results))
        for r in results:
            print("   - 검색된 groupId:", r.get("metadata", {}).get("groupId"))
            print("     요약 일부:", r["text"][:40])

    filtered = [
        r for r in results
        if r.get("metadata", {}).get("groupId") not in joined_ids
           and r.get("metadata", {}).get("groupId") is not None
    ]
    if debug:
        print("✅ [3] 필터링 후 추천 모임 수:", len(filtered))
        for r in filtered:
            print("   - 추천 대상 groupId:", r["metadata"]["groupId"])

    if not filtered:
        msg = "추천 가능한 새로운 모임이 아직 없어요. 당신이 직접 비슷한 모임을 열어보는 건 어떨까요?"
        if return_context:
            history.add_ai_message(msg)
        ai_logger.info("[Chatbot] 새로운 추천 모임 없음", extra={"user_id": user_id})
        return {
            "groupId": -1,
            "reason": msg
        }

    top_result = filtered[0]
    group_id = int(top_result["metadata"]["groupId"])
    reason = "이 모임은 당신의 관심사와 유사한 주제를 다루고 있어 추천드립니다."

    if return_context:
        try:
            reason = generate_explaination(query, [top_result["text"]])
            ai_logger.info("[Chatbot] 추천 사유 생성 완료", extra={"user_id": user_id})
            history.add_ai_message(reason)
        except Exception:
            ai_logger.warning("[Chatbot] 추천 사유 생성 실패 (기본값 사용)", extra={"user_id": user_id})

    return {
        "groupId": group_id,
        "reason": reason
    }