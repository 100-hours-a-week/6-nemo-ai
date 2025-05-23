from pydantic import BaseModel

class UserParticipationData(BaseModel):
    user_id: str
    group_id: str

class UserParticipationResponse(BaseModel):
    code: int
    message: str
    data: UserParticipationData
