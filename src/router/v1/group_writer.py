from fastapi import APIRouter, HTTPException
from src.schemas.v1.group_writer import GroupGenerationRequest, GroupDescriptionResponse, GroupPlanResponse
from src.services.v1.description_writer import generate_description
from src.services.v1.plan_writer import generate_plan

router = APIRouter()


@router.post("/groups/description", response_model=GroupDescriptionResponse)
def generate_group_description(data: GroupGenerationRequest) -> GroupDescriptionResponse:
    try:
        summary, description = generate_description(data)
        return GroupDescriptionResponse(summary=summary, description=description)
    except Exception as e:
        raise HTTPException(status_code=500, detail="모임 소개 생성 중 오류가 발생했습니다.")


@router.post("/groups/plan", response_model=GroupPlanResponse)
def generate_group_plan(data: GroupGenerationRequest) -> GroupPlanResponse:
    try:
        plan = generate_plan(data)
        return GroupPlanResponse(plan=plan)
    except Exception as e:
        raise HTTPException(status_code=500, detail="단계별 계획 생성 중 오류가 발생했습니다.")
