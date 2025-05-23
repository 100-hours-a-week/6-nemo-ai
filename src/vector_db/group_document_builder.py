# src/vector_db/document_builder.py

from typing import Dict, Any

def build_group_document(group_response: Dict[str, Any]) -> Dict[str, Any]:
    group = group_response.get("data", {})
    group_id = group.get("groupId")

    name = group.get("name", "")
    summary = group.get("summary", "")
    description = group.get("description", "")
    plan = group.get("plan", "")
    tags = group.get("tags", []) or []

    tags_text = " ".join(tags)

    # 벡터화 대상 텍스트 구성
    text_parts = [
        f"[모임 이름] {name}",
        f"[한줄 소개] {summary}",
        f"[설명] {description}",
        f"[계획] {plan}",
        f"[태그] {tags_text}",
    ]
    text = "\n".join(text_parts)

    # metadata는 검색 조건용 정보만 저장
    metadata = {
        "groupId": group.get("groupId"),
        "category": group.get("category"),
        "location": group.get("location"),
        "maxUserCount": group.get("maxUserCount"),
        "tags": tags,
    }

    return {
        "id": f"group-{group_id}",
        "text": text,
        "metadata": metadata
    }
