from fastapi import WebSocket
from starlette.websockets import WebSocketState
from typing import Dict
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        ai_logger.info("[WebSocketManager] 연결 등록", extra={"session_id": session_id})

    async def disconnect(self, session_id: str):
        websocket = self.active_connections.pop(session_id, None)
        if websocket and websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        ai_logger.info("[WebSocketManager] 연결 해제", extra={"session_id": session_id})

    async def send(self, session_id: str, data: dict):
        websocket = self.active_connections.get(session_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(data)
            ai_logger.debug("[WebSocketManager] 메시지 전송", extra={"session_id": session_id, "data": data})
        else:
            ai_logger.warning("[WebSocketManager] 전송 실패: 연결 없음", extra={"session_id": session_id})

    def is_connected(self, session_id: str) -> bool:
        websocket = self.active_connections.get(session_id)
        return websocket is not None and websocket.client_state == WebSocketState.CONNECTED


websocket_manager = WebSocketManager()