from fastapi import APIRouter
from src.schemas.v1.group_information import APIResponse, MeetingInput
from src.services.v1.group_information import build_meeting_data
router = APIRouter()

@router.post("/groups/information", response_model=APIResponse)
async def create_meeting(meeting: MeetingInput):
    meeting_data = await build_meeting_data(meeting)

    return {
        "code": 200,
        "message": "모임 정보 생성 완료",
        "data": meeting_data
    }
