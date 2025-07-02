from fastapi import WebSocket
from src.core.ai_logger import get_ai_logger
import asyncio
from starlette.websockets import WebSocketState

ai_logger = get_ai_logger()

async def authenticate_websocket(websocket: WebSocket) -> str | None:
    session_id = websocket.headers.get("X-CHATBOT-KEY")
    if not session_id:
        await websocket.close(code=4401)
        ai_logger.warning("[WebSocket] 세션 ID 누락")
        return None
    return session_id


async def validate_session_message(websocket: WebSocket, data: dict, session_id: str) -> bool:
    message_id = data.get("sessionId")
    if message_id is None and isinstance(data.get("payload"), dict):
        message_id = data["payload"].get("sessionId")

    if message_id != session_id:
        await websocket.send_json({"error": "Invalid session ID", "code": 403})
        ai_logger.warning(
            "[WebSocket] 세션 ID 불일치", extra={"expected": session_id, "got": message_id}
        )
        return False
    return True

async def ping_loop(websocket: WebSocket, stop_event: asyncio.Event) -> None:
    try:
        while not stop_event.is_set():
            await asyncio.sleep(30) # change the interval as needed
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json({"type": "PING"})
                    ai_logger.debug("[WebSocket] ping sent")
                except Exception as e:
                    ai_logger.warning("[WebSocket] ping failed", extra={"error": str(e)})
                    break
    finally:
        ai_logger.info("[WebSocket] ping loop terminated")