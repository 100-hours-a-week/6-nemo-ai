from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.models.gemma_3_4b import stream_vllm_response
from src.core.ai_logger import get_ai_logger

router = APIRouter()
ai_logger = get_ai_logger()

@router.websocket("/ws/test-llm")
async def websocket_test_llm(websocket: WebSocket):
    await websocket.accept()
    ai_logger.info("[LLM 테스트 WS] 연결 수락됨")

    try:
        # 1. 클라이언트로부터 프롬프트 수신
        payload = await websocket.receive_json()
        prompt = payload.get("prompt", "").strip()
        if not prompt:
            await websocket.send_json({
                "code": 400,
                "message": "프롬프트가 없습니다.",
                "data": {}
            })
            return

        ai_logger.info("[LLM 테스트 WS] 프롬프트 수신", extra={"prompt": prompt})

        # 2. 메시지 구성 (system + user 역할)
        messages = [
            {
                "role": "system",
                "text": "당신은 한국어로 대화하는 친절한 챗봇입니다. 모든 응답은 한국어로 진행됩니다."
            },
            {
                "role": "user",
                "text": prompt
            }
        ]

        # 3. 토큰 단위로 응답 스트리밍 전송
        async for token in stream_vllm_response(messages):
            await websocket.send_json({
                "code": 200,
                "message": "streaming",
                "data": {
                    "token": token  # ✅ 누적된 문장이 아니라 단일 토큰만 보냄
                }
            })

        # 4. 완료 신호 전송
        await websocket.send_json({
            "code": 200,
            "message": "complete",
            "data": {
                "done": True
            }
        })

    except WebSocketDisconnect:
        ai_logger.info("[LLM 테스트 WS] 클라이언트 연결 종료됨")

    except Exception as e:
        ai_logger.warning("[LLM 테스트 WS] 예외 발생", extra={"error": str(e)})
        await websocket.send_json({
            "code": 500,
            "message": f"LLM 테스트 중 오류: {str(e)}",
            "data": {}
        })