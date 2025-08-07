from pydantic import BaseModel
from typing import List, Optional, Literal, Union

class GroupEventData(BaseModel):
    groupId: int
    name: str
    category: str
    summary: str
    description: str
    plan: str
    location: str
    currentUserCount: int
    maxUserCount: int
    imageUrl: str
    tags: List[str]

class UserEventData(BaseModel):
    userId: int
    groupId: int

class GroupEvent(BaseModel):
    eventType: Literal["GROUP_CREATED", "GROUP_DELETED", "GROUP_JOINED", "GROUP_LEFT"]
    data: Optional[Union[GroupEventData, UserEventData]] = None
    groupId: Optional[int] = None  # For simple events like GROUP_DELETED
    timestamp: List[int]  # [year, month, day, hour, minute, second, nanosecond]

class GroupGenerateRequest(BaseModel):
    name: str
    goal: str
    category: str
    location: str
    period: str
    maxUserCount: int
    isPlanCreated: bool

class QuestionRequest(BaseModel):
    type: Literal["CREATE_QUESTION"]
    payload: dict

class RecommendRequest(BaseModel):
    type: Literal["RECOMMEND_REQUEST"]
    payload: dict

# DLQ Message Schema
class DLQMessage(BaseModel):
    originalMessage: dict
    errorType: str
    errorMessage: str
    failedAt: str
    source: Optional[str] = "AI-RECOMMENDER"
