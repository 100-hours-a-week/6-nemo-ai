# 표준 라이브러리
import logging
from contextlib import asynccontextmanager
# 외부 라이브러리
import torch
from fastapi import FastAPI
# 미들웨어
from src.middleware.http import log_requests, LogRequestsMiddleware
from src.middleware.ai_logger import AILoggingMiddleware
# 라우터
from src.router.v1 import health
from src.router.v1 import group_information as v1_group_information
# from src.router.v2 import group_information as v2_group_information
from src.router.v2 import vector_db, chatbot
# 코어 유틸
from src.core.ai_logger import get_ai_logger
from src.core.exception_handler import setup_exception_handlers
from src.core.chat_cache import clean_idle_sessions  # 저장 위치에 따라 조정
# 벡터 DB 관련
from src.vector_db.chroma_client import get_chroma_client, chroma_collection_exists
from src.vector_db.sync import (
    fetch_data_from_mysql,
    sync_group_documents,
    sync_user_documents,
)
# from src.tests.rate_test import router as rate_test_router
from src.router.v2.ws_chatbot import router as ws_chatbot_router


# 로거 초기화
ai_logger = get_ai_logger()
ai_logger.info("[시스템 시작] FastAPI 서버 초기화 및 Cloud Logging 활성화")

# 로깅 레벨 설정
logging.getLogger("chromadb").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    chroma = get_chroma_client()

    should_sync_user = not chroma_collection_exists("user-activity", chroma)
    should_sync_group = not chroma_collection_exists("group-info", chroma)

    if not (should_sync_user or should_sync_group):
        ai_logger.info("[Chroma] 모든 컬렉션 존재 → 동기화 생략")
    else:
        ai_logger.info("[Chroma] 일부 컬렉션 누락 → MySQL에서 데이터 불러오는 중")
        user_participation, group_infos = fetch_data_from_mysql()

        if should_sync_user:
            ai_logger.info(f"[Chroma] 유저 문서 {len(user_participation)}건 동기화 중")
            sync_user_documents(user_participation)

        if should_sync_group:
            ai_logger.info(f"[Chroma] 그룹 문서 {len(group_infos)}건 동기화 중")
            await sync_group_documents(group_infos)

        ai_logger.info("[Chroma] 필요한 항목 동기화 완료")
    clean_idle_sessions()
    yield
    ai_logger.info("[Chroma] Lifespan 종료 - 앱 shutdown")
app = FastAPI(
    title="NE:MO AI API",
    description="네가 찾는 모임: 네모",
    version="2.0.0",
    lifespan=lifespan
)

setup_exception_handlers(app)

# [AI] 성능 로깅 미들웨어 등록
app.add_middleware(AILoggingMiddleware)
app.middleware("http")(log_requests)
app.add_middleware(LogRequestsMiddleware)
@app.get("/")
def root():
    return {"message": "Ne:Mo AI Server Running!"}
app.include_router(health.router)
# app.include_router(rate_test_router)
app.include_router(vector_db.router, prefix="/ai/v2")
app.include_router(chatbot.router, prefix="/ai/v2")
# app.include_router(ws_chatbot.router)
app.include_router(ws_chatbot_router, prefix="/ai/v2")

# [AI] v1 라우터 등록
ai_logger.info("[AI] [라우터 등록 시작] v1 group_information 라우터 준비 중")
app.include_router(v1_group_information.router, prefix="/ai/v1")
ai_logger.info("[AI] [라우터 등록 완료] v1 group_information 라우터 활성화")
# [AI] v2 라우터 등록
# ai_logger.info("[AI-v2] [라우터 등록 시작] v2 group_information 라우터 준비 중")
# app.include_router(v2_group_information.router, prefix="/ai/v2")
# ai_logger.info("[AI-v2] [라우터 등록 완료] v2 group_information 라우터 활성화")

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
