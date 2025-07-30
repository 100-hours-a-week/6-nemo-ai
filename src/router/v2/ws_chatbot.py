from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
import asyncio
from src.core.websocket_manager import websocket_manager
from src.core.ai_logger import get_ai_logger
from src.middleware import authenticate_websocket, validate_session_message, ping_loop
from src.services.v2.ws_chatbot import (
    stream_question_chunks,
    stream_recommendation_chunks,
)
from src.models.gemma_3_4b import get_vllm_health_metrics

router = APIRouter(prefix="/chatbot", tags=["WebSocket"])
ai_logger = get_ai_logger()

@router.get("/health")
async def get_health_status():
    """Get vLLM service health status and metrics"""
    try:
        metrics = await get_vllm_health_metrics()
        return JSONResponse(content={
            "status": "healthy" if metrics["health"]["is_healthy"] else "unhealthy",
            "metrics": metrics,
            "timestamp": metrics["timestamp"]
        })
    except Exception as e:
        ai_logger.error(f"[Health Check] 상태 확인 실패: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

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

                try:
                    async for chunk in stream_question_chunks(answer, user_id, session_id):
                        if isinstance(chunk, str):
                            await websocket.send_json({
                                "type": "QUESTION_CHUNK",
                                "payload": {
                                    "sessionId": session_id,
                                    "text": chunk
                                }
                            })
                            ai_logger.debug(f"[질문 청크 전송] {chunk[:50]}{'...' if len(chunk) > 50 else ''}", extra={
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
                except Exception as question_error:
                    ai_logger.error(f"[질문 생성 중 오류] {str(question_error)}", extra={
                        "session_id": session_id,
                        "error": str(question_error),
                        "error_type": type(question_error).__name__
                    }, exc_info=True)
                    raise  # Re-raise to be caught by outer exception handler

            elif type_ == "RECOMMEND_REQUEST":
                messages = payload.get("messages", [])
                ai_logger.info("[추천 요청 처리 시작]", extra={
                    "session_id": session_id,
                    "messages": [m.get("text") for m in messages]
                })

                group_id = None
                group_id_sent = False

                try:
                    async for chunk in stream_recommendation_chunks(messages, user_id, session_id):
                        if isinstance(chunk, tuple) and chunk[0] == "RECOMMEND_DONE":
                            # chunk[1] contains group_id, chunk[2] contains final message if any
                            final_group_id = chunk[1] if len(chunk) > 1 else None
                            final_message = chunk[2] if len(chunk) > 2 else None
                            
                            await websocket.send_json({
                                "type": "RECOMMEND_DONE",
                                "payload": {
                                    "sessionId": session_id,
                                    "groupId": final_group_id,
                                    "reason": final_message
                                }
                            })
                            ai_logger.info("[추천 완료 시그널 전송 및 처리 종료]", extra={
                                "session_id": session_id,
                                "group_id": final_group_id,
                                "success": final_group_id != -1
                            })
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
                                if group_id == -1:
                                    ai_logger.info("[추천 실패 ID 전송]", extra={
                                        "session_id": session_id,
                                        "group_id": group_id
                                    })
                                else:
                                    ai_logger.info("[추천 그룹 ID 전송]", extra={
                                        "session_id": session_id,
                                        "group_id": group_id
                                    })
                        else:
                            partial_text = chunk

                        await websocket.send_json({
                            "type": "RECOMMEND_REASON",
                            "payload": {
                                "sessionId": session_id,
                                "reason": partial_text
                            }
                        })
                        ai_logger.debug(f"[추천 청크 전송] {str(chunk)[:50]}{'...' if len(str(chunk)) > 50 else ''}", extra={
                            "session_id": session_id
                        })
                except Exception as recommend_error:
                    ai_logger.error(f"[추천 처리 중 오류] {str(recommend_error)}", extra={
                        "session_id": session_id,
                        "error": str(recommend_error),
                        "error_type": type(recommend_error).__name__
                    }, exc_info=True)
                    raise  # Re-raise to be caught by outer exception handler
    except WebSocketDisconnect:
        ai_logger.info("[WS 연결 종료]", extra={"session_id": session_id})
    except Exception as e:
        ai_logger.error(f"[WS 처리 중 오류 발생] {str(e)}", extra={
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__
        }, exc_info=True)
        
        # Send error message to client
        try:
            await websocket.send_json({
                "type": "ERROR",
                "payload": {
                    "sessionId": session_id,
                    "message": "서버에서 오류가 발생했습니다. 다시 시도해주세요.",
                    "error_code": "INTERNAL_ERROR"
                }
            })
        except Exception as send_error:
            ai_logger.warning(f"[오류 메시지 전송 실패]: {send_error}")
        
        # Log health metrics on error for debugging
        try:
            health_metrics = await get_vllm_health_metrics()
            ai_logger.error("[오류 발생 시 vLLM 상태]", extra={"metrics": health_metrics})
        except Exception as health_error:
            ai_logger.warning(f"[Health check 실패]: {health_error}")
            
    finally:
        stop_event.set()
        await ping_task
        await websocket_manager.disconnect(session_id)
