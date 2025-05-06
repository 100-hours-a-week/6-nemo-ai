from fastapi import APIRouter
from src.services.vector_db_settings_v1 import add_to_chroma, search_chroma, collection
from src.models.chroma_db import Document
router = APIRouter()

@router.get("/")
def root():
    return {"message": "Hello World: Currently setting up"}
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

@router.post("/debug/show-db")
def show_all_documents():
    result = collection.get(include=["documents", "metadatas"])
    docs = []
    for doc_id, doc_text in zip(result["ids"], result["documents"]):
        docs.append({
            "id": doc_id,
            "text": doc_text
        })
    return {"total": len(docs), "documents": docs}
