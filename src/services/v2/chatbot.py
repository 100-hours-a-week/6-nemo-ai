from src.models.gemma_3_4b import call_vllm_api
from src.vector_db.vector_searcher import search_similar_documents, get_user_joined_group_ids
import json
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

async def handle_combined_question(
    answer: str | None,
    user_id: str,
    session_id: str,
    debug_mode: bool = True
) -> dict:
    """
    이전 답변(answer)을 바탕으로 다음 질문을 생성하여
    question + options(answer list)만 반환합니다.
    """

    if debug_mode:
        ai_logger.info("[Chatbot] Debug 모드: 고정 질문/선택지 반환", extra={
            "user_id": user_id,
            "session_id": session_id
        })
        return {
            "question": "어떤 활동을 좋아하시나요?",
            "options": ["운동", "스터디", "봉사활동", "게임"]
        }

    prompt = generate_combined_prompt(answer)

    try:
        raw_response = await call_vllm_api(prompt)

        # 불필요한 마크다운 제거 및 정제
        cleaned = raw_response.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(cleaned)

        question = parsed.get("question", "").strip()
        options = parsed.get("options", [])

        if not question or not isinstance(options, list) or len(options) < 2:
            raise ValueError("질문 또는 보기 생성 실패")

        ai_logger.info("[Chatbot] 질문 생성 성공", extra={
            "user_id": user_id,
            "session_id": session_id,
            "question": question
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
            "question": "죄송합니다. 질문을 생성하는 데 문제가 발생했어요.",
            "options": []
        }

def generate_combined_prompt(previous_answer: str | None) -> str:
    """
    사용자의 이전 응답이 있다면 자연스럽게 이어지는 문장과 질문을 생성하고,
    없다면 모임 성향 파악을 위한 첫 질문을 구성하는 프롬프트를 반환합니다.
    생성된 질문은 추천할 모임을 더 정확히 파악하는 데 도움이 되어야 합니다.
    """

    if previous_answer:
        intro = (
            f"당신은 친절한 모임 추천 챗봇입니다.\n"
            f"사용자가 이전에 아래와 같이 응답했습니다:\n\n"
            f"\"{previous_answer}\"\n\n"
            f"이 내용을 바탕으로, 해당 사용자의 성향이나 관심사를 파악하여 모임을 더 잘 추천할 수 있도록\n"
            f"이어지는 자연스러운 문장과 질문을 만들어 주세요.\n"
        )
    else:
        intro = (
            "당신은 친절한 모임 추천 챗봇입니다.\n"
            "사용자가 처음 질문에 응답하는 상황입니다.\n"
            "사용자의 모임 참여 성향이나 관심사를 파악하기 위해\n"
            "적절한 첫 질문을 자연스럽고 간결한 문장으로 구성해주세요.\n"
        )

    instruction = (
        "다음 형식의 JSON으로 출력하세요:\n\n"
        "{\n"
        "  \"question\": \"자연스러운 도입 문장과 함께 이어지는 질문\",\n"
        "  \"options\": [\"선택지1\", \"선택지2\", \"선택지3\", \"선택지4\"]\n"
        "}\n\n"
        "질문은 추천할 모임을 고를 때 도움이 될 수 있도록\n"
        "사용자의 관심사, 활동 스타일, 시간대, 사람과의 교류 방식 등과 관련된 내용을 다뤄야 합니다.\n"
        "질문 길이는 약 100자 이내로 제한합니다.\n"
        "문장은 반드시 자연스러운 대화처럼 시작하고, 마지막에 질문으로 끝나야 합니다.\n"
        "선택지는 4개로 구성하고, 각각은 명확하고 중복되지 않으며 4단어 이내로 작성해주세요."
    )

    return intro + instruction

async def handle_answer_analysis(
    messages: list[dict],
    user_id: str,
    session_id: str,
    debug_mode: bool = True  # LLM 호출 없이 고정 사유만 반환
) -> dict:
    if not messages:
        ai_logger.warning("[추천] 빈 메시지 수신", extra={"session_id": session_id})
        return {
            "groupId": -1,
            "reason": "대화 내용이 부족하여 추천을 생성할 수 없습니다."
        }

    # 1. 대화 내용 합치기
    combined_text = "\n".join([f"{m['role']}: {m['text']}" for m in messages])
    ai_logger.info("[추천] 메시지 병합 완료", extra={"session_id": session_id})

    # 2. 이미 참여한 그룹 제외
    try:
        joined_ids = get_user_joined_group_ids(user_id)
    except Exception:
        joined_ids = set()
        ai_logger.warning("[추천] 유저 참여 그룹 조회 실패", extra={"session_id": session_id})

    # 3. 유사 그룹 검색
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

    # 4. 추천 그룹 선택
    top_result = filtered[0]
    group_id = int(top_result["metadata"]["groupId"])
    group_text = top_result["text"]

    # 5. 설명 생성 (LLM 호출은 생략하고, 고정된 메시지로 대체)
    if debug_mode:
        ai_logger.info("[추천] Debug 모드: LLM 없이 설명 생성 생략", extra={"group_id": group_id})
        return {
            "groupId": group_id,
            "reason": "대화 내용을 바탕으로 가장 적합한 모임을 추천드립니다."
        }

    try:
        reason = await generate_explaination(messages, group_text)
        ai_logger.info("[추천] 추천 사유 생성 완료", extra={"group_id": group_id})
    except Exception:
        reason = "이 모임은 당신의 대화 내용과 가장 잘 어울려 추천드립니다."
        ai_logger.warning("[추천] 추천 사유 생성 실패", extra={"group_id": group_id})

    return {
        "groupId": group_id,
        "reason": reason
    }

async def generate_explaination(messages: list[dict], group_text: str, debug: bool = False) -> str:
    """
    전체 대화 히스토리 + 추천 그룹 정보를 바탕으로
    이 그룹이 사용자에게 적합한 이유를 자연스럽게 설명합니다.
    """

    # 대화 형식 문자열로 변환 (AI부터 시작해야 함)
    conversation = "\n".join([f"{m['role']}: {m['text']}" for m in messages])

    # 프롬프트 구성
    prompt = f"""
당신은 대화형 추천 챗봇입니다.
다음은 사용자와의 대화 내용입니다. 대화는 'ai'로 시작합니다.

{conversation}

그리고 아래는 추천 후보 모임의 정보입니다:

"{group_text.strip()}"

위 대화를 바탕으로, 이 모임이 사용자의 관심사와 어떻게 잘 맞는지 300자 이내로 공감의 말로 시작하여 설명해 주세요.
너무 일반적이거나 단순한 문장이 아닌, 사용자의 대화 흐름과 연결된 추천 사유여야 합니다.

형식:
- 설명만 출력하세요. "추천드립니다" 등의 마무리 말은 포함해도 괜찮습니다.
- JSON, 마크다운 등 포맷은 포함하지 마세요.
    """.strip()

    try:
        explanation = await call_vllm_api(prompt, max_tokens=400)

        if debug:
            print("📦 생성된 추천 설명:\n", explanation)

        return explanation.strip()

    except Exception as e:
        print(f"[❗️generate_explaination 에러] {e}")
        return "추천 사유를 생성하는 데 실패했습니다."