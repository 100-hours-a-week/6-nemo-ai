from typing import List, Dict, Literal, TypedDict
from datetime import datetime, timedelta
import threading
import time

class ChatMessage(TypedDict):
    role: Literal["USER", "AI"]
    content: str
    timestamp: datetime

class InMemoryHistory:
    def __init__(self):
        self.messages: List[ChatMessage] = []
        self.last_access: datetime = datetime.now()

    def add_message(self, role: Literal["USER", "AI"], content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        self.last_access = datetime.now()


    def add_user_message(self, content: str):
        self.add_message("USER", content)

    def add_ai_message(self, content: str):
        self.add_message("AI", content)

    def get_messages(self) -> List[ChatMessage]:
        self.last_access = datetime.now()

        return self.messages

    def clear(self):
        self.messages = []
        self.last_access = datetime.now()


store: Dict[str, InMemoryHistory] = {}

def get_session_history(session_id: str) -> InMemoryHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    else:
        store[session_id].last_access = datetime.now()

    return store[session_id]

def chat_history_to_string(history: InMemoryHistory) -> str:
    lines = []
    for msg in history.get_messages():
        role = "사용자" if msg["role"] == "USER" else "AI"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def clean_idle_sessions(timeout_minutes: int = 10, interval_seconds: int = 60):
    def cleaner():
        while True:
            now = datetime.now()
            to_delete = [
                session_id for session_id, history in store.items()
                if now - history.last_access > timedelta(minutes=timeout_minutes)
            ]
            for session_id in to_delete:
                del store[session_id]
            time.sleep(interval_seconds)

    thread = threading.Thread(target=cleaner, daemon=True)
    thread.start()