from pydantic import BaseModel
from typing import Optional, List

class GroupGenerationRequest(BaseModel):
    group_name: str
    purpose: str
    category: str
    duration: str
    curriculum_required: bool

class GroupGenerationResponse(BaseModel):
    one_line_intro: str
    detailed_intro: str
    curriculum: Optional[List[str]] = None
