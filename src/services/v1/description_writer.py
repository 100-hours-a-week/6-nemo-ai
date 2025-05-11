from typing import Tuple
from src.schemas.v1.group_writer import GroupGenerationRequest
from src.core.vertex_client import gen_model, config_model
from src.core.cloud_logging import logger


def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.

    주의 사항:
    - 사용자의 입력에 욕설, 비하, 공격적 표현이 포함된 경우 이를 무시하고 **건전한 텍스트**만 생성해주세요.
    - 욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.
    - 출력에는 절대 이모지(emoji)를 포함하지 마세요.

    다음 모임 정보를 바탕으로 아래 두 항목을 생성해주세요:

    1. 한 줄 소개 (64자 이내): 모임의 상세소개를 간단명료하게 요약하여 모임의 성격이 드러나도록 하나의 문장으로 작성하되, 반드시 **명사**로 자연스럽게 마무리해주세요.  
       예시: 실무 중심으로 안드로이드 앱을 개발하는 스터디 모임

    2. 상세 설명 (500자 이내): 어떤 활동을 하는 모임인지, 누가 참여하면 좋은지, 기간 동안 어떤 방식으로 운영되는지 등을 친절하고 명확하게 작성해주세요.
     - 각 문장을 끝낼 때마다 반드시 `\n`을 넣어 주세요. 문장 단위로 줄을 나눈 것처럼 작성해야 합니다.

    출력 조건:
    - 실제 줄바꿈(엔터)은 절대 사용하지 마세요.
    - 각 항목의 줄 끝에는 반드시 문자 그대로 **백슬래시 1 개와 소문자 n (`\n`)**을 넣어주세요.
    - 출력은 다음 형식처럼 **한 줄 문자열**로 이어져야 합니다:

    예시 출력:
    - 한 줄 소개:\n- 상세 설명:\n

    입력 정보:
    - 모임명: {data.name}
    - 목적: {data.goal}
    - 카테고리: {data.category}
    - 기간: {data.period}
    """
    response = gen_model.generate_content(prompt, generation_config=config_model)
    full_text = response.text.replace('\n', '')
    parts = full_text.split("- 한 줄 소개:")
    if len(parts) < 2:
        raise ValueError(f"'한 줄 소개' 구간 파싱 실패:\n{full_text}")

    try:
        logger.info("[요약 생성 시작]", extra={"meeting_name": data.name})
        response = gen_model.generate_content(prompt, generation_config=config_model)
        full_text = response.text.replace('\n', '')

        parts = full_text.split("- 한 줄 소개:")
        if len(parts) < 2:
            logger.warning("[파싱 실패] '한 줄 소개' 구간 없음", extra={"preview": full_text[:80]})
            return "", ""

        after_intro = parts[1]
        subparts = after_intro.split("- 상세 설명:")
        if len(subparts) < 2:
            logger.warning("[파싱 실패] '상세 설명' 구간 없음", extra={"preview": full_text[:80]})
            return "", ""

        summary = subparts[0].strip()
        description = subparts[1].strip()

        logger.info("[모임 소개 생성 완료]", extra={"summary_length": len(summary), "description_length": len(description)})
        return summary, description

    except Exception as e:
        logger.exception("[Vertex Gemini 소개 생성 실패]")
        return "", ""

if __name__ == "__main__":
    from src.schemas.v1.group_writer import GroupGenerationRequest

    data = GroupGenerationRequest(
        name=".",
        goal=".",
        category="학습/자기계발",
        period="2주",
        isPlanCreated=False
    )

    summary, description = generate_description(data)
    print(repr(summary))
    print(repr(description))