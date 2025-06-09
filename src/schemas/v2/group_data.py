from pydantic import BaseModel
from typing import List, Optional

class GroupData(BaseModel):
    groupId: int
    name: str
    summary: Optional[str] = ""
    description: Optional[str] = ""
    category: Optional[str] = ""
    location: Optional[str] = ""
    maxUserCount: Optional[str] = ""
    imageUrl: Optional[str] = ""
    tags: Optional[List[str]] = []
    plan: Optional[str] = ""

class GroupResponse(BaseModel):
    code: int
    message: str
    data: GroupData

class GroupPartialUpdate(BaseModel):
    groupId: Optional[int] = None
    name: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    maxUserCount: Optional[str] = None
    imageUrl: Optional[str] = None
    tags: Optional[List[str]] = None
    plan: Optional[str] = None

    class Config:
        extra = "allow"