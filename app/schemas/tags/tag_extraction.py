from pydantic import BaseModel

class TagRequest(BaseModel):
    text: str

class TagResponse(BaseModel):
    tags: list[str]
