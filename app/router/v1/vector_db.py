from fastapi import APIRouter
from app.database.vector_indexer import add_documents_to_vector_db
from app.database.vector_searcher import search_similar_documents
from app.database.chroma_client import get_chroma_client
from app.schemas.vectors.vector_db import Document
from app.models.embedding_model import embed

router = APIRouter()

@router.post("/add/")
def add_document(doc: Document):
    docs = [{
        "id": doc.id,
        "text": doc.text,
        "metadata": {"document_id": doc.id}
    }]
    add_documents_to_vector_db(docs, collection="group-info")
    return {"status": "added", "id": doc.id}

@router.post("/add-batch/")
def add_batch(docs: list[Document]):
    doc_list = [{
        "id": doc.id,
        "text": doc.text,
        "metadata": {"document_id": doc.id}
    } for doc in docs]
    add_documents_to_vector_db(doc_list, collection="group-info")
    return {"added": len(docs)}

@router.get("/search/")
def search_document(query: str):
    results = search_similar_documents(query, top_k=5, collection="group-info")
    return {
        "query": query,
        "results": [
            {
                "id": r["id"],
                "text": r["text"],
                "metadata": r["metadata"],
                "score": r["score"]
            }
            for r in results
        ]
    }

@router.post("/debug/show-db")
def show_all_documents():
    client = get_chroma_client()
    collection = client.get_or_create_collection(name="group-info", embedding_function=embed)
    result = collection.get(include=["documents", "metadatas"])
    docs = []
    for doc_id, doc_text in zip(result["ids"], result["documents"]):
        docs.append({
            "id": doc_id,
            "text": doc_text
        })
    return {"total": len(docs), "documents": docs}
