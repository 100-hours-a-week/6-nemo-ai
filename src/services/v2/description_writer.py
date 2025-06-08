from typing import Tuple
from src.schemas.v1.group_writer import GroupGenerationRequest
# from src.core.cloud_logging import logger
from src.core.ai_logger import get_ai_logger
from src.services.v2.local_model import local_model_generate   #로컬 모델 호출로 교체

ai_logger = get_ai_logger()

async def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.

    출력 내용:
    - 한 줄 소개 : 모임의 핵심 목적을 간결하고 명확하게 50자 이내로 요약한 한 문장입니다. 문장이 반드시 **명사형**으로 끝나야 합니다.
    - 상세 설명 : 모임의 목적에 맞게 추천 대상과 모임 운영 방식에 대해 300자 이내로 작성해주세요.

    입력 정보:
    - 모임명: {data.name}
    - 목적: {data.goal}
    - 카테고리: {data.category}
    - 기간: {data.period}
    """
    try:
        ai_logger.info("[AI-v2] [요약 생성 시작]", extra={"meeting_name": data.name})

        # 로컬 모델로 교체
        response = await local_model_generate(prompt, max_new_tokens=512)
        raw = response.strip()

        # 결과 파싱 (v1과 동일하게 유지)
        parts = response.split("한 줄 소개:")
        if len(parts) < 2:
            ai_logger.warning("[AI-v2] [파싱 실패] '한 줄 소개' 구간 없음", extra={"preview": response[:80]})
            return "", ""

        after_intro = parts[1]
        subparts = after_intro.split("상세 설명:")
        if len(subparts) < 2:
            ai_logger.warning("[AI-v2] [파싱 실패] '상세 설명' 구간 없음", extra={"preview": response[:80]})
            return "", ""

        summary = subparts[0].strip()
        description = subparts[1].strip()

        ai_logger.info("[AI-v2] [모임 소개 생성 완료]",
                       extra={"summary_length": len(summary), "description_length": len(description)})
        return summary, description

    except Exception as e:
        ai_logger.exception("[AI-v2] [로컬모델 소개 생성 실패]")
        return "", ""


if __name__ == "__main__":
    import asyncio
    from src.schemas.v1.group_writer import GroupGenerationRequest

    data = GroupGenerationRequest(
        name="로미의 백반기행",
        goal="판교의 맛집과 분좋카를 찾아 다니며 즐기는 친목 모임",
        category="친목/사교",
        period="3개월",
        isPlanCreated=False
    )


    async def run_test():
        summary, description = await generate_description(data)
        print("\n한 줄 소개:\n", summary)
        print("\n상세 설명:\n", description)


    asyncio.run(run_test())