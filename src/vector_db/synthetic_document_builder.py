from __future__ import annotations
from typing import Dict, Any, List
import json, re
import asyncio

from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

from src.models.gemma_3_4b import call_vllm_api

async def build_synthetic_documents(
    group: Dict[str, Any], num_docs: int = 3, max_retries: int = 2
) -> List[dict]:
    """Generate synthetic review-style documents for a group with retries."""
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

    base_prompt = f"""
    다음 모임 정보를 참고하여 자연스러운 후기나 소개글 형태의 문단을 작성하세요.
    문단은 4~5문장으로 구성하고, 서로 다른 표현을 사용하며 최소 80자 이상으로 작성하세요.
    - 모임명: {name}
    - 한줄소개: {summary}
    - 설명: {description}
    - 계획: {plan}
    - 태그: {tags}
    - 카테고리: {category}
    - 위치: {location}

    아래 형식의 JSON 으로만 답변하세요:
    {{"document": "문단"}}
    """

    prompts = [base_prompt for _ in range(num_docs)]

    raws: List[str] | str
    for attempt in range(max_retries + 1):
        try:
            raws = await call_vllm_api(prompts, max_tokens=768)
            if not isinstance(raws, list):
                raws = [raws]
            if any(text.strip() for text in raws):
                break
            raise ValueError("empty response")
        except Exception as e:
            ai_logger.warning(
                "[synthetic] 문서 생성 실패, 재시도",
                extra={"attempt": attempt + 1, "error": str(e), "groupId": group_id}
            )
            if attempt >= max_retries:
                ai_logger.error(
                    "[synthetic] 재시도 후 실패",
                    extra={"groupId": group_id, "error": str(e)}
                )
                raise
            await asyncio.sleep(1 + attempt)
    if not isinstance(raws, list):
        raws = [raws]

    texts = []
    for raw in raws:
        try:
            cleaned = re.search(r"\{[\s\S]+\}", raw).group(0)
            parsed = json.loads(cleaned)
            texts.append(parsed.get("document", "").strip())
        except Exception:
            texts.append(raw.strip())

    docs = []
    for idx, text in enumerate(texts[:num_docs]):
        doc_id = f"synthetic-{group_id}-{idx}"
        docs.append({
            "id": doc_id,
            "text": text,
            "metadata": {
                "groupId": group_id,
                "id": doc_id,
                "category": category,
                "location": location,
                "tags": tags,
            },
        })
    return docs
