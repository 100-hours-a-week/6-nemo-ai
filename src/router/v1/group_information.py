from fastapi import APIRouter
from src.schemas.v1.group_information import APIResponse, MeetingInput
from src.services.v1.group_information import build_meeting_data
from fastapi.responses import JSONResponse
from src.core.moderation import get_harmfulness_scores_korean, is_request_valid
from src.core.logging_config import logger

REJECTION_REASONS = {
    "TOXICITY": "전체적으로 공격적인 표현이 감지되었습니다.",
    "INSULT": "모욕적인 표현이 포함되어 있습니다.",
    "THREAT": "위협적인 내용이 포함되어 있습니다.",
    "IDENTITY_ATTACK": "특정 집단이나 정체성을 공격하는 표현이 포함되어 있습니다."
}
router = APIRouter()

@router.post("/groups/information")
def create_meeting(meeting: MeetingInput):
    logger.info("[POST /groups/information] 모임 정보 생성 요청 수신", extra={"meeting_name": meeting.name})
    input_text = f"{meeting.name}\n{meeting.goal}"

    try:
        scores = get_harmfulness_scores_korean(input_text)
        logger.info("[유해성 분석] 분석 결과 수신", extra={"scores": scores})
    except Exception:
        logger.exception("[유해성 분석] 분석 중 예외 발생")
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

        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "모임 생성이 거부되었습니다.",
                "data": reason_msg
            }
        )

    try:
        meeting_data = build_meeting_data(meeting)
        logger.info("[모임 생성] 모임 정보 생성 성공")
    except Exception:
        logger.exception("[모임 생성] 모임 정보 생성 중 예외 발생")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "모임 정보 생성 중 오류가 발생했습니다.",
                "data": None
            }
        )

    response = APIResponse(
        code=200,
        message="모임 정보 생성 완료",
        data=meeting_data
    )

    return JSONResponse(
        status_code=200,
        content=response.model_dump(exclude_none=True)
    )