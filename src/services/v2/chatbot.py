import json
import re
from src.core.ai_logger import get_ai_logger
from src.models.gemma_3_4b import call_vllm_api
from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.core.chat_cache import get_session_history
from src.core.similarity_filter import is_similar_to_any  # 유사 질문 비교

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
        ai_logger.info("[Chatbot] 원시 응답", extra={"response": raw_response})

        json_match = re.search(r"\{[\s\S]+?\}", raw_response)
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

    return f"""
{context}

- 질문은 75~120자 이내의 자연스럽고 대화체 말투로 작성하세요.
- AI에 대한 설명 없이, 사용자에게 직접 질문하세요.
- 질문 내용은 모임의 성격, 분위기, 규모, 목적 등 사용자에게 맞는 '모임 유형'을 파악하는 데 집중하세요.
- 선택지는 4개 작성하세요.
- 각 선택지는 1-3개 단어로 구성하세요.

다음 형식의 JSON으로만 출력하세요:
{{
  "question": "...",
  "options": ["...", "...", "...", "..."]
}}
""".strip()


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

    results = search_similar_documents(combined_text, top_k=10)
    filtered = [
        r for r in results
        if r.get("metadata", {}).get("groupId") not in joined_ids
        and r.get("metadata", {}).get("groupId") is not None
    ]

    if not filtered:
        return {
            "groupId": -1,
            "reason": "추천 가능한 새로운 모임이 아직 없어요. 직접 비슷한 모임을 열어보는 건 어떨까요?"
        }

    top_result = filtered[0]
    group_id = int(top_result["metadata"]["groupId"])
    group_text = top_result["text"]

    try:
        reason = await generate_explaination(messages, group_text)
        ai_logger.info("[추천] 추천 사유 생성 성공", extra={"group_id": group_id})
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

    prompt = f"""
    당신은 모임 추천 챗봇입니다.

    다음은 사용자와의 대화 내용입니다:
    {conversation}

    추천할 모임 정보:
    {group_text.strip()}

    이 모임이 사용자에게 적합한 이유를 **마크다운 형식**으로 작성하세요. 아래 조건을 지키세요:

    - 설명은 150~270자 이내로, 핵심만 간결하게    
    - 텍스트 설명만 출력 (JSON, 따옴표, 리스트 등 X)
    - 문장은 하나로 자연스럽게 이어지며, 반복 없이 핵심만 담을 것
    - "AI:", "설명:", "- " 같은 포맷은 절대 사용하지 마세요

    바로 아래에 설명을 작성하세요.
    """.strip()

    explanation = await call_vllm_api(prompt, max_tokens=400)
    cleaned = re.sub(
        r"^\s*(?:설명|추천|AI|\[AI\]|모임\s*이름)\s*[:：-]?\s*",
        "",
        explanation.strip(),
        flags=re.IGNORECASE
    )

    if debug:
        print("📦 생성된 추천 설명:\n", cleaned)

    return cleaned

#removed from prompt:
"""
- 최대 300자
- 제목 스타일(예: `###`, `**`)을 활용해 **모임 이름**을 강조하세요
- 줄바꿈(`\\n` 또는 빈 줄)을 활용해 시각적으로 구분하세요
- 리스트(`-`) 또는 하이라이트(`**`)를 적절히 사용하세요
"""