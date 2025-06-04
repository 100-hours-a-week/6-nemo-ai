from typing import Dict, Any

def build_user_document(user_response: Dict[str, Any]) -> Dict[str, Any]:
    user_id = user_response.get("user_id")
    group_id = user_response.get("group_id")

    if not user_id or not group_id:
        raise ValueError("user_id와 group_id는 반드시 있어야 합니다.")

    text = f"User {user_id} joined Group {group_id}"

    metadata = {
        "user_id": str(user_id),
        "group_id": str(group_id)
    }

    return {
        "id": f"user-{user_id}-group-{group_id}",
        "text": text,
        "metadata": metadata
    }