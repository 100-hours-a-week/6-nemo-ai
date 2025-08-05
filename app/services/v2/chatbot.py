import json
import re
from app.core.ai_logger import get_ai_logger
from app.models.gemma_3_4b import call_vllm_api
from app.database.vector_searcher import search_similar_documents, get_user_joined_group_ids, get_random_group_for_user
from app.core.chat_cache import get_session_history
from app.core.utils import is_similar_to_any  # 유사 질문 비교
from app.core.buffer_parser import clean_prompt_context
from app.prompts.prompt_loader import load_prompt_template

ai_logger = get_ai_logger()


async def handle_combined_question(
    answer: str | None,
    user_id: str,
    session_id: str,
    debug_mode: bool = False
) -> dict:
    history = get_session_history(session_id)

    previous_ai_messages = [m["content"] for m in history.get_messages() if m["role"] == "AI"]
    previous_question = previous_ai_messages[-1] if previous_ai_messages else None

    if debug_mode:
        question = "어떤 활동을 좋아하시나요?"
        history.add_ai_message(question)
        return {
            "question": question,
            "options": ["운동", "스터디", "봉사활동", "게임"]
        }

    prompt = generate_combined_prompt(answer, previous_question)
    ai_logger.info("[Chatbot] 질문 생성 프롬프트", extra={"prompt": prompt})

    try:
        raw_response = await call_vllm_api(prompt)
        # Buffer parser로 컨텍스트 정리
        cleaned_response = clean_prompt_context(raw_response)
        ai_logger.info("[Chatbot] 원시 응답", extra={"response": cleaned_response})

        json_match = re.search(r"\{[\s\S]+?\}", cleaned_response)
        if not json_match:
            raise ValueError("JSON 부분 추출 실패")

        cleaned = json_match.group(0)
        parsed = json.loads(cleaned)

        question = parsed.get("question", "").strip()
        options = parsed.get("options", [])

        if not question or not isinstance(options, list) or len(options) < 2:
            raise ValueError("질문 또는 보기 생성 실패")

        past_questions = [m["content"] for m in history.get_messages() if m["role"] == "AI"]
        if is_similar_to_any(question, past_questions):
            ai_logger.info("[Chatbot] 유사 질문 감지 → fallback 질문 반환")
            fallback_q = "다른 사람과 함께 하고 싶은 활동은 무엇인가요?"
            return {
                "question": fallback_q,
                "options": ["문화 체험", "운동", "스터디", "봉사"]
            }

        history.add_ai_message(question)

        return {
            "question": question,
            "options": options
        }

    except Exception as e:
        ai_logger.warning("[Chatbot] 질문 생성 실패", extra={
            "user_id": user_id,
            "session_id": session_id,
            "error": str(e)
        })
        return {
            "question": "새로운 모임을 찾기 위해 어떤 활동을 선호하시나요?",
            "options": ["문화 체험", "운동", "스터디", "봉사"]
        }


def generate_combined_prompt(previous_answer: str | None, previous_question: str | None = None) -> str:
    context_lines = []

    if previous_question:
        context_lines.append(f"이전 질문: \"{previous_question}\"")
    if previous_answer:
        context_lines.append(f"사용자 답변: \"{previous_answer}\"")

    if context_lines:
        context = "\n".join(context_lines) + "\n이 정보를 참고해 다음 질문을 생성하세요."
    else:
        context = "사용자의 모임 선호도를 파악하기 위한 첫 질문을 생성하세요."

    return load_prompt_template("chatbot_question_generation", "v2", context=context)


