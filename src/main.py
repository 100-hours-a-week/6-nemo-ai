from fastapi import FastAPI
#from src.router.v1 import group_information as v1_group_information
from src.router.v1 import health
from src.router.v2 import group_information as v2_group_information
import torch
from src.core.ai_logger import get_ai_logger
from src.core.exception_handler import setup_exception_handlers
from src.router.v2 import vector_db, chatbot
from src.middleware.ai_logger import AILoggingMiddleware
import logging

torch.set_float32_matmul_precision("high")
# 로거 초기화
ai_logger = get_ai_logger()
ai_logger.info("[시스템 시작] FastAPI 서버 초기화 및 Cloud Logging 활성화")

# 로깅 레벨 설정
logging.getLogger("chromadb").setLevel(logging.WARNING)

# 앱 초기화
app = FastAPI(
    title="NE:MO AI API",
    description="네가 찾는 모임: 네모",
    version="1.9.0"
)
setup_exception_handlers(app)

# [AI] 성능 로깅 미들웨어 등록
app.add_middleware(AILoggingMiddleware)

app.include_router(health.router)
app.include_router(vector_db.router, prefix="/ai/v2")
app.include_router(chatbot.router, prefix="/ai/v2")

@app.get("/")
def root():
    return {"message": "Ne:Mo AI Server Running!"}

# 공통 헬스 체크 라우터

app.include_router(health.router)
# [AI] v2 라우터 등록
ai_logger.info("[AI-v2] [라우터 등록 시작] v2 group_information 라우터 준비 중")
app.include_router(v2_group_information.router, prefix="/ai/v2")
ai_logger.info("[AI-v2] [라우터 등록 완료] v2 group_information 라우터 활성화")
app.include_router(vector_db.router, prefix="/ai/v2")
app.include_router(chatbot.router, prefix="/ai/v2")

# [AI] v1 라우터 등록
#ai_logger.info("[AI] [라우터 등록 시작] v1 group_information 라우터 준비 중")
#app.include_router(v1_group_information.router, prefix="/ai/v1")
#ai_logger.info("[AI] [라우터 등록 완료] v1 group_information 라우터 활성화")


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
