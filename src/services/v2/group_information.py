from src.schemas.v1.group_information import MeetingInput, MeetingData
from src.schemas.v1.group_writer import GroupGenerationRequest
from src.services.v2.tag_extraction import extract_tags
from src.services.v2.description_writer import generate_description
from src.services.v2.plan_writer import generate_plan
from src.core.ai_logger import get_ai_logger
import asyncio

ai_logger = get_ai_logger()

async def build_meeting_data(input: MeetingInput) -> MeetingData:
    ai_logger.info("[AI-v2] [모임 정보 생성 시작]", extra={
        "meeting_name": input.name,
        "has_plan": input.isPlanCreated
    })

    # 요청 데이터를 GroupGenerationRequest로 변환
    group_data = GroupGenerationRequest(
        name=input.name,
        goal=input.goal,
        category=input.category,
        period=input.period,
        isPlanCreated=input.isPlanCreated,
    )

    try:
        summary, description = await generate_description(group_data)
        tags = await extract_tags(description)
        plan = await generate_plan(group_data) if input.isPlanCreated else None

        ai_logger.info("[AI-v2] [모임 정보 생성 완료]", extra={"tags_count": len(tags)})

        return MeetingData(
            name=input.name,
            summary=summary,
            description=description,
            tags=tags,
            plan=plan,
        )

    except Exception:
        ai_logger.exception("[AI-v2] [모임 정보 생성 실패]")
        return MeetingData(
            name=input.name,
            summary="",
            description="",
            tags=[],
            plan=None,
        )

if __name__ == "__main__":
    test_input = MeetingInput(
        name="토익 스터디 모임",
        goal="함께 공부해서 다음 달 토익 시험 목표 점수 달성하기",
        category="학습/자기계발",
        period="2주",
        isPlanCreated=True,
    )

    async def run_test():
        result = await build_meeting_data(test_input)
        print(result)

    asyncio.run(run_test())
