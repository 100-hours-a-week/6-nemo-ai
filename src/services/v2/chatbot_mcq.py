from src.models.gemma_3_4b import generate_mcq_questions, generate_explaination
from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.core.chat_cache import get_session_history
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

def handle_mcq_question_generation(user_id: str, session_id: str, step: int, previous_answers: list[str], debug: bool = False) -> dict:
    ai_logger.info("[MCQ] 질문 생성 요청", extra={"user_id": user_id, "session_id": session_id, "step": step})
    history = get_session_history(user_id)

    questions = generate_mcq_questions(debug=debug, use_context=True, step=step, previous_answers=previous_answers)

    if not questions:
        ai_logger.warning("[MCQ] 질문 생성 실패", extra={"user_id": user_id})
        return {
            "sessionId": session_id,
            "question": "",
            "options": []
        }

    question = questions[0]  # Get the first question for the current step
    return {
        "sessionId": session_id,
        "question": question["question"],
        "options": question["options"]
    }


def handle_mcq_answer_processing(user_id: str, answers: list[dict], session_id: str, debug: bool = False, return_context: bool = False) -> dict:
    ai_logger.info("[MCQ] 답변 처리 시작", extra={"user_id": user_id, "session_id": session_id, "answer_count": len(answers)})

    if not answers:
        return {"recommendations": []}

    combined_text = "\n".join(f"Q: {a['question']}\nA: {a['selected_option']}" for a in answers)

    try:
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
        if return_context:
            history = get_session_history(user_id)
            history.add_ai_message(msg)
        return {"recommendations": []}

    top_results = filtered[:2]
    recommendations = []

    try:
        for result in top_results:
            group_id = int(result["metadata"]["groupId"])
            context = generate_explaination(combined_text, [result["text"]]) if return_context else ""
            recommendations.append({
                "groupId": group_id,
                "context": context
            })
        if return_context:
            history = get_session_history(user_id)
            history.add_ai_message(str(recommendations))
    except Exception:
        ai_logger.error("[MCQ] 요약 생성 실패", extra={"user_id": user_id})
        return {"recommendations": []}

    return {"recommendations": recommendations}
