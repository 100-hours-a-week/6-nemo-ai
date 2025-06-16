from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from src.schemas.v1.group_information import APIResponse, MeetingInput
from src.services.v2.group_information import build_meeting_data
from src.core.moderation import analyze_queued, is_request_valid
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()
router = APIRouter()

REJECTION_REASONS = {
    "TOXICITY": "전체적으로 공격적인 표현이 감지되었습니다.",
    "INSULT": "모욕적인 표현이 포함되어 있습니다.",
    "THREAT": "위협적인 내용이 포함되어 있습니다.",
    "IDENTITY_ATTACK": "특정 집단이나 정체성을 공격하는 표현이 포함되어 있습니다."
}

@router.post("/ai/v2/groups/information", response_model=APIResponse, response_model_exclude_none=True)
async def create_meeting(meeting: MeetingInput, request: Request):
    ai_logger.info("[AI-v2] [POST /groups/information] 모임 정보 생성 요청 수신", extra={"meeting_name": meeting.name})
    input_text = f"{meeting.name}\n{meeting.goal}"

    try:
        scores = await analyze_queued(input_text)
        ai_logger.info("[AI-v2] [유해성 분석] 분석 결과 수신", extra={"scores": scores})
    except Exception:
        ai_logger.exception("[AI-v2] [유해성 분석] 분석 중 예외 발생")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "유해성 분석 중 오류가 발생했습니다.",
                "data": None
            }
        )

    if not is_request_valid(scores):
        max_attr, max_score = max(scores.items(), key=lambda x: x[1])
        reason_msg = REJECTION_REASONS.get(max_attr, "부적절한 표현이 포함되어 있습니다.")

        ai_logger.warning("[AI-v2] [유해성 차단] 요청 거부됨", extra={
            "reason": reason_msg,
            "attribute": max_attr,
            "score": round(max_score, 3),
            "endpoint": request.url.path
        })

        raise HTTPException(status_code=422, detail=reason_msg)

    try:
        meeting_data = await build_meeting_data(meeting)
        ai_logger.info("[AI-v2] [모임 생성] 모임 정보 생성 성공")
    except Exception:
        ai_logger.exception("[AI-v2] [모임 생성] 모임 정보 생성 중 예외 발생")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "모임 정보 생성 중 오류가 발생했습니다.",
                "data": None
            }
        )

    return APIResponse(
        code=200,
        message="모임 정보 생성 완료",
        data=meeting_data
    )