from fastapi import APIRouter, Body, Query, HTTPException, BackgroundTasks
from typing import Literal, Optional

from src.vector_db.group_document_builder import build_group_document
from src.vector_db.user_document_builder import build_user_document
from src.vector_db.synthetic_document_builder import build_synthetic_documents
from src.vector_db.vector_indexer import add_documents_to_vector_db
from src.vector_db.chroma_client import get_chroma_client
from src.vector_db.hybrid_search import hybrid_group_search

from src.schemas.v2.group_data import GroupSaveRequest, GroupDeleteRequest
from src.schemas.v2.user_data import UserParticipationRequest, UserRemoveRequest


router = APIRouter(prefix="/groups", tags=["Vector DB"])


@router.post("")
async def save_group_to_chroma_route(payload: GroupSaveRequest, background_tasks: BackgroundTasks):
    try:
        doc = build_group_document(payload.dict())
        add_documents_to_vector_db([doc], collection="group-info")

        async def generate_and_save(data: dict):
            docs = await build_synthetic_documents(data)
            add_documents_to_vector_db(docs, collection="group-synthetic")

        background_tasks.add_task(generate_and_save, payload.dict())

        return {
            "code": 200,
            "message": "모임 정보 저장 완료",
            "data": None
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthetic")
async def generate_synthetic_documents_route(payload: GroupSaveRequest, count: int = Query(3)):
    try:
        docs = await build_synthetic_documents(payload.dict(), num_docs=count)
        add_documents_to_vector_db(docs, collection="group-synthetic")
        return {"code": 200, "message": "synthetic documents saved", "data": None}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/participants")
def add_user_document(payload: UserParticipationRequest):
    try:
        user_id = payload.userId
        group_id = payload.groupId

        docs = build_user_document(user_id, group_id)
        add_documents_to_vector_db(docs, collection="user-activity")

        return {
            "code": 200,
            "message": "유저 벡터 삽입 성공",
            "data": None
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete")
def delete_group_from_chroma_route(payload: GroupDeleteRequest):
    try:
        group_id = payload.groupId

        client = get_chroma_client()
        col = client.get_or_create_collection("group-info")
        col.delete(ids=[f"group-{group_id}"])

        return {
            "code": 200,
            "message": "모임 정보 삭제 완료",
            "data": None
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/participants/delete")
def remove_user_from_chroma_route(payload: UserRemoveRequest):
    try:
        user_id = payload.userId
        group_id = payload.groupId

        ids = [f"user-{user_id}-{group_id}"]

        client = get_chroma_client()
        col = client.get_or_create_collection("user-activity")
        col.delete(ids=ids)

        return {
            "code": 200,
            "message": "사용자 정보 삭제 완료",
            "data": None
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/hybrid")
def hybrid_search_route(query: str = Query(...), top_k: int = 5, userId: Optional[str] = None):
    try:
        results = hybrid_group_search(query, top_k=top_k, user_id=userId)
        return {"code": 200, "message": "검색 성공", "data": results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collection")
def list_collection_items(
        collection: Literal["group-info", "user-activity", "group-synthetic"] = Query(...),
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
        collection: Literal["group-info", "user-activity", "group-synthetic"] = Query(..., description="조회할 컬렉션 이름"),
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
