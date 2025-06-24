from typing import List, Dict, Literal, TypedDict
from datetime import datetime

class ChatMessage(TypedDict):
    role: Literal["USER", "AI"]
    content: str
    timestamp: datetime

class InMemoryHistory:
    def __init__(self):
        self.messages: List[ChatMessage] = []

    def add_message(self, role: Literal["USER", "AI"], content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })

    def add_user_message(self, content: str):
        self.add_message("USER", content)

    def add_ai_message(self, content: str):
        self.add_message("AI", content)

    def get_messages(self) -> List[ChatMessage]:
        return self.messages

    def clear(self):
        self.messages = []

store: Dict[str, InMemoryHistory] = {}

def get_session_history(session_id: str) -> InMemoryHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]

def chat_history_to_string(history: InMemoryHistory) -> str:
    lines = []
    for msg in history.get_messages():
        role = "사용자" if msg["role"] == "USER" else "AI"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)