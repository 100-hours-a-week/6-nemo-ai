from pydantic import BaseModel
from typing import List

class UserParticipationData(BaseModel):
    user_id: str
    group_id: List[str]

class UserParticipationResponse(BaseModel):
    code: int
    message: str
    data: UserParticipationData
