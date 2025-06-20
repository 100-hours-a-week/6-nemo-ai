from fastapi import APIRouter, Body, Header, Response
from src.schemas.v2.chatbot import (
    ChatQuestionRequest,
    QuestionResponse,
    QuestionItem,
    ChatAnswerRequest,
    RecommendationResponse,
    RecommendationItem,
)
from src.services.v2.chatbot import (
    handle_combined_question,
    handle_answer_analysis,
)
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

router = APIRouter(prefix="/groups/recommendations", tags=["Chatbot"])

@router.post("/questions", response_model=QuestionResponse)
async def generate_question_route(
    payload: ChatQuestionRequest = Body(...),
    session_id: str = Header(..., alias="x-session-id"),
    response: Response = None
):
    ai_logger.info("[질문 생성 요청 수신]", extra={
        "user_id": payload.userId,
        "session_id": session_id,
        "answer": payload.answer
    })

    result = await handle_combined_question(
        answer=payload.answer,
        user_id=str(payload.userId),
        session_id=session_id,
    )

    response.headers["x-session-id"] = session_id

    return QuestionResponse(
        code=200,
        message="요청이 성공적으로 처리되었습니다.",
        data=QuestionItem(
            question=result["question"],
            options=result["options"],  # 필드 이름만 변경된 구조
        ),
    )


@router.post("", response_model=RecommendationResponse)
async def generate_recommendation_route(
    payload: ChatAnswerRequest = Body(...),
    session_id: str = Header(..., alias="x-session-id"),
    response: Response = None
):
    ai_logger.info("[추천 요청 수신]", extra={
        "user_id": payload.userId,
        "session_id": session_id,
        "messages": [m.text for m in payload.messages]
    })

    result = await handle_answer_analysis(
        messages=[m.dict() for m in payload.messages],
        user_id=str(payload.userId),
        session_id=session_id,
    )

    response.headers["x-session-id"] = session_id

    return RecommendationResponse(
        code=200,
        message="요청이 성공적으로 처리되었습니다.",
        data=RecommendationItem(
            groupId=result["groupId"],
            reason=result["reason"],
        ),
    )