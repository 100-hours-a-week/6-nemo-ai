from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.core.websocket_manager import websocket_manager
from src.core.ai_logger import get_ai_logger
from src.services.v2.ws_chatbot import stream_question_chunks, stream_recommendation_chunks

router = APIRouter(prefix="/chatbot", tags=["WebSocket"])
ai_logger = get_ai_logger()


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    session_id = websocket.headers.get("X-CHATBOT-KEY")
    if not session_id:
        await websocket.close(code=4400)
        return

    await websocket_manager.connect(session_id, websocket)
    ai_logger.info("[WS 연결 수락됨]", extra={"session_id": session_id})

    try:
        while True:
            data = await websocket.receive_json()
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
                        ai_logger.debug("[질문 청크 전송]", extra={
                            "session_id": session_id,
                            "chunk": chunk
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

                    else:
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
                        ai_logger.debug("[추천 청크 전송]", extra={
                            "session_id": session_id,
                            "chunk": partial_text
                        })

            else:
                ai_logger.warning("[알 수 없는 type 요청]", extra={
                    "session_id": session_id,
                    "type": type_
                })

    except WebSocketDisconnect:
        ai_logger.info("[WS 연결 종료]", extra={"session_id": session_id})
    except Exception as e:
        ai_logger.error("[WS 처리 중 오류 발생]", extra={
            "session_id": session_id,
            "error": str(e)
        })
    finally:
        await websocket_manager.disconnect(session_id)
