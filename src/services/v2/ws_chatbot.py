import re
import json
from src.models.gemma_3_4b import stream_vllm_response
from src.core.chat_cache import get_session_history
from src.core.similarity_filter import is_similar_to_any
from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()


async def stream_question_chunks(answer: str | None, user_id: str, session_id: str):
    history = get_session_history(session_id)
    previous_ai_messages = [m["content"] for m in history.get_messages() if m["role"] == "AI"]
    previous_question = previous_ai_messages[-1] if previous_ai_messages else None

    prompt = generate_combined_prompt(answer, previous_question)
    ai_logger.info("[Prompt 생성 완료]", extra={"prompt": prompt})

    full_response = ""
    buffer = ""

    async for chunk in stream_vllm_response([{"role": "system", "text": prompt}]):
        buffer += chunk
        while " " in buffer:
            word, buffer = buffer.split(" ", 1)
            full_response += word + " "
            yield word

    if buffer.strip():
        full_response += buffer.strip() + " "
        yield buffer.strip()

    ai_logger.info("[질문 전체 응답 수신 완료]", extra={"full_response": full_response.strip()})

    try:
        json_match = re.search(r"\{[\s\S]+?\}", full_response)
        if not json_match:
            raise ValueError("JSON 부분 추출 실패")

        parsed = json.loads(json_match.group(0))
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
        yield ("__COMPLETE__", {"question": question, "options": options})

    except Exception as e:
        ai_logger.warning("[질문 응답 파싱 실패]", extra={"error": str(e), "raw": full_response.strip()})
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

    if not filtered:
        yield (-1, "추천 가능한 새로운 모임이 아직 없어요. 직접 비슷한 모임을 열어보는 건 어떨까요?")
        return

    top_result = filtered[0]
    group_id = int(top_result["metadata"]["groupId"])
    group_text = top_result["text"]

    prompt = f"""
당신은 모임 추천 챗봇입니다.

다음은 사용자와의 대화 내용입니다:
{combined_text}

추천할 모임 정보:
{group_text.strip()}

이 모임이 사용자에게 적합한 이유를 **텍스트 한 문장**으로 설명하세요.
조건:
- 설명은 150~270자 이내
- 반복 없이, 핵심만 담아야 함
- "설명:" 같은 표현 없이 텍스트만 출력
    """.strip()

    reason_chunks = []
    async for chunk in stream_vllm_response([{"role": "system", "text": prompt}]):
        reason_chunks.append(chunk)
        yield (group_id, chunk)

    full_reason = "".join(reason_chunks).strip()
    yield ("__COMPLETE__", group_id, full_reason)
