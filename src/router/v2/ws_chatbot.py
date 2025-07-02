from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.core.websocket_manager import websocket_manager
from src.core.ai_logger import get_ai_logger
from src.middleware import authenticate_websocket, validate_session_message, ping_loop
from src.services.v2.ws_chatbot import (
    stream_question_chunks,
    stream_recommendation_chunks,
)
import asyncio

router = APIRouter(prefix="/chatbot", tags=["WebSocket"])
ai_logger = get_ai_logger()


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    session_id = await authenticate_websocket(websocket)
    if not session_id:
        return

    await websocket_manager.connect(session_id, websocket)
    ai_logger.info("[WS 연결 수락됨]", extra={"session_id": session_id})
    stop_event = asyncio.Event()
    ping_task = asyncio.create_task(ping_loop(websocket, stop_event))

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "PONG":
                continue
            if not await validate_session_message(websocket, data, session_id):
                continue
            type_ = data.get("type")
            payload = data.get("payload", {})

            user_id = str(payload.get("userId"))
            ai_logger.info("[WS 메시지 수신]", extra={
                "session_id": session_id,
                "type": type_,
                "user_id": user_id
            })

            if type_ == "CREATE_QUESTION":
                answer = payload.get("answer")

                ai_logger.info("[질문 생성 요청 처리 시작]", extra={
                    "session_id": session_id,
                    "answer": answer
                })

                async for chunk in stream_question_chunks(answer, user_id, session_id):
                    if isinstance(chunk, str):
                        await websocket.send_json({
                            "type": "QUESTION_CHUNK",
                            "payload": {
                                "sessionId": session_id,
                                "text": chunk
                            }
                        })
                        ai_logger.debug(f"[질문 청크 전송] {chunk}", extra={
                            "session_id": session_id,
                        })

                    elif isinstance(chunk, tuple) and chunk[0] == "__COMPLETE__":
                        result = chunk[1]
                        await websocket.send_json({
                            "type": "QUESTION_OPTIONS",
                            "payload": {
                                "sessionId": session_id,
                                "options": result.get("options")
                            }
                        })
                        ai_logger.info("[질문 옵션 전송 완료]", extra={
                            "session_id": session_id,
                            "options": result.get("options")
                        })

            elif type_ == "RECOMMEND_REQUEST":
                messages = payload.get("messages", [])
                ai_logger.info("[추천 요청 처리 시작]", extra={
                    "session_id": session_id,
                    "messages": [m.get("text") for m in messages]
                })

                group_id = None
                group_id_sent = False

                async for chunk in stream_recommendation_chunks(messages, user_id, session_id):
                    if isinstance(chunk, tuple) and chunk[0] == "RECOMMEND_DONE":
                        await websocket.send_json({
                            "type": "RECOMMEND_DONE",
                            "payload": {
                                "sessionId": session_id,
                                "reason": None
                            }
                        })
                        ai_logger.info("[추천 완료 시그널 전송 및 처리 종료]", extra={"session_id": session_id})
                        break

                    if isinstance(chunk, tuple) and chunk[0] == "__COMPLETE__":
                        _, group_id, final_reason = chunk
                        if not group_id_sent and group_id is not None:
                            await websocket.send_json({
                                "type": "RECOMMEND_ID",
                                "payload": {
                                    "sessionId": session_id,
                                    "groupId": group_id
                                }
                            })
                            group_id_sent = True
                        await websocket.send_json({
                            "type": "RECOMMEND_REASON",
                            "payload": {
                                "sessionId": session_id,
                                "reason": final_reason or ""
                            }
                        })
                        ai_logger.info("[추천 결과 전송 완료]", extra={
                            "session_id": session_id,
                            "groupId": group_id
                        })
                        continue

                    if isinstance(chunk, tuple):
                        group_id, partial_text = chunk
                        if not group_id_sent and group_id is not None:
                            await websocket.send_json({
                                "type": "RECOMMEND_ID",
                                "payload": {
                                    "sessionId": session_id,
                                    "groupId": group_id
                                }
                            })
                            group_id_sent = True
                    else:
                        partial_text = chunk

                    await websocket.send_json({
                        "type": "RECOMMEND_REASON",
                        "payload": {
                            "sessionId": session_id,
                            "reason": partial_text
                        }
                    })
                    ai_logger.debug(f"[추천 청크 전송] {chunk}", extra={
                        "session_id": session_id
                    })
    except WebSocketDisconnect:
        ai_logger.info("[WS 연결 종료]", extra={"session_id": session_id})
    except Exception as e:
        ai_logger.error("[WS 처리 중 오류 발생]", extra={
            "session_id": session_id,
            "error": str(e)
        })
    finally:
        stop_event.set()
        await ping_task
        await websocket_manager.disconnect(session_id)
