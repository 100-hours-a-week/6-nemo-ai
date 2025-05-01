from fastapi import APIRouter
from src.core.vector_db_settings_v1 import add_to_chroma, search_chroma

router = APIRouter()

@router.post("/add/")
def add_document(id: str, text: str):
    add_to_chroma(id, text)
    return {"status": "added", "id": id}

@router.get("/search/")
def search_document(query: str):
    return search_chroma(query)
