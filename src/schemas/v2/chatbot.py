from pydantic import BaseModel
from typing import List


#자유형 챗봇
class FreeFormRequest(BaseModel):
    query: str
    user_id: str

class FreeFormResponse(BaseModel):
    context: str
    groupId: List[str]

#MCQ 질문 요청 (질문 생성)
class MCQQuestionRequest(BaseModel):
    user_id: str

class MCQQuestion(BaseModel):
    question: str
    options: List[str]  # 선택지 리스트

#MCQ 답변 요청 (질문 응답 → 추천)
class MCQAnswer(BaseModel):
    question: str
    selected_option: str

class MCQAnswerRequest(BaseModel):
    user_id: str
    answers: List[MCQAnswer]
