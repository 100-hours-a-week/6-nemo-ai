from pydantic import BaseModel
from typing import List

class UserParticipationRequest(BaseModel):
    userId: str
    groupId: str

class UserParticipationResponse(BaseModel):
    code: int
    message: str
    data: UserParticipationRequest

class UserRemoveRequest(BaseModel):
    userId: str
    groupId: str
