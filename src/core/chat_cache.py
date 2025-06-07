from typing import List, Dict, Literal, TypedDict
from datetime import datetime, timedelta

MAX_HISTORY_MINUTES = 10

class ChatMessage(TypedDict):
    role: Literal["human", "ai"]
    content: str
    timestamp: datetime

class InMemoryHistory:
    def __init__(self):
        self.messages: List[ChatMessage] = []

    def _trim(self):
        cutoff = datetime.now() - timedelta(minutes=MAX_HISTORY_MINUTES)
        self.messages = [msg for msg in self.messages if msg["timestamp"] >= cutoff]

    def add_message(self, role: Literal["human", "ai"], content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        self._trim()

    def add_user_message(self, content: str):
        self.add_message("human", content)

    def add_ai_message(self, content: str):
        self.add_message("ai", content)

    def get_messages(self) -> List[ChatMessage]:
        self._trim()  # 조회 시도에도 정리
        return self.messages

    def clear(self):
        self.messages = []

store: Dict[str, InMemoryHistory] = {}

def get_session_history(user_id: str) -> InMemoryHistory:
    if user_id not in store:
        store[user_id] = InMemoryHistory()
    return store[user_id]

def chat_history_to_string(history: InMemoryHistory) -> str:
    lines = []
    for msg in history.get_messages():
        role = "사용자" if msg["role"] == "human" else "AI"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)