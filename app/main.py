# 표준 라이브러리
from contextlib import asynccontextmanager
import asyncio
# 외부 라이브러리
from fastapi import FastAPI
# 모니터링
from app.integrations.monitoring import PrometheusConfig, setup_monitoring_logging
# 미들웨어
from app.middleware.http import log_requests, LogRequestsMiddleware
from app.middleware.ai_logger import AILoggingMiddleware
# 라우터
from app.router.v1 import health
from app.router.v1 import group_information as v1_group_information
from app.router.v2 import group_information as v2_group_information
from app.router.v2 import vector_db, chatbot
# 코어 유틸
from app.core.ai_logger import initialize_logging
from app.core.exception_handler import setup_exception_handlers
from app.core.chat_cache import clean_idle_sessions  # 저장 위치에 따라 조정
# 벡터 DB 관련
from app.database.chroma_client import get_chroma_client, chroma_collection_exists
from app.database.sync import (
    fetch_data_from_mysql,
    sync_group_documents,
    sync_user_documents,
)
from app.router.v3.ws_chatbot import router as ws_chatbot_router
from app.integrations.kafka.kafka_consumer_manager import KafkaConsumerManager

# Initialize all logging consistently
ai_logger = initialize_logging()
ai_logger.info("시스템 시작 FastAPI 서버 초기화 및 Cloud Logging 활성화")

# 모니터링 로깅 설정
monitoring_logger = setup_monitoring_logging()
monitoring_logger.info("모니터링 시스템 초기화 시작")

kafka_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global kafka_manager
    # Start Chroma sync and Kafka in the background after FastAPI is up
    async def chroma_and_kafka():
        chroma = get_chroma_client()
        should_sync_user = not chroma_collection_exists("user-activity", chroma)
        should_sync_group = not chroma_collection_exists("group-info", chroma)
        if not (should_sync_user or should_sync_group):
            ai_logger.info("Chroma 모든 컬렉션 존재 → 동기화 생략")
        else:
            ai_logger.info("Chroma 일부 컬렉션 누락 → MySQL에서 데이터 불러오는 중")
            user_participation, group_infos = fetch_data_from_mysql()
            if should_sync_user:
                ai_logger.info(f"Chroma 유저 문서 {len(user_participation)}건 동기화 중")
                sync_user_documents(user_participation)
            if should_sync_group:
                ai_logger.info(f"Chroma 그룹 문서 {len(group_infos)}건 동기화 중")
                await sync_group_documents(group_infos)
            ai_logger.info("Chroma 필요한 항목 동기화 완료")
        clean_idle_sessions()
        # Kafka (after Chroma sync)
        kafka_manager_local = KafkaConsumerManager()
        await kafka_manager_local.start_consumers()
        global kafka_manager
        kafka_manager = kafka_manager_local
    # Start the background task
    asyncio.create_task(chroma_and_kafka())
    yield
    # Shutdown logic
    if kafka_manager and hasattr(kafka_manager, 'stop_consumers'):
        await kafka_manager.stop_consumers()
        ai_logger.info("Kafka Lifespan 종료: 앱 shutdown")

app = FastAPI(
    title="NE:MO AI API",
    description="네가 찾는 모임: 네모",
    version="3.0.0",
    lifespan=lifespan
)

# 모니터링 설정
prometheus_config = PrometheusConfig(
    service_name="NE:MO-AI",
    version="3.0.0",
    environment="production"
)

# Prometheus 계측 설정 및 메트릭 엔드포인트 노출
prometheus_config.setup_instrumentator(app).expose_metrics(app)
monitoring_logger.info("Prometheus 메트릭 엔드포인트 활성화: /metrics")

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
ai_logger.info("[V1] 라우터 등록 시작: v1 group_information 라우터 준비 중")
app.include_router(v1_group_information.router, prefix="/ai/v1")
ai_logger.info("[V1] 라우터 등록 완료: v1 group_information 라우터 활성화")
# [AI] v2 라우터 등록
ai_logger.info("[V2] 라우터 등록 시작: v2 group_information 라우터 준비 중")
app.include_router(v2_group_information.router, prefix="/ai/v2")
ai_logger.info("[V2] 라우터 등록 완료: v2 group_information 라우터 활성화")

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    host = "0.0.0.0"
    port = 8000
    ai_logger.info("FastAPI 실행 서버 시작 전 초기화")
    try:
        uvicorn.run(app, host=host, port=port)
        ai_logger.info("FastAPI 실행 완료 서버가 정상적으로 실행되었습니다.")
    except Exception as e:
        ai_logger.error("FastAPI 실행 오류 서버 실행 중 예외 발생", exc_info=True)
