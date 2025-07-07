from __future__ import annotations
from typing import Dict, Any, List
import json, re

from src.models.gemma_3_4b import call_vllm_api

async def build_synthetic_documents(group: Dict[str, Any], num_docs: int = 3) -> List[dict]:
    """Generate synthetic review-style documents for a group."""
    group_id = str(group.get("groupId"))
    if not group_id:
        raise ValueError("invalid groupId")

    name = group.get("name", "")
    summary = group.get("summary", "")
    description = group.get("description", "")
    plan = group.get("plan", "")
    tags = ", ".join(group.get("tags", []) or [])
    category = group.get("category", "")
    location = group.get("location", "")

    prompt = f"""
    다음 모임 정보를 참고하여 자연스러운 후기나 소개글 형태의 문단을 {num_docs}개 생성하세요.
    각 문단은 2~3문장으로 구성하고, 서로 다른 표현을 사용하세요.
    - 모임명: {name}
    - 한줄소개: {summary}
    - 설명: {description}
    - 계획: {plan}
    - 태그: {tags}
    - 카테고리: {category}
    - 위치: {location}

    아래 형식의 JSON 으로만 답변하세요:
    {{"documents": ["문단1", "문단2", ...]}}
    """

    raw = await call_vllm_api(prompt, max_tokens=512)
    try:
        cleaned = re.search(r"\{[\s\S]+\}", raw).group(0)
        parsed = json.loads(cleaned)
        texts = parsed.get("documents", [])
    except Exception:
        texts = [t.strip() for t in raw.strip().split("\n") if t.strip()]

    docs = []
    for idx, text in enumerate(texts[:num_docs]):
        docs.append({
            "id": f"synthetic-{group_id}-{idx}",
            "text": text,
            "metadata": {
                "groupId": group_id,
                "category": category,
                "location": location,
                "tags": tags,
            },
        })
    return docs
