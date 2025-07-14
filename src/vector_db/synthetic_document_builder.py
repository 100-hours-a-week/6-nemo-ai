from __future__ import annotations
from typing import Dict, Any, List
import json, re
import asyncio

from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

from src.models.gemma_3_4b import call_vllm_api

async def build_synthetic_documents(
    group: Dict[str, Any], num_docs: int =2, max_retries: int = 2
) -> List[dict]:
    """Generate synthetic review-style documents for a group with semantic diversity."""
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

    # Create diverse prompts for semantic variety
    prompt_templates = [
        f"""
        다음 모임에 대한 참가자 후기를 자연스럽게 작성하세요. 실제 경험담처럼 작성하되 구체적인 활동과 감정을 포함하세요.
        모임: {name} | 카테고리: {category} | 위치: {location}
        설명: {description}
        태그: {tags}
        
        4-5문장, 최소 80자 이상으로 작성하세요.
        {{"document": "후기 내용"}}
        """,
        
        f"""
        다음 모임을 추천하는 글을 작성하세요. 어떤 사람들에게 좋을지, 어떤 활동을 하는지 구체적으로 설명하세요.
        모임명: {name}
        한줄소개: {summary}
        계획: {plan}
        위치: {location}
        태그: {tags}
        
        4-5문장으로 자연스럽게 작성하세요.
        {{"document": "추천 내용"}}
        """,
        
        f"""
        다음 모임의 분위기와 특징을 소개하는 글을 작성하세요. 모임의 고유한 매력과 참가자들의 성향을 포함하세요.
        모임: {name}
        카테고리: {category}
        설명: {description}
        위치: {location}
        
        구체적이고 생생하게 4-5문장으로 작성하세요.
        {{"document": "소개 내용"}}
        """
    ]

    # Use different prompts for diversity
    prompts = prompt_templates[:num_docs] if len(prompt_templates) >= num_docs else prompt_templates * ((num_docs // len(prompt_templates)) + 1)
    prompts = prompts[:num_docs]

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
            text = parsed.get("document", "").strip()
            
            # Ensure minimum quality and length
            if len(text) < 50:  # Reject too short responses
                text = f"{summary} {description}".strip()  # Fallback
            
            texts.append(text)
        except Exception:
            # Fallback to raw text if JSON parsing fails
            fallback_text = raw.strip()
            if len(fallback_text) < 50:
                fallback_text = f"{name} 모임입니다. {summary} {description}".strip()
            texts.append(fallback_text)

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
                "synthetic_type": ["review", "recommendation", "introduction"][idx % 3],  # Track type for analysis
            },
        })
    return docs
