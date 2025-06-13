from fastapi import APIRouter, HTTPException
from src.schemas.v2.chatbot import (
    FreeFormRequest,
    MCQQuestionRequest,
    MCQAnswerRequest
)
from src.services.v2.chatbot_freeform import handle_freeform_chatbot
from src.services.v2.chatbot_mcq import (
    handle_mcq_question_generation,
    handle_mcq_answer_processing
)

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post("/freeform", response_model=dict)
def freeform_chatbot_api(req: FreeFormRequest):
    try:
        result = handle_freeform_chatbot(req.query, req.user_id)
        # if not result.get("context"):  # ✅ 결과 없음 처리
        #     raise HTTPException(status_code=502, detail="모델이 유효한 응답을 생성하지 못했습니다.")
        return {
            "code": 200,
            "message": "챗봇 응답 생성 완료",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자유형 응답 생성 실패: {str(e)}")


@router.post("/questions", response_model=dict)
def mcq_question_api(req: MCQQuestionRequest):
    try:
        result = handle_mcq_question_generation(req.user_id)
        questions = result.get("questions", [])
        # if not isinstance(questions, list) or not questions:  # ✅ 결과 없음 처리
        #     raise HTTPException(status_code=502, detail="모델이 질문 생성을 실패했습니다.")
        return {
            "code": 200,
            "message": "챗봇 질문 생성 완료",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질문 생성 실패: {str(e)}")


@router.post("/answers", response_model=dict)
def mcq_answer_api(req: MCQAnswerRequest):
    try:
        result = handle_mcq_answer_processing(req.user_id, req.answers)
        # if not result.get("context"):  # ✅ 결과 없음 처리
        #     raise HTTPException(status_code=502, detail="모델이 추천 사유 생성을 실패했습니다.")
        return {
            "code": 200,
            "message": "모임 추천 완료",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 분석 실패: {str(e)}")