async def handle_answer_analysis(
    messages: list[dict],
    user_id: str,
    session_id: str,
    debug_mode: bool = False
) -> dict:
    if not messages:
        ai_logger.warning("[추천] 빈 메시지 수신", extra={"session_id": session_id})
        return {
            "groupId": -1,
            "reason": "대화 내용이 부족하여 추천을 생성할 수 없습니다."
        }

    combined_text = "\n".join([f"{m['role']}: {m['text']}" for m in messages])
    ai_logger.info("[추천] 메시지 병합 완료", extra={"session_id": session_id})

    try:
        joined_ids = get_user_joined_group_ids(user_id)
    except Exception:
        joined_ids = set()
        ai_logger.warning("[추천] 유저 참여 그룹 조회 실패", extra={"session_id": session_id})

    results = search_similar_documents(combined_text, top_k=10, user_id=user_id)
    filtered = [
        r for r in results
        if r.get("metadata", {}).get("groupId") not in joined_ids
        and r.get("metadata", {}).get("groupId") is not None
    ]

    if not filtered:
        ai_logger.info("[추천] 매칭 모임 없음 - 랜덤 모임 시도", extra={"session_id": session_id})
        # 랜덤 모임 추천 시도
        random_group = get_random_group_for_user(user_id)
        if random_group:
            group_id = int(random_group["metadata"]["groupId"])
            group_text = random_group["text"]
            
            try:
                reason = await generate_random_explaination(messages, group_text)
                ai_logger.info("[추천] 랜덤 모임 추천 성공", extra={
                    "group_id": group_id, 
                    "reason_preview": reason[:50] + "..." if len(reason) > 50 else reason
                })
            except Exception as e:
                reason = "새로운 모임을 경험해보는 것도 좋은 선택입니다. 이 모임에서 새로운 취미를 발견해보세요!"
                ai_logger.warning("[추천] 랜덤 모임 추천 사유 생성 실패", extra={"group_id": group_id, "error": str(e)})
            
            get_session_history(session_id).clear()
            return {
                "groupId": group_id,
                "reason": reason
            }
        
        return {
            "groupId": -1,
            "reason": "추천 가능한 새로운 모임이 아직 없어요. 직접 비슷한 모임을 열어보는 건 어떨까요?"
        }

    top_result = filtered[0]
    group_id = int(top_result["metadata"]["groupId"])
    group_text = top_result["text"]

    try:
        reason = await generate_explaination(messages, group_text)
        ai_logger.info("[추천] 추천 사유 생성 성공", extra={
            "group_id": group_id, 
            "reason_preview": reason[:50] + "..." if len(reason) > 50 else reason
        })
    except Exception as e:
        reason = "이 모임은 당신의 대화 내용과 가장 잘 어울려 추천드립니다."
        ai_logger.warning("[추천] 추천 사유 생성 실패", extra={"group_id": group_id, "error": str(e)})

    get_session_history(session_id).clear()

    return {
        "groupId": group_id,
        "reason": reason
    }


async def generate_explaination(messages: list[dict], group_text: str, debug: bool = True) -> str:
    conversation = "\n".join([f"{m['role']}: {m['text']}" for m in messages])

    prompt = load_prompt_template("chatbot_recommendation_explanation", "v2", 
                                  conversation=conversation, 
                                  group_text=group_text.strip())

    explanation = await call_vllm_api(prompt, max_tokens=400)
    # Buffer parser로 컨텍스트 정리
    cleaned_explanation = clean_prompt_context(explanation)
    cleaned = re.sub(
        r"^\s*(?:설명|추천|AI|\[AI\]|모임\s*이름)\s*[:：-]?\s*",
        "",
        cleaned_explanation.strip(),
        flags=re.IGNORECASE
    )

    if debug:
        print("📦 생성된 추천 설명:\n", cleaned)

    return cleaned


async def generate_random_explaination(messages: list[dict], group_text: str, debug: bool = True) -> str:
    """랜덤 모임 추천 설명 생성"""
    conversation = "\n".join([f"{m['role']}: {m['text']}" for m in messages])

    prompt = load_prompt_template("chatbot_random_recommendation", "v2", 
                                  conversation=conversation, 
                                  group_text=group_text.strip())

    explanation = await call_vllm_api(prompt, max_tokens=400)
    # Buffer parser로 컨텍스트 정리
    cleaned_explanation = clean_prompt_context(explanation)
    cleaned = re.sub(
        r"^\s*(?:설명|추천|AI|\[AI\]|모임\s*이름)\s*[:：-]?\s*",
        "",
        cleaned_explanation.strip(),
        flags=re.IGNORECASE
    )

    if debug:
        print("🎲 생성된 랜덤 추천 설명:\n", cleaned)

    return cleaned


#removed from prompt:
"""
- 최대 300자
- 제목 스타일(예: `###`, `**`)을 활용해 **모임 이름**을 강조하세요
- 줄바꿈(`\\n` 또는 빈 줄)을 활용해 시각적으로 구분하세요
- 리스트(`-`) 또는 하이라이트(`**`)를 적절히 사용하세요
"""
