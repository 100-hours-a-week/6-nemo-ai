from pydantic import BaseModel
from typing import List, Optional

class GroupSaveRequest(BaseModel):
    groupId: int
    name: str
    summary: Optional[str] = ""
    description: Optional[str] = ""
    category: Optional[str] = ""
    location: Optional[str] = ""
    currentUserCount: Optional[int] = ""
    maxUserCount: Optional[int] = ""
    imageUrl: Optional[str] = ""
    tags: Optional[List[str]] = []
    plan: Optional[str] = ""

class GroupDeleteRequest(BaseModel):
    groupId: int

class GroupResponse(BaseModel):
    code: int
    message: str
    data: GroupSaveRequest

class GroupPartialUpdate(BaseModel):
    groupId: Optional[int] = None
    name: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    currentUserCount: Optional[int] = None
    maxUserCount: Optional[int] = None
    imageUrl: Optional[str] = None
    tags: Optional[List[str]] = None
    plan: Optional[str] = None

    class Config:
        extra = "allow"