from src.schemas.v1.group_writer import GroupGenerationRequest
from src.core.ai_logger import get_ai_logger
from src.models.gemma_3_4b import call_vllm_api  # 로컬 모델 호출로 교체
import asyncio
import re

ai_logger = get_ai_logger()

def clean_output_to_steps(text:str) -> str:
    match = re.search(r"(Step\s*1[\s\S]*)", text, re.IGNORECASE)
    if not match:
        return text.strip()

    steps_text = match.group(1).strip()

    # 줄별로 순회하며 Step N: 앞의 들여쓰기만 제거
    cleaned_lines = []
    for line in steps_text.splitlines():
        if re.match(r"\s*Step\s*\d+:", line, re.IGNORECASE):
            cleaned_lines.append(line.lstrip())   #들여쓰기 제거
        else:
            cleaned_lines.append(line) # 유지
    return "\n".join(cleaned_lines)

async def generate_plan(data: GroupGenerationRequest) -> str:
    prompt = f"""
    당신은 모임의 '목적'을 중심으로 실현 가능한 활동 커리큘럼을 스텝별로 작성하는 AI입니다.

    # 조건
    - 입력된 기간을 참고하여 적절한 단계 수(4~8단계 이내)를 추정해야 합니다.
    - 단, 무조건 8단계를 채우지 말고, 모임 목적과 활동 적절성에 따라 4~8단계 내에서 결정하세요.
    - 출력 형식은 순수한 텍스트로만 작성합니다. 코드 예시나 함수 정의는 작성하지 않습니다.
    - 각 단계는 다음 형식을 따릅니다:
    - Step N: [제목]
        - [설명 문장 1]
        - [설명 문장 2]
        - [설명 문장 3]

    # 입력 정보
    - 모임명: {data.name}
    - 목적: {data.goal}
    - 카테고리: {data.category}
    - 기간: {data.period}
    """
    try:
        ai_logger.info("[AI-v2] [커리큘럼 생성 시작]", extra={"meeting_name": data.name})
        # 로컬 모델 호출로 교체
        response = await call_vllm_api(prompt, max_tokens=700)

        # 문자열로 추정되는 경우 바로 처리
        plan_text = response.strip() if isinstance(response, str) else str(response)
        step_count = plan_text.count("Step ")

        ai_logger.info("[AI-v2] [커리큘럼 생성 완료]",
                       extra={"steps": step_count, "text_length": len(plan_text)})
        return clean_output_to_steps(plan_text)

    except Exception:
        ai_logger.exception("[AI-v2] [로컬모델 단계별 계획 생성 실패]")
        return ""


if __name__ == "__main__":
    data = GroupGenerationRequest(
        name="RAG 스터디 모임",
        goal="RAG 이론 공부하기",
        category="개발",
        period="1개월 이하",
        isPlanCreated=True
    )

    async def run_test():
        plan = await generate_plan(data)
        print("\n생성된 커리큘럼:\n")
        print(plan)


    asyncio.run(run_test())