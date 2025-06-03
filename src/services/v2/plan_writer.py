from src.schemas.v1.group_writer import GroupGenerationRequest
from src.core.ai_logger import get_ai_logger
from src.services.v2.local_model import local_model_generate    # 로컬 모델 호출로 교체
import asyncio

ai_logger = get_ai_logger()

async def generate_plan(data: GroupGenerationRequest) -> str:
    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.
    다음 모임 정보를 참고하여, 모임의 '목적'을 중심으로 **실현 가능한 활동 커리큘럼**을 스텝별로 작성해주세요.

    주의사항:
    - 부적절한 표현이나 욕설은 무시하고 건전하고 명확한 텍스트만 생성해주세요.
    - 출력에는 이모지(emoji)를 절대 포함하지 마세요.
    - **각 줄마다 실제 줄바꿈(Enter 키)를 사용해주세요. `\\n`은 쓰지 마세요.**
    - 출력은 파이썬의 멀티라인 문자열처럼, 줄이 실제로 바뀌는 형태여야 합니다.
    - 한 줄로 이어 쓰지 말고, 각 단계와 설명을 줄바꿈을 활용하여 명확하게 나누어 작성해주세요.

    조건:
    - 아래 `기간` 항목은 정수형이 아닌 '기간 범위(예: 1~3개월)'로 주어질 수 있습니다.
    - 이 경우, LLM은 입력된 기간 범위를 참고하여 **적절한 단계 수(1~8단계 이내)**를 추정해야 합니다.
    - 일반적으로 다음과 같이 해석하세요:
      - 1개월 이하 → 약 2~3단계
      - 1~3개월 → 약 3~5단계
      - 3~6개월 → 약 5~6단계
      - 6개월~1년 → 약 6~7단계
      - 1년 이상 → 7~8단계
    - 단, **무조건 8단계를 채우지 말고**, 모임 목적과 활동 적절성에 따라 1~8단계 내에서 유연하게 결정하세요.
    - 각 단계는 다음 형식을 따릅니다:

    - Step N: [제목]
        - [설명 문장 1]
        - [설명 문장 2]
        - [설명 문장 3]

    + 아래 출력 형식을 반드시 정확히 따르세요. 줄 간 공백 없이 출력하세요.
    - 각 설명은 간결하고 실천 가능한 내용으로 구성하며, 최대 3개까지만 작성하세요.
    - **모든 활동은 반드시 모임의 '목적'과 직접적으로 연결되어야 합니다.**
    - 너무 작게 나누지 말고, 의미 있는 단위로 단계화하세요.
    - 출력은 실제 줄바꿈(Enter)을 사용하여 파이썬의 멀티라인 문자열처럼 구성되어야 합니다.

    입력 정보:
    - 모임명: {data.name}
    - 목적: {data.goal}
    - 카테고리: {data.category}
    - 기간: {data.period}
    """
    try:
        ai_logger.info("[AI-v2] [커리큘럼 생성 시작]", extra={"meeting_name": data.name})
        # 로컬 모델 호출로 교체
        response = await local_model_generate(prompt, max_new_tokens=512)
        result = response.strip()

        step_count = result.count("Step ")
        ai_logger.info("[AI-v2] [커리큘럼 생성 완료]",
                       extra={"steps": step_count, "text_length": len(result)})
        return result

    except Exception:
        ai_logger.exception("[AI-v2] [로컬모델 단계별 계획 생성 실패]")
        return ""


if __name__ == "__main__":
    data = GroupGenerationRequest(
        name="토익 스터디 모임",
        goal="함께 공부해서 다음 달 토익 시험 목표 점수 달성하기",
        category="학습/자기계발",
        period="2주",
        isPlanCreated=False
    )

    async def run_test():
        plan = await generate_plan(data)
        print("\n생성된 커리큘럼:\n")
        print(plan)

    asyncio.run(run_test())