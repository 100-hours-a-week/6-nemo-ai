from pydantic import BaseModel
from typing import List, Optional, Literal

#자유형 챗봇
class FreeFormRequest(BaseModel):
    userId: int
    requestText: str

class RecommendationItem(BaseModel):
    groupId: int
    reason: str

#MCQ 질문 요청 (질문 생성)
class MCQQuestionRequest(BaseModel):
    userId: int
    answer: Optional[str] = None

class MCQQuestionItem(BaseModel):
    question: str
    options: List[str]

class MCQQuestionResponse(BaseModel):
    code: int
    message: str
    data: MCQQuestionItem

#MCQ 답변 요청 (질문 응답 → 추천)
class MessageItem(BaseModel):
    role: Literal["user", "ai"]
    text: str

class MCQAnswerRequest(BaseModel):
    messages: List[MessageItem]


#추천 답변
class RecommendationResponse(BaseModel):
    code: int
    message: str
    data: RecommendationItem