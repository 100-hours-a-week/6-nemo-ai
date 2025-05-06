from fastapi import APIRouter
from src.schemas.v1.group_information import APIResponse, MeetingInput
from src.services.v1.group_information import build_meeting_data
from fastapi.responses import JSONResponse
router = APIRouter()

@router.post("/groups/information")
async def create_meeting(meeting: MeetingInput):
    meeting_data = await build_meeting_data(meeting)

    response = APIResponse(
        code=200,
        message="모임 정보 생성 완료",
        data=meeting_data
    )

    return JSONResponse(
        status_code=200,
        content=response.model_dump(exclude_none=True)
    )

