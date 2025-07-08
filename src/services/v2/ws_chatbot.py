import json
from src.models.gemma_3_4b import stream_vllm_response
from src.core.chat_cache import get_session_history
from src.core.similarity_filter import is_similar_to_any
from src.vector_db.vector_searcher import (
    search_similar_documents,
    RECOMMENDATION_THRESHOLD,
)
from src.vector_db.hybrid_search import hybrid_group_search
from src.core.ai_logger import get_ai_logger
import time

ai_logger = get_ai_logger()


async def stream_question_chunks(answer: str | None, user_id: str, session_id: str):
    history = get_session_history(session_id)
    previous_ai_messages = [m["content"] for m in history.get_messages() if m["role"] == "AI"]
    previous_question = previous_ai_messages[-1] if previous_ai_messages else None

    prompt = generate_combined_prompt(answer, previous_question)
    ai_logger.info("[Prompt 생성 완료]", extra={"prompt": prompt})

    streamed_text = ""
    full_question = ""
    options_text = ""
    capturing_options = False
    first = True
    start_time = time.time()

    async for chunk in stream_vllm_response([
        {"role": "system", "text": "당신은 한국어로 대화하는 친근한 모임 추천 챗봇입니다."},
        {"role": "user", "text": prompt}
    ]):
        if first:
            ai_logger.info(f"[vLLM 첫 chunk 수신] chunk: {chunk} time {time.time() - start_time} sec")
            first = False

        streamed_text += chunk

        # options가 시작되는 시점 파악
        if not capturing_options and "options" in chunk:
            capturing_options = True
            idx = chunk.index("options")
            full_question += chunk[:idx].strip()
            options_text += chunk[idx:]
            continue

        if capturing_options:
            options_text += chunk  # stream은 멈추고 내부에서 buffer에 저장
        else:
            full_question += chunk
            cleaned_chunk = chunk.replace("**", "").replace("*", "").replace("\n", "").replace("\r", "").strip()
            if cleaned_chunk:
                yield cleaned_chunk

    full_response = streamed_text.strip()
    end_time = time.time()
    ai_logger.info(f"[질문 전체 응답 수신 완료] time {end_time - start_time} sec,\nfull_response: {full_response}")

    try:
        options = extract_options_from_stream(options_text)

        if not options or len(options) < 2:
            raise ValueError("options 파싱 실패 또는 항목 부족")

        history.add_ai_message(full_question.strip())

        yield ("__COMPLETE__", {
            "question": None,
            "options": options
        })

    except Exception as e:
        ai_logger.warning("[질문 옵션 파싱 실패]", extra={"error": str(e), "raw": options_text})
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

    connect_instruction = (
        "- 질문은 이전 응답을 반영하여 **연결된 말투**로 시작하세요. (예: \"그렇군요, 그러면...\", \"아, 그런 스타일 좋아하시네요. 그렇다면...\")"
        if previous_question and previous_answer else
        "- 자연스럽고 중립적인 말투로 질문을 시작하세요. (예: \"모임에 참여하신다면 어떤 분위기를 선호하시나요?\")"
    )

    return f"""
{context}
당신은 질문을 생성을 하는 모임 추천을 위한 챗봇이지만, 이 단계에서는 추천하지 마세요.  
다음 질문은 한국어로 자연스럽고 친근한 말투로 작성해주세요.
질문은 일반 문장 형태로 먼저 출력되고, 옵션은 JSON 형태로 나중에 함께 출력됩니다.

- "**질문:**", "**options:**" 같은 마크다운 접두어는 절대 쓰지 마세요. 그냥 질문 문장과 JSON만 출력하세요.
- "네, 알겠습니다", "질문을 만들어보겠습니다", "아", "**질문:**" 같은 서론을 절대 포함하지 마세요
- 질문은 반드시 **AI가 사용자에게 묻는 문장**이어야 합니다. 질문의 주어는 항상 '당신' 또는 생략된 2인칭 사용자입니다.
- 문장은 항상 **2인칭 대상에게 질문하는 형태**여야 하며, **AI는 조력자 역할**입니다.
- 서론 없이 질문은 **하나의 문장**으로, **75~120자** 길이의 **친근하고 자연스러운 말투**로 작성하세요.
{connect_instruction}
- 질문의 주제는 모임의 성격, 분위기, 활동 목적, 인원 수, 대화 스타일, 모임 빈도 등 다양하게 설정하세요.
- 반드시 **이전 질문과는 다른 주제나 방향**의 질문을 작성하세요.
- 문장 앞뒤가 매끄럽게 이어지도록 하며, **반말이나 명령형은 피하고**, 정중하고 부드러운 말투를 사용하세요.
- 선택지는 총 4개이며, **각각 1~3단어 이내의 표현으로 구성**하세요.
질문 다음에 바로 아래 JSON 형식으로 출력하세요: 
  "options": ["...", "...", "...", "..."]
""".strip()


async def stream_recommendation_chunks(messages: list[dict], user_id: str, session_id: str):
    if not messages:
        yield (-1, "대화 내용이 부족하여 추천을 생성할 수 없습니다.")
        return

    combined_text = "\n".join([f"{m['role']}: {m['text']}" for m in messages])

    results = hybrid_group_search(combined_text, top_k=10, user_id=user_id)
    if not results:
        results = search_similar_documents(
            "",
            top_k=10,
            collection="group-info",
            user_id=user_id,
        )

    if not results or results[0].get("score", 0) < RECOMMENDATION_THRESHOLD:
        yield (-1, "조건에 맞는 모임이 아직 없어요. 직접 비슷한 모임을 열어보는 건 어떨까요?")
        return

    top_result = results[0]
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
    start_time = time.time()

    async for chunk in stream_vllm_response(messages_for_vllm):
        if first:
            first_chunk_time = time.time()
            ai_logger.info(
                f"[vLLM 첫 chunk 수신] chunk: {chunk} time {first_chunk_time - start_time} sec"
            )
            first = False

        full_reason += chunk
        yield (group_id, chunk)

    full_reason = full_reason.strip()
    end_time = time.time()
    ai_logger.info(
        f"[질문 전체 응답 수신 완료] time {end_time-start_time} sec, \n full_reason: {full_reason}"
    )
    yield ("RECOMMEND_DONE", group_id, None)

def extract_options_from_stream(raw: str) -> list[str] | None:
    import re

    json_match = re.search(r'"options"\s*:\s*(\[\s*".+?"\s*(?:,\s*".+?"\s*)*\])', raw, re.DOTALL)
    options_str = None

    if json_match:
        options_str = json_match.group(1)

    if not options_str:
        fallback_match = re.search(r'\[\s*"(.*?)"(?:\s*,\s*"(.*?)")+\s*\]', raw, re.DOTALL)
        if fallback_match:
            options_str = fallback_match.group(0)

    if not options_str:
        start_idx = raw.find('"options"')
        if start_idx != -1:
            array_start = raw.find('[', start_idx)
            array_end = raw.find(']', array_start)
            if array_start != -1 and array_end != -1:
                options_str = raw[array_start:array_end + 1]

    if not options_str:
        return None

    try:
        options = json.loads(options_str)
        if isinstance(options, list):
            return [o.strip() for o in options if isinstance(o, str)]
    except Exception:
        return None

    return None