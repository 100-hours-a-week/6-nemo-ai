from typing import List, Dict, Literal, TypedDict

MAX_HISTORY_MESSAGES = 6  # 최대 저장 메시지 수

# 메시지 타입 정의
class ChatMessage(TypedDict):
    role: Literal["human", "ai"]
    content: str

# 히스토리 클래스 정의
class InMemoryHistory:
    def __init__(self):
        self.messages: List[ChatMessage] = []

    def _trim(self):
        """최신 MAX_HISTORY_MESSAGES 개만 유지"""
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            self.messages = self.messages[-MAX_HISTORY_MESSAGES:]

    def add_message(self, role: Literal["human", "ai"], content: str):
        self.messages.append({"role": role, "content": content})
        self._trim()

    def add_user_message(self, content: str):
        self.add_message("human", content)

    def add_ai_message(self, content: str):
        self.add_message("ai", content)

    def get_messages(self) -> List[ChatMessage]:
        return self.messages

    def clear(self):
        self.messages = []

# 사용자별 세션 저장소
store: Dict[str, InMemoryHistory] = {}

def get_session_history(user_id: str) -> InMemoryHistory:
    if user_id not in store:
        store[user_id] = InMemoryHistory()
    return store[user_id]

# 히스토리를 문자열로 변환
def chat_history_to_string(history: InMemoryHistory) -> str:
    lines = []
    for msg in history.get_messages():
        role = "사용자" if msg["role"] == "human" else "AI"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)
