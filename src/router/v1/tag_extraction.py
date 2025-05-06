from fastapi import APIRouter
from src.services.v1.tag_extraction import extract_tags, pick_best_by_vector_similarity
from src.services.v1.vector_db import embed
from src.schemas.v1.tag_extraction import TagRequest, TagResponse
router = APIRouter()

@router.post("/tag/extract", response_model=TagResponse)
async def extract_keyword(payload: TagRequest):
    extracted = await extract_tags(payload.text)
    tags = pick_best_by_vector_similarity(extracted, base_text=payload.text, embed_fn=embed)
    return {"tags": tags}
