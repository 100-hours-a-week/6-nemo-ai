from fastapi import FastAPI
from src.router.v1 import group_information, health
from src.core.ai_logger import get_ai_logger
from src.core.exception_handler import setup_exception_handlers
from src.middleware.ai_logger import AILoggingMiddleware
import logging
import src.core.vertex_client

# 로거 초기화
ai_logger = get_ai_logger()
ai_logger.info("[시스템 시작] FastAPI 서버 초기화 및 Cloud Logging 활성화")

# 로깅 레벨 설정
logging.getLogger("chromadb").setLevel(logging.WARNING)

# 앱 초기화
app = FastAPI()
setup_exception_handlers(app)

# [AI] 성능 로깅 미들웨어 등록
app.add_middleware(AILoggingMiddleware)

@app.get("/")
def root():
    return {"message": "Hello World"}

app.include_router(health.router)

# [AI] 라우터 등록
ai_logger.info("[AI] [라우터 등록 시작] group_information 라우터 준비 중")
app.include_router(group_information.router, prefix="/ai/v1")
ai_logger.info("[AI] [라우터 등록 완료] group_information 라우터 활성화")

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    host = "0.0.0.0"
    port = 8000
    ai_logger.info("[FastAPI 실행] 서버 시작 전 초기화")
    try:
        uvicorn.run(app, host=host, port=port)
        ai_logger.info("[FastAPI 실행 완료] 서버가 정상적으로 실행되었습니다.")
    except Exception as e:
        ai_logger.error("[FastAPI 실행 오류] 서버 실행 중 예외 발생", exc_info=True)
