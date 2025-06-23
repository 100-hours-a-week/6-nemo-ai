import json
from src.models.gemma_3_4b import call_vllm_api
from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

import re

async def handle_combined_question(
    answer: str | None,
    user_id: str,
    session_id: str,
    debug_mode: bool = True
) -> dict:
    if debug_mode:
        ai_logger.info("[Chatbot] Debug 모드: 고정 질문 반환", extra={"user_id": user_id, "session_id": session_id})
        return {
            "question": "어떤 활동을 좋아하시나요?",
            "options": ["운동", "스터디", "봉사활동", "게임"]
        }

    prompt = generate_combined_prompt(answer)
    ai_logger.info("[Chatbot] 질문 생성 프롬프트", extra={"prompt": prompt})

    try:
        raw_response = await call_vllm_api(prompt)
        ai_logger.info("[Chatbot] 원시 응답", extra={"response": raw_response})

        # ✅ JSON 부분만 추출 (정규식 기반)
        json_match = re.search(r"\{[\s\S]+?\}", raw_response)
        if not json_match:
            raise ValueError("JSON 부분 추출 실패")

        cleaned = json_match.group(0)
        parsed = json.loads(cleaned)

        question = parsed.get("question", "").strip()
        options = parsed.get("options", [])

        if not question or not isinstance(options, list) or len(options) < 2:
            ai_logger.warning("[Chatbot] 생성된 질문 형식 이상 → fallback 적용", extra={
                "question": question, "options": options
            })
            raise ValueError("질문 또는 보기 생성 실패")

        ai_logger.info("[Chatbot] 질문 생성 성공", extra={
            "user_id": user_id,
            "session_id": session_id,
            "question": question,
            "options": options
        })

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

def generate_combined_prompt(previous_answer: str | None) -> str:
    if previous_answer:
        context = f'"{previous_answer}" 이 답변을 참고해 사용자에게 모임 취향을 묻는 후속 질문을 작성하세요.'
    else:
        context = "모임 취향을 파악하기 위한 첫 질문을 작성하세요."

    return f"""
{context}

- 질문은 100~200자 이내로 자연스럽게 묻는 말투로 작성
- AI 자신에 대한 설명 없이, 사용자에게 직접 질문
- 선택지는 1~3단어 이내로 4개 작성

다음 형식의 JSON으로만 출력:
{{
  "question": "...",
  "options": ["...", "...", "...", "..."]
}}
""".strip()


async def handle_answer_analysis(
    messages: list[dict],
    user_id: str,
    session_id: str,
    debug_mode: bool = True
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

    if debug_mode:
        ai_logger.info("[추천] Debug 모드: 설명 생략", extra={"group_id": group_id})
        return {
            "groupId": group_id,
            "reason": "대화 내용을 바탕으로 가장 적합한 모임을 추천드립니다."
        }

    try:
        reason = await generate_explaination(messages, group_text)
        ai_logger.info("[추천] 추천 사유 생성 성공", extra={"group_id": group_id})
    except Exception as e:
        reason = "이 모임은 당신의 대화 내용과 가장 잘 어울려 추천드립니다."
        ai_logger.warning("[추천] 추천 사유 생성 실패", extra={"group_id": group_id, "error": str(e)})

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

    - 최대 300자
    - 제목 스타일(예: `###`, `**`)을 활용해 **모임 이름**을 강조하세요
    - 줄바꿈(`\\n` 또는 빈 줄)을 활용해 시각적으로 구분하세요
    - 리스트(`-`) 또는 하이라이트(`**`)를 적절히 사용하세요
    - 설명은 300자 이내로, 핵심만 간결하게    
    - 텍스트 설명만 출력 (JSON, 따옴표, 리스트 등 X)
    - 문장은 하나로 자연스럽게 이어지며, 반복 없이 핵심만 담을 것
    - "AI:", "설명:", "- " 같은 포맷은 절대 사용하지 마세요

    바로 아래에 설명을 작성하세요.
    """.strip()

    try:
        explanation = await call_vllm_api(prompt, max_tokens=400)
        if debug:
            print("📦 생성된 추천 설명:\n", explanation)
        return explanation.strip()
    except Exception as e:
        print(f"[❗️generate_explaination 에러] {e}")
        return "추천 사유를 생성하는 데 실패했습니다."
