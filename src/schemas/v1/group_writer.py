from pydantic import BaseModel

class GroupGenerationRequest(BaseModel):
    name: str
    goal: str
    category: str
    period: str
    isPlanCreated: bool

class GroupDescriptionResponse(BaseModel):
    summary: str
    description: str

class GroupPlanResponse(BaseModel):
    plan: str
