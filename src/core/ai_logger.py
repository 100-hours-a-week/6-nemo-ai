import logging
import requests
# from google.cloud import logging as gcp_logging
# from google.cloud.logging_v2.handlers import CloudLoggingHandler
# from google.oauth2 import service_account
from src.config import WEBHOOK_URL

DISCORD_WEBHOOK_URL = WEBHOOK_URL  # 여기에 본인 Webhook 넣기

def send_to_discord(message: str):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    except Exception as e:
        print(f"[AI 로거] Discord 전송 실패: {e}")

class DiscordHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno >= logging.WARNING:
                msg = self.format(record)
                send_to_discord(f"[AI LOG] {msg}")
        except Exception:
            pass

def get_ai_logger() -> logging.Logger:
    logger = logging.getLogger("ai")

    if not logger.handlers:
        # ✅ 콘솔 핸들러
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(stream_handler)

        # ✅ Discord 핸들러
        discord_handler = DiscordHandler()
        discord_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(discord_handler)

        # ✅ Cloud Logging (보존됨)
        # try:
        #     credentials = service_account.Credentials.from_service_account_file(CREDENTIAL_PATH)
        #     client = gcp_logging.Client(credentials=credentials)
        #     cloud_handler = CloudLoggingHandler(client)
        #     cloud_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        #     logger.addHandler(cloud_handler)
        #     print("[AI 로거] GCP Cloud Logging 연동 완료")
        # except Exception as e:
        #     print("[AI 로거] GCP Cloud Logging 연동 실패:", e)

        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger