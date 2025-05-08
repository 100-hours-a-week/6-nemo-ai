from fastapi import APIRouter, HTTPException
from src.schemas.v1.group_information import APIResponse, MeetingInput
from src.services.v1.group_information import build_meeting_data
from src.core.moderation import get_harmfulness_scores_korean, is_request_valid

REJECTION_REASONS = {
    "TOXICITY": "전체적으로 공격적인 표현이 감지되었습니다.",
    "INSULT": "모욕적인 표현이 포함되어 있습니다.",
    "THREAT": "위협적인 내용이 포함되어 있습니다.",
    "IDENTITY_ATTACK": "특정 집단이나 정체성을 공격하는 표현이 포함되어 있습니다."
}
router = APIRouter()

@router.post("/groups/information", response_model=APIResponse)
def create_meeting(meeting: MeetingInput):
    input_text = f"{meeting.name}\n{meeting.goal}"

    scores = get_harmfulness_scores_korean(input_text)

    if not is_request_valid(scores):
        max_attr, _ = max(scores.items(), key=lambda x: x[1])
        reason_msg = REJECTION_REASONS.get(max_attr, "부적절한 표현이 포함되어 있습니다.")

        raise HTTPException(status_code=422, detail=reason_msg)

    meeting_data = build_meeting_data(meeting)

    return APIResponse(
        code=200,
        message="모임 정보 생성 완료",
        data=meeting_data
    )