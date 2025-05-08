from pydantic import BaseModel
from typing import List, Optional
import re

# 사용자 요청 스키마
class MeetingInput(BaseModel):
    name: str
    goal: str
    category: str
    period: str
    isPlanCreated: bool

# 내부 생성된 최종 모임 정보
class MeetingData(BaseModel):
    name: str
    summary: str
    description: str
    tags: List[str]
    plan: Optional[str] = None

    model_config = {
        "exclude_none": True
    }


# 공통 응답 래퍼
class APIResponse(BaseModel):
    code: int
    message: str
    data: MeetingData
