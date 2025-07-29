"""
V1 Group Information Service - Simple retry logic implementation
Builds meeting data from user input with basic retry mechanism
"""

from app.schemas.groups.group_information import MeetingInput, MeetingData
from app.schemas.groups.group_writer import GroupGenerationRequest
from app.services.v1.tag_extraction import extract_tags
from app.services.v1.description_writer import generate_description
from app.services.v1.plan_writer import generate_plan
from app.core.ai_logger import get_ai_logger
import asyncio

ai_logger = get_ai_logger()

async def build_meeting_data(input: MeetingInput) -> MeetingData:
    """
    V1 build_meeting_data with basic retry logic
    
    Args:
        input (MeetingInput): User input containing meeting requirements
        
    Returns:
        MeetingData: Generated meeting data
    """
    
    ai_logger.info("[AI] [모임 정보 생성 시작]", extra={
        "meeting_name": input.name,
        "has_plan": input.isPlanCreated
    })

    group_data = GroupGenerationRequest(
        name=input.name,
        goal=input.goal,
        category=input.category,
        period=input.period,
        isPlanCreated=input.isPlanCreated,
    )

    # Simple retry logic - try up to 3 times
    max_retries = 3
    for attempt in range(max_retries):
        try:
            summary, description = await generate_description(group_data)
            tags = await extract_tags(description)
            plan = await generate_plan(group_data) if input.isPlanCreated else None

            ai_logger.info("[AI] [모임 정보 생성 완료]", extra={"tags_count": len(tags)})

            return MeetingData(
                name=input.name,
                summary=summary,
                description=description,
                tags=tags,
                plan=plan,
            )

        except Exception as e:
            ai_logger.warning(f"[AI] [모임 정보 생성 시도 {attempt + 1}/{max_retries} 실패]: {str(e)}")
            if attempt == max_retries - 1:  # Last attempt
                ai_logger.exception("[AI] [모임 정보 생성 실패]")
                return MeetingData(
                    name=input.name,
                    summary="",
                    description="",
                    tags=[],
                    plan=None,
                )
            # Wait a bit before retry
            await asyncio.sleep(1.0)

    # This should never be reached, but just in case
    return MeetingData(
        name=input.name,
        summary="",
        description="",
        tags=[],
        plan=None,
    )


if __name__ == "__main__":
    """Test the V1 group information service"""
    test_input = MeetingInput(
        name="딥러닝 실전 스터디",
        goal="딥러닝 실전 프로젝트 완수와 포트폴리오 제작",
        category="인공지능",
        period="4주",
        isPlanCreated=True,
    )

    async def run_test():
        result = await build_meeting_data(test_input)
        print(result)

    asyncio.run(run_test())
