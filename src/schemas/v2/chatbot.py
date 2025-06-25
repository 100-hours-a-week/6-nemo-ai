from pydantic import BaseModel
from typing import List, Literal, Optional


class MessageItem(BaseModel):
    role: Literal["USER", "AI"]
    text: str


# 질문 생성 요청
class ChatQuestionRequest(BaseModel):
    userId: int
    answer: Optional[str] = None  # 첫 질문이면 null 가능


# 질문 생성 응답
class QuestionItem(BaseModel):
    question: str
    options: List[str]  # 기존: options → answer 로 맞춤

class QuestionResponse(BaseModel):
    code: int
    message: str
    data: QuestionItem


# 답변 후 추천 요청
class ChatAnswerRequest(BaseModel):
    userId: int
    messages: List[MessageItem]


# 추천 응답
class RecommendationItem(BaseModel):
    groupId: int
    reason: str

class RecommendationResponse(BaseModel):
    code: int
    message: str
    data: RecommendationItem
