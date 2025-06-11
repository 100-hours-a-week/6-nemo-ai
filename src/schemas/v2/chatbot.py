from pydantic import BaseModel
from typing import List, Optional


#자유형 챗봇
class FreeFormRequest(BaseModel):
    userId: int
    recommendationText: str

class RecommendationItem(BaseModel):
    groupId: int
    context: str

class FreeFormResponse(BaseModel):
    recommendations: List[RecommendationItem]

#MCQ 질문 요청 (질문 생성)
class MCQQuestionRequest(BaseModel):
    sessionId: str
    userId: int
    step: int
    previousAnswers: List[str]

class MCQQuestionResponse(BaseModel):
    sessionId: str
    question: str
    options: List[str]

#MCQ 답변 요청 (질문 응답 → 추천)
class MCQAnswer(BaseModel):
    question: str
    selected_option: str

class MCQAnswerRequest(BaseModel):
    sessionId: str
    userId: int
    answers: List[MCQAnswer]
