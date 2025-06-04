from pydantic import BaseModel
from typing import List

class FreeFormRequest(BaseModel):
    query: str
    user_id: str

class FreeFormResponse(BaseModel):
    context: str
    groupId: List[str]
