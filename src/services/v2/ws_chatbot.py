import json
from src.models.gemma_3_4b import stream_vllm_response
from src.core.chat_cache import get_session_history
from src.core.similarity_filter import is_similar_to_any
from src.vector_db.vector_searcher import (
    search_similar_documents,
    get_user_joined_group_ids,
    RECOMMENDATION_THRESHOLD,
)
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()


async def stream_question_chunks(answer: str | None, user_id: str, session_id: str):
    history = get_session_history(session_id)
    previous_ai_messages = [m["content"] for m in history.get_messages() if m["role"] == "AI"]
    previous_question = previous_ai_messages[-1] if previous_ai_messages else None

    prompt = generate_combined_prompt(answer, previous_question)
    ai_logger.info("[Prompt 생성 완료]", extra={"prompt": prompt})

    chunks = []
    first = True

    async for chunk in stream_vllm_response([
        {"role": "system", "text": "당신은 한국어로 대화하는 친근한 모임 추천 챗봇입니다."},
        {"role": "user", "text": prompt}
    ]):
        if first:
            ai_logger.info("[vLLM 첫 chunk 수신]", extra={"chunk": chunk})
            first = False
        chunks.append(chunk)
        yield chunk  # stream용

    full_response = "".join(chunks).strip()
    ai_logger.info("[질문 전체 응답 수신 완료]", extra={"full_response": full_response})

    try:
        # JSON 파싱 시도
        start = full_response.find("{")
        end = full_response.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("JSON 부분 추출 실패")

        json_str = full_response[start:end + 1]
        parsed = json.loads(json_str)

        question = parsed.get("question", "").strip()
        options = parsed.get("options", [])

        if not question or not isinstance(options, list) or len(options) < 2:
            raise ValueError("질문 또는 보기 생성 실패")

        if is_similar_to_any(question, previous_ai_messages):
            ai_logger.info("[유사 질문 감지 → fallback 필요]")
            fallback = {
                "question": "다른 사람과 함께 하고 싶은 활동은 무엇인가요?",
                "options": ["문화 체험", "운동", "스터디", "봉사"]
            }
            yield ("__COMPLETE__", fallback)
            return

        history.add_ai_message(question)

        yield ("__COMPLETE__", {"question": None, "options": options})

    except Exception as e:
        ai_logger.warning("[질문 응답 파싱 실패]", extra={"error": str(e), "raw": full_response})
        fallback = {
            "question": "다른 사람과 함께 하고 싶은 활동은 무엇인가요?",
            "options": ["문화 체험", "운동", "스터디", "봉사"]
        }
        yield ("__COMPLETE__", fallback)


def generate_combined_prompt(previous_answer: str | None, previous_question: str | None = None) -> str:
    context_lines = []
    if previous_question:
        context_lines.append(f"이전 질문: \"{previous_question}\"")
    if previous_answer:
        context_lines.append(f"사용자 답변: \"{previous_answer}\"")

    context = "\n".join(context_lines) + "\n이 정보를 참고해 다음 질문을 생성하세요." if context_lines else \
        "사용자의 모임 선호도를 파악하기 위한 첫 질문을 생성하세요."

    return f"""
{context}
다음 질문은 한국어로 자연스럽고 친근한 말투로 작성해주세요.
질문은 일반 문장 형태로 먼저 출력되고, 옵션은 JSON 형태로 나중에 함께 출력됩니다.

- 질문은 75~120자 이내의 자연스럽고 대화체 말투로 작성하세요.
- AI에 대한 설명 없이, 사용자에게 직접 질문하세요.
- 질문 내용은 모임의 성격, 분위기, 규모, 목적 등 사용자에게 맞는 '모임 유형'을 파악하는 데 집중하세요.
- 선택지는 총 4개, 각각 1-3단어로 구성하세요.
- 이전 질문이랑 겹치지 않게 다르게 작성하세요.

다음 형식의 JSON으로 마무리하세요:
{{
  "question": "...",
  "options": ["...", "...", "...", "..."]
}}
""".strip()


async def stream_recommendation_chunks(messages: list[dict], user_id: str, session_id: str):
    if not messages:
        yield (-1, "대화 내용이 부족하여 추천을 생성할 수 없습니다.")
        return

    combined_text = "\n".join([f"{m['role']}: {m['text']}" for m in messages])

    try:
        joined_ids = get_user_joined_group_ids(user_id)
    except Exception:
        joined_ids = set()
        ai_logger.warning("[추천] 참여 그룹 조회 실패", extra={"session_id": session_id})

    results = search_similar_documents(combined_text, top_k=10)
    filtered = [
        r for r in results
        if r.get("metadata", {}).get("groupId") not in joined_ids
        and r.get("metadata", {}).get("groupId") is not None
    ]

    if not filtered or filtered[0].get("score", 0) < RECOMMENDATION_THRESHOLD:
        yield (-1, "조건에 맞는 모임이 아직 없어요. 직접 비슷한 모임을 열어보는 건 어떨까요?")
        return

    top_result = filtered[0]
    group_id = int(top_result["metadata"]["groupId"])
    group_text = top_result["text"]

    prompt = f"""
다음은 사용자와의 대화 내용입니다:

{combined_text}

추천할 모임 정보:
{group_text.strip()}

[작성 지침]
- 한국어로만 작성하세요. 영어는 절대 포함하지 마세요.
- 설명은 150~270자 이내로 자연스럽고 말하듯 작성하세요.
- "설명:" 같은 접두어 없이 문장만 출력하세요.
- 예시는 참고용이며, 사용자의 대화와 모임 정보를 바탕으로 새롭게 작성하세요.
""".strip()

    messages_for_vllm = [
        {"role": "system", "text": "당신은 한국어로 대화하는 친절한 모임 추천 챗봇입니다. 영어를 절대 사용하지 마세요."},
        {"role": "user", "text": prompt}
    ]

    full_reason = ""
    first = True

    async for chunk in stream_vllm_response(messages_for_vllm):
        if first:
            ai_logger.info("[vLLM 첫 chunk 수신 - 추천]", extra={"chunk": chunk})
            first = False

        full_reason += chunk
        yield (group_id, chunk)

    full_reason = full_reason.strip()
    ai_logger.info("[추천 전체 응답 수신 완료]", extra={"groupId": group_id, "reason": full_reason})
    yield ("__COMPLETE__", group_id, None)

