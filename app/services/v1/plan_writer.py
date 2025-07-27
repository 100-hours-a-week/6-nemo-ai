from app.schemas.groups.group_writer import GroupGenerationRequest
from app.core.ai_logger import get_ai_logger
from app.core.vertex_client import smart_generate
from app.prompts.prompt_loader import load_prompt_template
import asyncio

ai_logger = get_ai_logger()


async def generate_plan(data: GroupGenerationRequest) -> str:
    prompt = load_prompt_template("plan_writer_v1",
                                  name=data.name,
                                  goal=data.goal,
                                  category=data.category,
                                  period=data.period)
    try:
        ai_logger.info("[AI] [커리큘럼 생성 시작]", extra={"meeting_name": data.name})
        response = await smart_generate(prompt)
        result = response.strip()

        step_count = result.count("Step ")
        ai_logger.info("[AI] [커리큘럼 생성 완료]", extra={"steps": step_count, "text_length": len(result)})
        return result

    except Exception:
        ai_logger.exception("[AI] [Vertex Gemini 단계별 계획 생성 실패]")
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