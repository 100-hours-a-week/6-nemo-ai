"""
Chatbot 스키마 모듈
채팅봇 관련 데이터 모델들을 정의합니다.
"""

from .chatbot import (
    MessageItem,
    ChatQuestionRequest,
    QuestionItem,
    QuestionResponse,
    ChatAnswerRequest,
    RecommendationItem,
    RecommendationResponse
)
from .ws_chatbot import (
    StreamChunk,
    StreamComplete,
    StreamError
)

__all__ = [
    # HTTP Chatbot Schemas
    "MessageItem",
    "ChatQuestionRequest",
    "QuestionItem", 
    "QuestionResponse",
    "ChatAnswerRequest",
    "RecommendationItem",
    "RecommendationResponse",
    # WebSocket Chatbot Schemas
    "StreamChunk",
    "StreamComplete",
    "StreamError",
]
