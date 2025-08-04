import logging
import os
import requests
from pathlib import Path
from src.config import WEBHOOK_URL, DISCORD_ENABLED, DISCORD_LOG_LEVEL
# from google.cloud import logging as gcp_logging
# from google.cloud.logging_v2.handlers import CloudLoggingHandler
# from google.oauth2 import service_account

DISCORD_WEBHOOK_URL = WEBHOOK_URL

def send_to_discord(message: str):
    """Send message to Discord webhook if enabled"""
    if not DISCORD_ENABLED:
        return
        
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        if response.status_code != 204:
            print(f"[AI 로거] Discord 전송 실패: status={response.status_code}, response={response.text}")
    except Exception as e:
        print(f"[AI 로거] Discord 예외 발생: {e}")

class DiscordHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.enabled = DISCORD_ENABLED
        
    def emit(self, record: logging.LogRecord) -> None:
        # Skip if Discord is disabled
        if not self.enabled:
            return
            
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
                "[Client Error]",
                "[질문 전체 응답 수신 완료]",
                "[원본 응답]:",
                "[정리된 응답]:",
                "[옵션 파싱 시작]",
                "[vLLM 첫 chunk 수신]",
                "[추천 vLLM 첫 chunk 수신]",
                "[청크 처리]",
                "[청크 정리]",
                "[접두어",
                "[일반 스트리밍",
                "[옵션 파싱 성공",
                "[JSON 패턴 매치]",
                "[추천 청크 처리]"
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
        stream_handler.setLevel(logging.DEBUG) #Change to Debug if you want to see more logs in the console.
        stream_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(stream_handler)

        # Discord 핸들러 (조건부 추가)
        if DISCORD_ENABLED:
            try:
                # Convert string log level to logging constant
                discord_level = getattr(logging, DISCORD_LOG_LEVEL, logging.WARNING)
                
                discord_handler = DiscordHandler()
                discord_handler.setLevel(discord_level)
                discord_handler.setFormatter(logging.Formatter("[AI] %(asctime)s %(levelname)s: %(message)s"))
                logger.addHandler(discord_handler)
                
                print(f"[AI 로거] Discord 핸들러 활성화됨 (레벨: {DISCORD_LOG_LEVEL})")
            except Exception as e:
                print(f"[AI 로거] Discord 핸들러 설정 실패: {e}")
        else:
            print("[AI 로거] Discord 핸들러 비활성화됨")

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

def toggle_discord_handler(enabled: bool):
    """Runtime toggle for Discord handler (useful for debugging)"""
    logger = logging.getLogger("ai")
    
    # Find and update Discord handler
    for handler in logger.handlers:
        if isinstance(handler, DiscordHandler):
            handler.enabled = enabled
            print(f"[AI 로거] Discord 핸들러 {'활성화' if enabled else '비활성화'}됨")
            return
    
    if enabled and DISCORD_ENABLED:
        print("[AI 로거] Discord 핸들러가 없습니다. get_ai_logger()를 먼저 호출하세요.")

if __name__ == "__main__":
    logger = get_ai_logger()
    print("logger level:", logger.level)
    print(f"Discord enabled: {DISCORD_ENABLED}")
    print(f"Discord log level: {DISCORD_LOG_LEVEL}")

    logger.warning("[예외 처리] 테스트 케이스")  # Discord에는 안 가야 함
    logger.warning("[Quota Error] 429 Too Many Requests")  # Discord 전송됨 (if enabled)
    logger.warning("[Client Error] /favicon.ico - 404")  # Discord 차단됨

    logger.debug("디버그 테스트")  # 콘솔 X, Discord X
    logger.info("정보 메시지")  # 콘솔 O, Discord X
    logger.warning("경고 발생!")  # 콘솔 O, Discord O (if enabled)
    logger.error("에러 발생!")  # 콘솔 O, Discord O (if enabled)
    
    # Runtime toggle test
    print("\n=== Runtime Toggle Test ===")
    toggle_discord_handler(False)
    logger.error("비활성화된 Discord 테스트")
    
    toggle_discord_handler(True)
    logger.error("재활성화된 Discord 테스트")
