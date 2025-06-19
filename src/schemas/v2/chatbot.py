from pydantic import BaseModel
from typing import List, Literal, Optional

class MessageItem(BaseModel):
    role: Literal["user", "ai"]
    text: str


class QuestionGenerationRequest(BaseModel):
    userId: int
    answer: Optional[str] = None  # null 가능 (첫 질문일 경우)


class QuestionGenerationResponseItem(BaseModel):
    question: str
    options: List[str]


class QuestionGenerationResponse(BaseModel):
    code: int
    message: str
    data: QuestionGenerationResponseItem


class UnifiedChatAnswerRequest(BaseModel):
    userId: int
    messages: List[MessageItem]


class RecommendationItem(BaseModel):
    groupId: int
    reason: str


class RecommendationResponse(BaseModel):
    code: int
    message: str
    data: RecommendationItem
