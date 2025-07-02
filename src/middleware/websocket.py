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

async def ping_loop(websocket: WebSocket, stop_event: asyncio.Event, interval: int = 30) -> None:
    try:
        while not stop_event.is_set():
            await asyncio.sleep(interval)
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_ping()
                    ai_logger.debug("[WebSocket] ping 프레임 전송됨")
                except Exception as e:
                    ai_logger.debug("[WebSocket] ping 전송 실패 - 연결 종료 추정", extra={"error": str(e)})
                    stop_event.set()
                    break
            else:
                ai_logger.debug("[WebSocket] 클라이언트 상태가 CONNECTED가 아님 - 종료")
                stop_event.set()
                break
    finally:
        ai_logger.info("[WebSocket] ping loop 정상 종료됨")