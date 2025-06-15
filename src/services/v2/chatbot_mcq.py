from src.models.gemma_3_4b import generate_mcq_questions, generate_explaination
from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.core.chat_cache import get_session_history
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

def handle_mcq_question_generation(user_id: str, answer: str = None, debug: bool = False) -> dict:
    ai_logger.info("[MCQ] 질문 생성 요청", extra={"user_id": user_id, "answer": answer})
    history = get_session_history(user_id)

    # 이전 답변 기반 다음 질문 생성
    previous_answers = [answer] if answer else []
    questions = generate_mcq_questions(
        debug=debug,
        use_context=True,
        step=len(previous_answers),
        previous_answers=previous_answers
    )

    if not questions:
        ai_logger.warning("[MCQ] 질문 생성 실패", extra={"user_id": user_id})
        return {
            "question": "",
            "options": []
        }

    q = questions[0]
    return {
        "question": q["question"],
        "options": q["options"]
    }


def handle_mcq_answer_processing(messages: list[dict], debug: bool = False, return_context: bool = True) -> dict:
    if not messages:
        ai_logger.warning("[MCQ] 빈 메시지 목록", extra={})
        return {
            "groupId": -1,
            "reason": "추천 가능한 정보가 부족합니다."
        }

    # 메시지를 텍스트로 변환
    combined_text = "\n".join([f"{m['role']}: {m['text']}" for m in messages])
    ai_logger.info("[MCQ] 응답 내용 정리 완료", extra={"message_count": len(messages)})

    try:
        user_id = "unknown"  # 필요 시 프론트에서 넘겨받도록 확장
        joined_ids = get_user_joined_group_ids(user_id)
    except Exception:
        joined_ids = set()
        ai_logger.warning("[MCQ] 유저 참여 모임 조회 실패", extra={"user_id": user_id})

    results = search_similar_documents(query=combined_text, top_k=10)
    filtered = [
        r for r in results
        if r.get("metadata", {}).get("groupId") not in joined_ids
           and r.get("metadata", {}).get("groupId") is not None
    ]

    if not filtered:
        msg = "추천 가능한 새로운 모임이 아직 없어요. 당신이 직접 비슷한 모임을 열어보는 건 어떨까요?"
        return {
            "groupId": -1,
            "reason": msg
        }

    top_result = filtered[0]
    group_id = int(top_result["metadata"]["groupId"])

    try:
        reason = generate_explaination(combined_text, [top_result["text"]]) if return_context else "추천 사유는 제공되지 않았습니다."
        ai_logger.info("[MCQ] 추천 사유 생성 완료", extra={"group_id": group_id})
    except Exception:
        reason = "이 모임은 당신의 응답 내용과 가장 관련이 있어 보여 추천드립니다."
        ai_logger.warning("[MCQ] 추천 사유 생성 실패", extra={"group_id": group_id})

    return {
        "groupId": group_id,
        "reason": reason
    }
