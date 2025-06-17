from pydantic import BaseModel
from typing import List

class UserParticipationRequest(BaseModel):
    userId: int
    groupId: int

class UserParticipationResponse(BaseModel):
    code: int
    message: str
    data: UserParticipationRequest

class UserRemoveRequest(BaseModel):
    userId: int
    groupId: int

