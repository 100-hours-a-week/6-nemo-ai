#src/services/group_writer.py

from models.group import GroupGenerationRequest, GroupGenerationResponse
from services.summary_writer import generate_summary_and_tags
from services.plan_writer import generate_plan

async def generate_group_info(data: GroupGenerationRequest) -> GroupGenerationResponse:

    summary, description, tags = await generate_summary_and_tags(data)

    plan = await generate_plan(data) if data.isPlanCreated else None

    return GroupGenerationResponse(
        summary=summary,
        description=description,
        plan=plan,
        tags=tags,
    )

