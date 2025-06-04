from fastapi import APIRouter
from src.schemas.v2.chatbot import FreeFormRequest, FreeFormResponse
from src.services.v2.chatbot_freeform import handle_freeform_chatbot

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

@router.post("/freeform", response_model=dict)
def freeform_chatbot_api(req: FreeFormRequest):
    result = handle_freeform_chatbot(req.query, req.user_id)
    return {
        "code": 200,
        "message": "챗봇 응답 생성 완료",
        "data": result
    }