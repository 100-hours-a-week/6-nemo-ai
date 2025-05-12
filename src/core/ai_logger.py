import logging
import requests
from src.config import WEBHOOK_URL
# from google.cloud import logging as gcp_logging
# from google.cloud.logging_v2.handlers import CloudLoggingHandler
# from google.oauth2 import service_account

DISCORD_WEBHOOK_URL = WEBHOOK_URL

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
        # ✅ 콘솔 핸들러 (INFO 이상)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(stream_handler)

        # ✅ Discord 핸들러 (WARNING 이상)
        discord_handler = DiscordHandler()
        discord_handler.setLevel(logging.WARNING)
        discord_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(discord_handler)

        # ✅ 로거 레벨은 DEBUG로 설정 (모든 로그 수용 가능하게)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

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

    return logger

if __name__ == "__main__":
    logger = get_ai_logger()

    logger.debug("디버그 테스트")  # 콘솔 X, Discord X
    logger.info("정보 메시지")  # 콘솔 O, Discord X
    logger.warning("경고 발생!")  # 콘솔 O, Discord O
    logger.error("에러 발생!")  # 콘솔 O, Discord O
