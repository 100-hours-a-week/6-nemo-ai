# src/models/group.py

from pydantic import BaseModel
from typing import List, Optional

class GroupGenerationRequest(BaseModel):
    name: str
    goal: str
    category: str
    period: str
    isPlanCreated: bool

class GroupGenerationResponse(BaseModel):
    summary: str
    description: str
    tags: List[str]
    plan: Optional[List[str]] = None

