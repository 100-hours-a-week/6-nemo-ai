from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from src.router.v1 import group_information
from src.core.logging_config import logger
import logging

logger.info("[시스템 시작] FastAPI 서버 초기화 및 Cloud Logging 활성화")

# 로깅 설정
logging.getLogger("chromadb").setLevel(logging.WARNING)

app = FastAPI()

@app.get("/")
def root():
    logger.info("[루트 엔드포인트] / 호출됨")  # milestone: 사용자 요청 진입
    return {"message": "Hello World: Version 1 API is running"}

#정상 작동
# app.include_router(vector_db.router, prefix="/ai/v1")
# app.include_router(tag_extraction.router, prefix="/ai/v1")
# app.include_router(group_writer.router, prefix="/ai/v1")

#  milestone: 라우터 등록 전후 로깅
logger.info("[라우터 등록 시작] group_information 라우터 준비 중")
app.include_router(group_information.router, prefix="/ai/v1")
logger.info("[라우터 등록 완료] group_information 라우터 활성화")


if __name__ == "__main__":
    import uvicorn

    logger.info("[FastAPI 실행] 서버 시작 전 초기화")  # milestone: 서버 진입 지점
    try:
        port = 8000
        uvicorn.run(app, host="0.0.0.0", port=port)
        logger.info("[FastAPI 실행 완료] 서버가 정상적으로 실행되었습니다.")
    except Exception as e:
        logger.error("[FastAPI 실행 오류] 서버 실행 중 예외 발생", exc_info=True)

