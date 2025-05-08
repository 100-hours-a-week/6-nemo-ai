from pydantic import BaseModel, field_validator
from typing import List, Optional
import re

# 사용자 요청 스키마
class MeetingInput(BaseModel):
    name: str
    goal: str
    category: str
    period: str
    isPlanCreated: bool

    @field_validator('name', 'goal', 'category', mode='before')
    @classmethod
    def must_be_meaningful(cls, value: str, info):
        cleaned = value.strip()

        if len(cleaned) < 2:
            raise ValueError(f"{info.field_name}은 너무 짧습니다.")

        if re.fullmatch(r"[^\w가-힣]+", cleaned):
            raise ValueError(f"{info.field_name}에 유효하지 않은 내용이 포함되어 있습니다.")

        if re.fullmatch(r"\d+", cleaned):
            raise ValueError(f"{info.field_name}에 숫자만 입력할 수 없습니다.")

        return value

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
