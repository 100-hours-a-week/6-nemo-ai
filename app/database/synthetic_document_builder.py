from __future__ import annotations
from typing import Dict, Any, List
import json, re
import asyncio

from app.core.ai_logger import get_ai_logger
from app.models.text_generation_model import call_vllm_api
from app.prompts.prompt_loader import load_prompt_template

ai_logger = get_ai_logger()

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
        load_prompt_template("synthetic_review", "v3", 
                           name=name, category=category, location=location, 
                           description=description, tags=tags),
        
        load_prompt_template("synthetic_recommendation", "v3",
                           name=name, summary=summary, plan=plan, 
                           location=location, tags=tags),
        
        load_prompt_template("synthetic_introduction", "v3",
                           name=name, category=category, description=description, 
                           location=location)
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
