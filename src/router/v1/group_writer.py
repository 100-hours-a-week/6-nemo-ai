from fastapi import APIRouter
from src.schemas.v1.group_writer import GroupGenerationRequest, GroupGenerationResponse
from src.services.v1.group_writer import generate_group_info

router = APIRouter()

@router.post("/groups", response_model=GroupGenerationResponse)
async def create_group(data: GroupGenerationRequest):
    result = await generate_group_info(data)
    return result
