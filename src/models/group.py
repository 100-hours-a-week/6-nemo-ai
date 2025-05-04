from pydantic import BaseModel
from typing import Optional, List

# 요청 모델: 사용자가 보내는 모임 정보
class GroupGenerationRequest(BaseModel):
    name: str
    goal: str
    category: str
    period: str
    isPlanCreated: bool

# 응답 모델: AI가 생성한 결과
class GroupGenerationResponse(BaseModel):
    summary: str
    description: str
    plan: Optional[List[str]] = None
