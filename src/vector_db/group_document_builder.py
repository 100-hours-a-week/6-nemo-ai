from typing import Dict, Any
from typing import Dict, Any

def build_group_document(group_response: Dict[str, Any]) -> Dict[str, Any]:
    group_id = str(group_response.get("groupId"))  # 항상 str로 강제

    name = group_response.get("name", "")
    summary = group_response.get("summary", "")
    description = group_response.get("description", "")
    plan = group_response.get("plan", "")
    tags = group_response.get("tags", [])
    if tags is None:
        tags = []

    tags_text = " ".join(tags)

    text_parts = [
        f"[모임 이름] {name}",
        f"[한줄 소개] {summary}",
        f"[설명] {description}",
        f"[계획] {plan}",
        f"[태그] {tags_text}",
    ]
    text = "\n".join(text_parts)

    raw_metadata = {
        "groupId": group_id,
        "category": group_response.get("category"),
        "location": group_response.get("location"),
        "maxUserCount": int(group_response["maxUserCount"]) if group_response.get("maxUserCount") else None,
        "tags": ", ".join(tags)
    }

    metadata = {k: v for k, v in raw_metadata.items() if v is not None}

    return {
        "id": f"group-{group_id}",
        "text": text,
        "metadata": metadata
    }

def build_document_from_partial(partial_update: Dict[str, Any], group_id: Any) -> Dict[str, Any]:
    text_parts = []
    if "name" in partial_update:
        text_parts.append(f"[모임 이름] {partial_update['name']}")
    if "summary" in partial_update:
        text_parts.append(f"[한줄 소개] {partial_update['summary']}")
    if "description" in partial_update:
        text_parts.append(f"[설명] {partial_update['description']}")
    if "plan" in partial_update:
        text_parts.append(f"[계획] {partial_update['plan']}")
    if "tags" in partial_update:
        tags_text = " ".join(partial_update["tags"])
        text_parts.append(f"[태그] {tags_text}")

    text = "\n".join(text_parts)

    return {
        "id": f"group-{group_id}",
        "text": text,
        "metadata": partial_update  # 변경된 필드만 저장
    }