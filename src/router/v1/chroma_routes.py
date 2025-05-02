from fastapi import APIRouter
from src.core.vector_db_settings_v1 import add_to_chroma, search_chroma
from pydantic import BaseModel
router = APIRouter()
class Document(BaseModel):
    id: str
    text: str
@router.get("/")
def root():
    return {"message": "Hello World: Currently setting up Chroma!"}
@router.post("/add/")
def add_document(doc: Document):
    add_to_chroma(doc.id, doc.text)
    return {"status": "added", "id": doc.id}
@router.post("/add-batch/")
def add_batch(docs: list[Document]):
    for doc in docs:
        add_to_chroma(doc.id, doc.text)
    return {"added": len(docs)}
@router.get("/search/")
def search_document(query: str):
    return search_chroma(query)
