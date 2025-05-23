from fastapi import APIRouter, Body, Query, HTTPException
from typing import Literal, Optional

from src.vector_db.group_document_builder import build_group_document
from src.vector_db.user_document_builder import build_user_document
from src.vector_db.vector_indexer import add_documents_to_vector_db
from src.vector_db.chroma_client import get_chroma_client

router = APIRouter(prefix="/vector", tags=["Vector DB"])

@router.post("/group")
def add_group_document(payload: dict = Body(...)):
    doc = build_group_document(payload)
    add_documents_to_vector_db([doc], collection="group-info")
    return {"status": "ok", "id": doc["id"]}

@router.post("/user")
def add_user_document(payload: dict = Body(...)):
    doc = build_user_document(payload)
    add_documents_to_vector_db([doc], collection="user-activity")
    return {"status": "ok", "id": doc["id"]}

@router.get("/collection")
def list_collection_items(
    collection: Literal["group-info", "user-activity"],
    limit: int = 10,
    offset: int = 0
):
    client = get_chroma_client()
    col = client.get_or_create_collection(name=collection)
    results = col.get(include=["documents", "metadatas", "ids"])
    total = len(results["ids"])
    return {
        "total": total,
        "items": [
            {
                "id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i],
            }
            for i in range(offset, min(offset + limit, total))
        ]
    }

@router.get("/document")
def get_single_document(
    collection: Literal["group-info", "user-activity"],
    id: str = Query(...)
):
    client = get_chroma_client()
    col = client.get_or_create_collection(name=collection)

    try:
        result = col.get(ids=[id], include=["documents", "metadatas", "ids"])
        return {
            "id": result["ids"][0],
            "text": result["documents"][0],
            "metadata": result["metadatas"][0]
        }
    except IndexError:
        raise HTTPException(status_code=404, detail="Document not found")