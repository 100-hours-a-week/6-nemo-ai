from src.schemas.v1.group_information import MeetingInput, MeetingData
from src.schemas.v1.group_writer import GroupGenerationRequest
from src.services.v1.tag_extraction import extract_tags
from src.services.v1.description_writer import generate_description
from src.services.v1.plan_writer import generate_plan

def build_meeting_data(input: MeetingInput) -> MeetingData:
    group_data = GroupGenerationRequest(
        name=input.name,
        goal=input.goal,
        category=input.category,
        period=input.period,
        isPlanCreated=input.isPlanCreated,
    )

    summary, description = generate_description(group_data)
    tags = extract_tags(description)
    plan = generate_plan(group_data) if input.isPlanCreated else None
    return MeetingData(
        name=input.name,
        summary=summary,
        description=description,
        tags=tags,
        plan=plan,
    )

if __name__ == "__main__":
    import src.core.vertex_client
    from src.schemas.v1.group_information import MeetingInput

    test_input = MeetingInput(
        name="딥러닝 실전 스터디",
        goal="딥러닝 실전 프로젝트 완수와 포트폴리오 제작",
        category="인공지능",
        period="4주",
        isPlanCreated=True,
    )

    result = build_meeting_data(test_input)
    print(result)

