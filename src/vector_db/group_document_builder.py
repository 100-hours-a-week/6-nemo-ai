from typing import Dict, Any

def build_group_document(group_response: Dict[str, Any]) -> Dict[str, Any]:
    data = group_response.get("data", group_response)
    group = group_response.get("data", {})
    group_id = group.get("groupId")

    name = group.get("name", "")
    summary = group.get("summary", "")
    description = group.get("description", "")
    plan = group.get("plan", "")
    tags = group.get("tags", []) or []

    tags_text = " ".join(tags)

    text_parts = [
        f"[모임 이름] {name}",
        f"[한줄 소개] {summary}",
        f"[설명] {description}",
        f"[계획] {plan}",
        f"[태그] {tags_text}",
    ]
    text = "\n".join(text_parts)

    metadata = {
        "groupId": group.get("groupId"),
        "category": group.get("category"),
        "location": group.get("location"),
        "maxUserCount": group.get("maxUserCount"),
        "tags": ", ".join(data["tags"]) if isinstance(data.get("tags"), list) else data.get("tags")
    }

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