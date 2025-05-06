from src.schemas.v1.group_information import MeetingInput, MeetingData
from src.services.v1.tag_extraction import extract_tags, pick_best_by_vector_similarity
from src.services.v1.summary_writer import generate_summary
from src.services.v1.plan_writer import generate_plan
from src.services.v1.plan_writer import GroupGenerationRequest
from src.services.v1.vector_db import embed
async def build_meeting_data(input: MeetingInput) -> MeetingData:
    # 1. 요약 + 상세 설명 생성
    group_data = GroupGenerationRequest(
        name=input.name,
        goal=input.goal,
        category=input.category,
        period=input.period,
        isPlanCreated=input.isPlanCreated
    )
    summary, description = await generate_summary(group_data)

    # 2. 태그 추출
    extracted = await extract_tags(description)
    tags = pick_best_by_vector_similarity(extracted, base_text=description, embed_fn=embed)

    # 3. 계획 생성
    plan = await generate_plan(group_data) if input.isPlanCreated else "계획은 추후 구성 예정입니다."

    # 4. MeetingData 생성
    return MeetingData(
        name=input.name,
        summary=summary,         # 요약 (요약된 1~2문장)
        description=description, # 상세 설명 (풍부한 정보)
        tags=tags,
        plan=plan
    )