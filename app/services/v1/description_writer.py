from typing import Tuple
from app.schemas.groups.group_writer import GroupGenerationRequest
# from app.core.cloud_logging import logger
from app.core.ai_logger import get_ai_logger
from app.core.vertex_client import smart_generate
from app.prompts.prompt_loader import load_prompt_template
import asyncio

ai_logger = get_ai_logger()

async def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = load_prompt_template("description_writer_v1",
                                  name=data.name,
                                  goal=data.goal,
                                  category=data.category,
                                  period=data.period)
    try:
        ai_logger.info("[AI] [요약 생성 시작]", extra={"meeting_name": data.name})
        response = await smart_generate(prompt)

        parts = response.split("한 줄 소개:")
        if len(parts) < 2:
            ai_logger.warning("[AI] [파싱 실패] '한 줄 소개' 구간 없음", extra={"preview": response[:80]})
            return "", ""

        after_intro = parts[1]
        subparts = after_intro.split("상세 설명:")
        if len(subparts) < 2:
            ai_logger.warning("[AI] [파싱 실패] '상세 설명' 구간 없음", extra={"preview": response[:80]})
            return "", ""

        summary = subparts[0].strip()
        description = subparts[1].strip()

        ai_logger.info("[AI] [모임 소개 생성 완료]",
                       extra={"summary_length": len(summary), "description_length": len(description)})
        return summary, description

    except Exception as e:
        ai_logger.exception("[AI] [Vertex Gemini 소개 생성 실패]")
        return "", ""

if __name__ == "__main__":
    import asyncio
    from app.schemas.groups.group_writer import GroupGenerationRequest

    data = GroupGenerationRequest(
        name="주말 러닝 크루",
        goal="매주 함께 뛰며 체력과 건강을 관리하기",
        category="운동/건강",
        period="3개월",
        isPlanCreated=False
    )

    async def run_test():
        summary, description = await generate_description(data)
        print("\n한 줄 소개:\n", summary)
        print("\n상세 설명:\n", description)

    asyncio.run(run_test())