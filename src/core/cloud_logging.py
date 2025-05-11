import logging
import sys
import os
import json
from datetime import datetime, UTC
from google.oauth2 import service_account
from google.cloud import logging as gcp_logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from src.config import CREDENTIAL_PATH

# JSON 구조 콘솔 출력 포맷터
class CloudLoggingFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# 로거 설정 함수
def setup_logger() -> logging.Logger:
    logger = logging.getLogger("cloud")

    # .env에서 LOG_LEVEL 불러오기 (기본: INFO)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(log_level)

    # 중복 핸들러 제거
    if logger.hasHandlers():
        logger.handlers.clear()

    # 1. 콘솔 핸들러 (개발 시 디버깅용)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(CloudLoggingFormatter())
    logger.addHandler(stream_handler)

    # 2. GCP Cloud Logging 핸들러 (운영용)
    try:
        credentials = service_account.Credentials.from_service_account_file(CREDENTIAL_PATH)
        client = gcp_logging.Client(credentials=credentials)
        cloud_handler = CloudLoggingHandler(client)
        cloud_handler.setLevel(logging.INFO)
        logger.addHandler(cloud_handler)

        logger.info("[로깅 초기화] GCP Cloud Logging 핸들러 적용 완료")

    except Exception as e:
        logger.warning(f"[로깅 초기화] GCP 핸들러 설정 실패: {e}")

    return logger

# 외부에서 사용할 전역 로거 인스턴스
logger = setup_logger()
