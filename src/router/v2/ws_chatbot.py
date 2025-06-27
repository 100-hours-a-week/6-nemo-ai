from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from src.core.ai_logger import get_ai_logger
from src.core.websocket_manager import websocket_manager
from src.services.v2.ws_chatbot import stream_question_chunks, stream_recommendation_chunks
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws/groups/recommendations", tags=["WebSocket"])
ai_logger = get_ai_logger()


@router.websocket("/questions")
async def stream_question(websocket: WebSocket):
    session_id = websocket.headers.get("x-session-id")
    if not session_id:
        await websocket.close(code=4400)
        return

    await websocket_manager.connect(session_id, websocket)
    ai_logger.info("[WS 연결 수락됨]", extra={"session_id": session_id})

    try:
        while True:
            data = await websocket.receive_json()
            user_id = str(data.get("userId"))
            answer = data.get("answer")

            ai_logger.info("[WS 질문 요청 수신]", extra={
                "session_id": session_id,
                "user_id": user_id,
                "answer": answer
            })

            question_so_far = ""

            async for chunk in stream_question_chunks(answer, user_id, session_id):
                if isinstance(chunk, str):
                    question_so_far += chunk
                    await websocket.send_json({
                        "code": 200,
                        "message": "streaming",
                        "data": {
                            "question": question_so_far,
                            "options": None
                        }
                    })
                elif isinstance(chunk, tuple) and chunk[0] == "__COMPLETE__":
                    result = chunk[1]
                    await websocket.send_json({
                        "code": 200,
                        "message": "complete",
                        "data": {
                            "question": result["question"],
                            "options": result["options"]
                        }
                    })

    except WebSocketDisconnect:
        ai_logger.info("[WS 연결 종료]", extra={"session_id": session_id})
    finally:
        await websocket_manager.disconnect(session_id)


@router.websocket("/recommendations")
async def stream_recommendation(websocket: WebSocket):
    session_id = websocket.headers.get("x-session-id")
    if not session_id:
        await websocket.close(code=4400)
        return

    await websocket_manager.connect(session_id, websocket)
    ai_logger.info("[WS 연결 수락됨 - 추천]", extra={"session_id": session_id})

    try:
        while True:
            data = await websocket.receive_json()
            user_id = str(data.get("userId"))
            messages = data.get("messages", [])

            ai_logger.info("[WS 추천 요청 수신]", extra={
                "session_id": session_id,
                "user_id": user_id,
                "messages": [m.get("text") for m in messages]
            })

            reason_so_far = ""
            group_id = None

            async for chunk in stream_recommendation_chunks(messages, user_id, session_id):
                # 스트리밍 중 (chunk는 str)
                if isinstance(chunk, str):
                    reason_so_far += chunk
                    await websocket.send_json({
                        "code": 200,
                        "message": "streaming",
                        "data": {
                            "groupId": group_id,
                            "reason": reason_so_far
                        }
                    })

                # 마지막 완료 시점: ("__COMPLETE__", group_id, reason)
                elif isinstance(chunk, tuple) and chunk[0] == "__COMPLETE__":
                    _, group_id, final_reason = chunk
                    await websocket.send_json({
                        "code": 200,
                        "message": "complete",
                        "data": {
                            "groupId": group_id,
                            "reason": final_reason
                        }
                    })

    except WebSocketDisconnect:
        ai_logger.info("[WS 연결 종료 - 추천]", extra={"session_id": session_id})
    finally:
        await websocket_manager.disconnect(session_id)
