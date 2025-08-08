from pydantic import BaseModel
from typing import Literal


class StreamChunk(BaseModel):
    type: Literal["stream_chunk"]
    data: str


class StreamComplete(BaseModel):
    type: Literal["complete"]
    data: dict  # {"message": "..."} 또는 {"question": "...", "options": [...]}


class StreamError(BaseModel):
    type: Literal["error"]
    data: str
