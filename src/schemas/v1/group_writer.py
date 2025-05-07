from pydantic import BaseModel

class GroupGenerationRequest(BaseModel):
    name: str
    goal: str
    category: str
    period: str
    isPlanCreated: bool