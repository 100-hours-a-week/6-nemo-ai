"""
스키마 메인 모듈
모든 도메인별 스키마들을 중앙에서 관리합니다.
"""

# Groups domain schemas
from .groups import (
    GroupSaveRequest,
    GroupDeleteRequest,
    GroupResponse,
    GroupPartialUpdate,
    GroupGenerationRequest,
    GroupDescriptionResponse,
    GroupPlanResponse,
    MeetingInput,
    MeetingData,
    APIResponse,
)

# Chatbot domain schemas  
from .chatbot import (
    MessageItem,
    ChatQuestionRequest,
    QuestionItem,
    QuestionResponse,
    ChatAnswerRequest,
    RecommendationItem,
    RecommendationResponse,
    StreamChunk,
    StreamComplete,
    StreamError,
)

# Vector domain schemas
from .vectors import (
    Document,
)

# Tags domain schemas
from .tags import (
    TagRequest,
    TagResponse,
)

# Users domain schemas
from .users import (
    UserParticipationRequest,
    UserParticipationResponse,
    UserRemoveRequest,
)

# Events domain schemas
from .events import (
    GroupEventData,
    UserEventData,
    GroupEvent,
    GroupGenerateRequest,
    QuestionRequest,
    RecommendRequest,
    DLQMessage,
)

__all__ = [
    # Groups schemas
    "GroupSaveRequest",
    "GroupDeleteRequest",
    "GroupResponse", 
    "GroupPartialUpdate",
    "GroupGenerationRequest",
    "GroupDescriptionResponse",
    "GroupPlanResponse",
    "MeetingInput",
    "MeetingData",
    "APIResponse",
    
    # Chatbot schemas
    "MessageItem",
    "ChatQuestionRequest",
    "QuestionItem",
    "QuestionResponse", 
    "ChatAnswerRequest",
    "RecommendationItem",
    "RecommendationResponse",
    "StreamChunk",
    "StreamComplete",
    "StreamError",
    
    # Vector schemas
    "Document",
    
    # Tags schemas
    "TagRequest",
    "TagResponse",
    
    # Users schemas
    "UserParticipationRequest",
    "UserParticipationResponse",
    "UserRemoveRequest",
    
    # Events schemas
    "GroupEventData",
    "UserEventData",
    "GroupEvent",
    "GroupGenerateRequest",
    "QuestionRequest", 
    "RecommendRequest",
    "DLQMessage",
]
