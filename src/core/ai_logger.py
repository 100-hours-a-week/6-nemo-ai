# src/core/logger_ai.py
import logging
from google.cloud import logging as gcp_logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from google.oauth2 import service_account
from src.config import CREDENTIAL_PATH

def get_ai_logger() -> logging.Logger:
    logger = logging.getLogger("ai")

    if not logger.handlers:
        try:
            # ✅ vertex_client와 동일한 인증 방식 사용
            credentials = service_account.Credentials.from_service_account_file(CREDENTIAL_PATH)
            client = gcp_logging.Client(credentials=credentials)

            cloud_handler = CloudLoggingHandler(client)
            cloud_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
            logger.addHandler(cloud_handler)

            print("[AI 로거] GCP Cloud Logging 연동 완료")
        except Exception as e:
            print("[AI 로거] GCP 연동 실패 - 콘솔로만 출력됩니다:", e)

        # ✅ 콘솔 핸들러는 항상 추가
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(stream_handler)

        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
