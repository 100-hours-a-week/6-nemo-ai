from typing import Dict, Any

def build_user_document(user_response: Dict[str, Any]) -> Dict[str, Any]:
    user = user_response.get("data", {})
    user_id = user.get("user_id")
    group_id = user.get("group_id")

    text = f"User {user_id} joined Group {group_id}"

    return {
        "id": f"user-{user_id}-group-{group_id}",
        "text": text,
        "metadata": user
    }
