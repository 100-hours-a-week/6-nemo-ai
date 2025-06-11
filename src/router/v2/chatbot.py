from fastapi import APIRouter, HTTPException
from src.schemas.v2.chatbot import (
    FreeFormRequest,
    FreeFormResponse,
    MCQQuestionRequest,
    MCQQuestionResponse,
    MCQAnswerRequest
)
from src.services.v2.chatbot_freeform import handle_freeform_chatbot
from src.services.v2.chatbot_mcq import (
    handle_mcq_question_generation,
    handle_mcq_answer_processing
)

router = APIRouter(prefix="/groups/recommendations", tags=["Chatbot"])


@router.post("/freeform", response_model=FreeFormResponse)
def freeform_chatbot_api(req: FreeFormRequest):
    try:
        result = handle_freeform_chatbot(req.recommendationText, str(req.userId))
        # if not result.get("context"):  # ✅ 결과 없음 처리
        #     raise HTTPException(status_code=502, detail="모델이 유효한 응답을 생성하지 못했습니다.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자유형 응답 생성 실패: {str(e)}")


@router.post("/questions", response_model=MCQQuestionResponse)
def mcq_question_api(req: MCQQuestionRequest):
    try:
        result = handle_mcq_question_generation(str(req.userId), session_id=req.sessionId, step=req.step, previous_answers=req.previousAnswers)
        # if not result.get("context"):  # ✅ 결과 없음 처리
        #     raise HTTPException(status_code=502, detail="모델이 유효한 응답을 생성하지 못했습니다.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질문 생성 실패: {str(e)}")


@router.post("", response_model=FreeFormResponse)
def mcq_answer_api(req: MCQAnswerRequest):
    try:
        result = handle_mcq_answer_processing(str(req.userId), req.answers, session_id=req.sessionId)
        # if not result.get("context"):  # ✅ 결과 없음 처리
        #     raise HTTPException(status_code=502, detail="모델이 추천 사유 생성을 실패했습니다.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 분석 실패: {str(e)}")
