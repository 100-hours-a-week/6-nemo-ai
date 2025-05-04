from src.models.group import GroupGenerationRequest, GroupGenerationResponse
from src.services.summary_writer import generate_summary
from src.services.plan_writer import generate_plan

async def generate_group_info(data: GroupGenerationRequest) -> GroupGenerationResponse:

    summary, description = await generate_summary(data)

    plan = await generate_plan(data) if data.isPlanCreated else None

    return GroupGenerationResponse(
        summary=summary,
        description=description,
        plan=plan
    )

