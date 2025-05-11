from src.schemas.v1.group_writer import GroupGenerationRequest
from src.core.vertex_client import gen_model, config_model
from src.core.logging_config import logger

def generate_plan(data: GroupGenerationRequest) -> str:
    prompt = f"""
        당신은 모임을 소개하는 AI 비서입니다.
        다음 모임 정보를 참고하여, 모임의 '목적'을 중심으로 **실현 가능한 활동 커리큘럼**을 스텝별로 작성해주세요.

        주의사항:
        - 부적절한 표현이나 욕설은 무시하고 건전하고 명확한 텍스트만 생성해주세요.
        - 출력에는 이모지(emoji)를 절대 포함하지 마세요.
        - 각 줄 끝에는 문자 그대로 1 개의 백슬래시와 소문자 n (`\n`)을 넣어주세요. 실제 줄바꿈은 프론트엔드에서 처리됩니다. 
        - 출력은 반드시 한 줄의 문자열로 반환되어야 합니다.

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
         - Step N: [제목] \n- [설명 문장 1] \n- [설명 문장 2] \n- [설명 문장 3] \n
        - 각 설명은 간결하고 실천 가능한 내용으로 구성하며 최대 3개까지만 작성합니다.
        - **모든 활동은 반드시 모임의 '목적'과 직접적으로 연결되어야 합니다.**
        - 너무 작게 나누지 말고, 의미 있는 단위로 단계화하세요.

        입력 정보:
        - 모임명: {data.name}
        - 목적: {data.goal}
        - 카테고리: {data.category}
        - 기간: {data.period} (예: "1개월 이하", "1~3개월", "6개월~1년", "1년 이상")
        """
    try:
        logger.info("[커리큘럼 생성 시작]", extra={"meeting_name": data.name})
        response = gen_model.generate_content(prompt, generation_config=config_model)
        result = response.text.strip()

        step_count = result.count("Step ")
        logger.info("[커리큘럼 생성 완료]", extra={"steps": step_count, "text_length": len(result)})
        return result

    except Exception as e:
        logger.exception("[Vertex Gemini 단계별 계획 생성 실패]")
        return ""

if __name__ == "__main__":
    from src.schemas.v1.group_writer import GroupGenerationRequest

    data = GroupGenerationRequest(
        name=".",
        goal=".",
        category="학습/자기계발",
        period="2주",
        isPlanCreated=False
    )
    plan = generate_plan(data)
    print(repr(plan))