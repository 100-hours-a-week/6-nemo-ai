import logging
import os
import requests
from src.config import WEBHOOK_URL
from pathlib import Path
# from google.cloud import logging as gcp_logging
# from google.cloud.logging_v2.handlers import CloudLoggingHandler
# from google.oauth2 import service_account

DISCORD_WEBHOOK_URL = WEBHOOK_URL

def send_to_discord(message: str):
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        if response.status_code != 204:
            print(f"[AI 로거] Discord 전송 실패: status={response.status_code}, response={response.text}")
    except Exception as e:
        print(f"[AI 로거] Discord 예외 발생: {e}")

class DiscordHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            # print("emit called")
            record_path = Path(record.pathname).resolve()
            src_root = Path(__file__).resolve().parent.parent  # → /.../src

            # print("record path:", record_path)
            # print("src root:", src_root)

            # src 내부에서 발생한 로그만 Discord로 전송
            if src_root not in record_path.parents:
                # print("필터됨 (src 외 경로)")
                return

            msg = self.format(record)
            # print("메시지:", msg)

            # 필터링할 내용
            blocked_keywords = [
                "[예외 처리]",
                "favicon.ico",
                "/docs",
                "[Moderation 평가]",
                "[유해성 차단]",
                "[Client Error]"
            ]
            if any(block in msg for block in blocked_keywords):
                # print("필터됨 (내용 조건)")
                return

            # print("Discord 전송 시도 중...")
            send_to_discord(f"[AI LOG] {msg}")
        except Exception as e:
            print(f"[emit 에러]: {e}")

def get_ai_logger() -> logging.Logger:
    logger = logging.getLogger("ai")

    if not logger.handlers:
        # 콘솔 핸들러 (INFO 이상)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.WARNING) #Change to Debug if you want to see more logs in the console.
        stream_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(stream_handler)

        # Discord 핸들러 (WARNING 이상)
        discord_handler = DiscordHandler()
        discord_handler.setLevel(logging.WARNING)
        discord_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(discord_handler)

        # 로거 기본 설정
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # GCP Cloud Logging (보존됨)
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
    print("logger level:", logger.level)

    logger.warning("[예외 처리] 테스트 케이스")  # Discord에는 안 가야 함
    logger.warning("[Quota Error] 429 Too Many Requests")  # Discord 전송됨
    logger.warning("[Client Error] /favicon.ico - 404")  # Discord 차단됨

    logger.debug("디버그 테스트")  # 콘솔 X, Discord X
    logger.info("정보 메시지")  # 콘솔 O, Discord X
    logger.warning("경고 발생!")  # 콘솔 O, Discord O
    logger.error("에러 발생!")  # 콘솔 O, Discord O
