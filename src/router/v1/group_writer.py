from fastapi import APIRouter
from src.schemas.v1.group_writer import GroupGenerationRequest, GroupDescriptionResponse, GroupPlanResponse
from src.services.v1.description_writer import generate_description
from src.services.v1.plan_writer import generate_plan

router = APIRouter()


@router.post("/groups/description", response_model=GroupDescriptionResponse)
def generate_group_description(data: GroupGenerationRequest) -> GroupDescriptionResponse:
    summary, description = generate_description(data)
    return GroupDescriptionResponse(summary=summary, description=description)


@router.post("/groups/plan", response_model=GroupPlanResponse)
def generate_group_plan(data: GroupGenerationRequest) -> GroupPlanResponse:
    plan = generate_plan(data)
    return GroupPlanResponse(plan=plan)
