from fastapi import APIRouter, Request, Header, HTTPException
from src.schemas.v2.chatbot import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    UnifiedChatAnswerRequest,
    RecommendationResponse
)
from src.services.v2.chatbot import (
    handle_combined_question,
    handle_answer_analysis
)

router = APIRouter(prefix="/groups/recommendations", tags=["Chatbot"])


@router.post("/questions", response_model=QuestionGenerationResponse)
async def generate_question(
    req: QuestionGenerationRequest,
    x_session_id: str = Header(...)
):
    try:
        result = await handle_combined_question(
            answer=req.answer,
            user_id=str(req.userId),
            session_id=x_session_id
        )

        return {
            "code": 200,
            "message": "질문 생성 완료",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질문 생성 실패: {str(e)}")


@router.post("", response_model=RecommendationResponse)
def recommend_group(
    req: UnifiedChatAnswerRequest,
    x_session_id: str = Header(...)
):
    try:
        result = handle_answer_analysis(
            messages=[m.dict() for m in req.messages],
            user_id=str(req.userId),
            session_id=x_session_id
        )

        return {
            "code": 200,
            "message": "추천 결과 생성 완료",
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 실패: {str(e)}")
