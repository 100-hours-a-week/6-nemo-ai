from fastapi import APIRouter, HTTPException
from src.schemas.v1.group_writer import GroupGenerationRequest, GroupDescriptionResponse, GroupPlanResponse
from src.services.v1.description_writer import generate_description
from src.services.v1.plan_writer import generate_plan
from src.core.logging_config import logger

router = APIRouter()


@router.post("/groups/description", response_model=GroupDescriptionResponse)
def generate_group_description(data: GroupGenerationRequest) -> GroupDescriptionResponse:
    try:
        summary, description = generate_description(data)
        logger.info("[그룹 소개 생성] Gemini 요약 및 소개 생성 성공")
        return GroupDescriptionResponse(summary=summary, description=description)
    except Exception:
        logger.exception("[그룹 소개 생성] Gemini API 호출 또는 파싱 중 예외 발생")
        raise HTTPException(status_code=500, detail="그룹 소개 생성 중 오류가 발생했습니다.")


@router.post("/groups/plan", response_model=GroupPlanResponse)
def generate_group_plan(data: GroupGenerationRequest) -> GroupPlanResponse:
    logger.info("[POST /groups/plan] 그룹 커리큘럼 생성 요청 수신", extra={"meeting_name": data.name})

    try:
        plan = generate_plan(data)
        logger.info("[그룹 커리큘럼 생성] 계획 생성 성공")
        return GroupPlanResponse(plan=plan)
    except Exception:
        logger.exception("[그룹 커리큘럼 생성] Gemini API 호출 또는 파싱 중 예외 발생")
        raise HTTPException(status_code=500, detail="그룹 커리큘럼 생성 중 오류가 발생했습니다.")
