from src.models.gemma_3_4b import generate_mcq_questions, generate_explaination
from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.core.chat_cache import get_session_history
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()


def handle_mcq_question_generation(user_id: str, debug: bool = False) -> dict:
    ai_logger.info("[MCQ] 질문 생성 요청", extra={"user_id": user_id})
    history = get_session_history(user_id)

    # 🧠 최근 AI 메시지가 'MCQ 질문들'이라면 캐시 재사용
    cached = [
        msg["content"] for msg in history.get_messages()
        if msg["role"] == "ai" and msg["content"].startswith("[MCQ 질문]")
    ]
    if cached:
        if debug:
            print("♻️ 캐시된 질문 반환")
        return {"questions": eval(cached[-1].replace("[MCQ 질문]", "").strip())}

    # 🔄 새로 생성
    questions = generate_mcq_questions(debug=debug)

    if questions:
        history.add_ai_message(f"[MCQ 질문]{str(questions)}")
        ai_logger.info("[MCQ] 질문 생성 완료 및 캐시됨", extra={"user_id": user_id})
    else:
        ai_logger.warning("[MCQ] 질문 생성 실패", extra={"user_id": user_id})

    return {"questions": questions or []}


def handle_mcq_answer_processing(user_id: str, answers: list[dict], debug: bool = False) -> dict:
    ai_logger.info("[MCQ] 답변 처리 시작", extra={"user_id": user_id, "answer_count": len(answers)})

    if not answers:
        return {"context": "답변이 비어 있습니다.", "groupId": []}

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
        return {
            "context": "추천 가능한 새로운 모임이 아직 없어요. 당신이 직접 비슷한 모임을 열어보는 건 어떨까요?",
            "groupId": []
        }

    top_results = filtered[:2]
    try:
        summary = generate_explaination(combined_text, [r["text"] for r in top_results])
    except Exception:
        summary = "추천 사유를 생성하는 데 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."

    group_ids = [r["metadata"]["groupId"] for r in top_results]
    return {"context": summary, "groupId": group_ids}