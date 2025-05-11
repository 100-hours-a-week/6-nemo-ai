import logging
import requests
from google.cloud import logging as gcp_logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from google.oauth2 import service_account
from src.config import CREDENTIAL_PATH, WEBHOOK_URL

DISCORD_WEBHOOK_URL = WEBHOOK_URL  # 여기에 본인 Webhook 넣기

def send_to_discord(message: str):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    except Exception as e:
        print(f"[AI 로거] Discord 전송 실패: {e}")

class DiscordHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if record.levelno >= logging.WARNING:
                send_to_discord(f"[AI LOG] {msg}")
        except Exception:
            pass  # 실패해도 앱 동작엔 영향 없음

def get_ai_logger() -> logging.Logger:
    logger = logging.getLogger("ai")

    if not logger.handlers:
        # 1. GCP 로깅 핸들러
        credentials = service_account.Credentials.from_service_account_file(CREDENTIAL_PATH)
        client = gcp_logging.Client(credentials=credentials)
        cloud_handler = CloudLoggingHandler(client)
        cloud_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(cloud_handler)

        # 2. 콘솔 출력
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(stream_handler)

        # 3. Discord 핸들러 추가
        discord_handler = DiscordHandler()
        discord_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(discord_handler)

        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
