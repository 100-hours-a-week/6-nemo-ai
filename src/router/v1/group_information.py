from fastapi import APIRouter, HTTPException
from src.schemas.v1.group_information import APIResponse, MeetingInput
from src.services.v1.group_information import build_meeting_data
from fastapi.responses import JSONResponse
from src.core.moderation import get_harmfulness_scores_korean, is_request_valid

router = APIRouter()

@router.post("/groups/information")
def create_meeting(meeting: MeetingInput):
    # 1. 입력 텍스트 구성 (검열 대상 필드만 선택적으로 포함)
    input_text = f"{meeting.name}\n{meeting.goal}"

    # 2. Perspective API 검사
    scores = get_harmfulness_scores_korean(input_text)

    # 3. 유해성 기준 초과 시 생성 거부
    if not is_request_valid(scores):
        raise HTTPException(
            status_code=422,
            detail="모임 생성이 거부되었습니다. 입력 내용에 유해한 표현이 포함되어 있습니다."
        )

    # 4. 유효할 경우 모임 데이터 생성
    meeting_data = build_meeting_data(meeting)

    # 5. 응답 구성
    response = APIResponse(
        code=200,
        message="모임 정보 생성 완료",
        data=meeting_data
    )

    return JSONResponse(
        status_code=200,
        content=response.model_dump(exclude_none=True)
    )