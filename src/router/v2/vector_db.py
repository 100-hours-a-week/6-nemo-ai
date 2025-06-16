from fastapi import APIRouter, Body, Query, HTTPException
from typing import Literal, Optional

from src.vector_db.group_document_builder import build_group_document
from src.vector_db.user_document_builder import build_user_document
from src.vector_db.vector_indexer import add_documents_to_vector_db
from src.vector_db.chroma_client import get_chroma_client

router = APIRouter(prefix="/groups", tags=["Vector DB"])

@router.post("/")
def add_group_document(payload: dict = Body(...)):
    try:
        doc = build_group_document(payload)
        add_documents_to_vector_db([doc], collection="group-info")
        return {
            "code": 200,
            "message": "그룹 벡터 삽입 성공",
            "data": {
                "id": doc["id"]
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/participants")
def add_user_document(payload: dict = Body(...)):
    try:
        user_id = payload.get("user_id")
        group_ids = payload.get("group_id")

        if not user_id or not group_ids:
            raise HTTPException(status_code=400, detail="user_id와 group_id는 필수입니다.")

        docs = build_user_document(user_id, group_ids)  # <- 두 인자 전달
        add_documents_to_vector_db(docs, collection="user-activity")

        return {
            "code": 200,
            "message": "유저 벡터 삽입 성공",
            "data": {
                "count": len(docs),
                "user_id": user_id
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collection")
def list_collection_items(
    collection: Literal["group-info", "user-activity"] = Query(...),
    limit: int = 10,
    offset: int = 0
):
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=collection)
        results = col.get(include=["documents", "metadatas"])

        total = len(results.get("documents", []))

        items = []
        for i in range(offset, min(offset + limit, total)):
            try:
                items.append({
                    "id": f"{collection}-{i}",
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
            except (IndexError, KeyError, TypeError):
                continue  # 이상한 항목은 무시

        return {
            "code": 200,
            "message": "조회 성공",
            "data": {
                "total": total,
                "items": items
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()  # 콘솔에 전체 오류 출력
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/document")
def get_single_document(
    collection: Literal["group-info", "user-activity"] = Query(..., description="조회할 컬렉션 이름"),
    id: str = Query(..., description="조회할 문서 ID")
):
    client = get_chroma_client()
    col = client.get_or_create_collection(name=collection)

    try:
        result = col.get(ids=[id], include=["documents", "metadatas"])
        if not result["documents"]:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "id": id,
            "text": result["documents"][0],
            "metadata": result["metadatas"][0]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
