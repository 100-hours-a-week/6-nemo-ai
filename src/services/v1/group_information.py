from src.schemas.v1.group_information import MeetingInput, MeetingData
from src.schemas.v1.group_writer import GroupGenerationRequest
from src.services.v1.tag_extraction import extract_tags
from src.services.v1.description_writer import generate_description
from src.services.v1.plan_writer import generate_plan
from src.core.ai_logger import get_ai_logger
from concurrent.futures import ThreadPoolExecutor

ai_logger = get_ai_logger()

def build_meeting_data(input: MeetingInput) -> MeetingData:
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

    try:
        with ThreadPoolExecutor() as executor:
            future_desc = executor.submit(generate_description, group_data)
            summary, description = future_desc.result()

            future_tags = executor.submit(extract_tags, description)
            future_plan = executor.submit(generate_plan, group_data) if input.isPlanCreated else None

            tags = future_tags.result()
            plan = future_plan.result() if future_plan else None

        ai_logger.info("[AI] [모임 정보 생성 완료]", extra={"tags_count": len(tags)})

        return MeetingData(
            name=input.name,
            summary=summary,
            description=description,
            tags=tags,
            plan=plan,
        )
    except Exception:
        ai_logger.exception("[AI] [모임 정보 생성 실패]")
        return MeetingData(
            name=input.name,
            summary="",
            description="",
            tags=[],
            plan=None,
        )

if __name__ == "__main__":
    test_input = MeetingInput(
        name="딥러닝 실전 스터디",
        goal="딥러닝 실전 프로젝트 완수와 포트폴리오 제작",
        category="인공지능",
        period="4주",
        isPlanCreated=True,
    )

    result = build_meeting_data(test_input)
    print(repr(result))
