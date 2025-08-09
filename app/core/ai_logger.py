import logging
import requests
from app.config import WEBHOOK_URL, DISCORD_ENABLED, DISCORD_LOG_LEVEL
from pathlib import Path
import uvicorn.logging
import sys
from datetime import datetime

DISCORD_WEBHOOK_URL = WEBHOOK_URL

def send_to_discord(message: str):
    if not DISCORD_ENABLED or not DISCORD_WEBHOOK_URL:
        return
        
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        if response.status_code != 204:
            # Use consistent format for Discord errors
            ai_logger = get_ai_logger()
            ai_logger.error(f"Discord 전송 실패: status={response.status_code}, response={response.text}")
    except Exception as e:
        ai_logger = get_ai_logger()
        ai_logger.error(f"Discord 예외 발생: {e}")

class DiscordHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            record_path = Path(record.pathname).resolve()
            src_root = Path(__file__).resolve().parent.parent  # → /.../src

            # src 내부에서 발생한 로그만 Discord로 전송
            if src_root not in record_path.parents:
                return

            msg = self.format(record)

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
                return

            send_to_discord(f"[AI LOG] {msg}")
        except Exception as e:
            # Use standard AI logger format for emit errors
            ai_logger = get_ai_logger()
            ai_logger.error(f"emit 에러: {e}")

class AIFormatter(logging.Formatter):
    """Custom formatter that ensures all logs follow [AI] timestamp LEVEL: message format"""
    
    def format(self, record):
        # Create timestamp in consistent format
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        
        # Format: [AI] timestamp LEVEL: message
        formatted_message = f"[AI] {timestamp} {record.levelname}: {record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            formatted_message += "\n" + self.formatException(record.exc_info)
            
        return formatted_message

def get_ai_logger() -> logging.Logger:
    logger = logging.getLogger("ai")

    if not logger.handlers:
        # 콘솔 핸들러 (INFO 이상)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG) #Change to Debug if you want to see more logs in the console.
        stream_handler.setFormatter(AIFormatter())
        logger.addHandler(stream_handler)

        # Discord 핸들러 (동적 설정)
        if DISCORD_ENABLED and DISCORD_WEBHOOK_URL:
            discord_handler = DiscordHandler()
            discord_level = getattr(logging, DISCORD_LOG_LEVEL, logging.WARNING)
            discord_handler.setLevel(discord_level)
            discord_handler.setFormatter(AIFormatter())
            logger.addHandler(discord_handler)
            # Use standard format for Discord activation message
            print(f"[AI] {datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} INFO: Discord 핸들러 활성화됨 (레벨: {DISCORD_LOG_LEVEL})")
        else:
            print(f"[AI] {datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} INFO: Discord 핸들러 비활성화됨")

        # 로거 기본 설정
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

    return logger

def setup_uvicorn_logging():
    """Configure uvicorn to keep its original format for server startup messages"""
    # Keep uvicorn's original logging format for server startup messages
    # We'll only standardize our application logs, not uvicorn's system messages
    pass

def setup_third_party_logging():
    """Configure third-party libraries to use AI logger format or stay silent"""
    # Libraries that should use AI format
    ai_format_loggers = [
        "telemetry",
        "application"
    ]
    
    # Libraries that should stay silent
    silent_loggers = [
        "chromadb",
        "aiokafka", "aiokafka.consumer", "aiokafka.producer", "aiokafka.client",
        "aiokafka.cluster", "aiokafka.coordinator", "aiokafka.coordinator.consumer",
        "aiokafka.coordinator.group", "aiokafka.coordinator.assignors",
        "aiokafka.protocol", "aiokafka.errors", "aiokafka.heartbeat",
        "kafka", "kafka.cluster", "kafka.protocol", "kafka.consumer", 
        "kafka.producer", "kafka.coordinator", "kafka.client", "kafka.errors",
        "kafka.conn", "kafka.metrics"
    ]
    
    # Apply AI format to specified loggers
    for logger_name in ai_format_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(AIFormatter())
        logger.addHandler(console_handler)
        logger.propagate = False
    
    # Silence specified loggers
    for logger_name in silent_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL + 1)
        logger.propagate = False
        logger.disabled = True

def toggle_discord_handler(enabled: bool = None) -> bool:
    """Discord 핸들러 동적 토글"""
    logger = logging.getLogger("ai")
    
    # Discord 핸들러 찾기
    discord_handlers = [h for h in logger.handlers if isinstance(h, DiscordHandler)]
    
    if enabled is None:
        # 현재 상태 토글
        enabled = len(discord_handlers) == 0
    
    if enabled and not discord_handlers and DISCORD_WEBHOOK_URL:
        # Discord 핸들러 추가
        discord_handler = DiscordHandler()
        discord_level = getattr(logging, DISCORD_LOG_LEVEL, logging.WARNING)
        discord_handler.setLevel(discord_level)
        discord_handler.setFormatter(AIFormatter())
        logger.addHandler(discord_handler)
        ai_logger = get_ai_logger()
        ai_logger.info(f"Discord 핸들러 활성화됨 (레벨: {DISCORD_LOG_LEVEL})")
        return True
    elif not enabled and discord_handlers:
        # Discord 핸들러 제거
        for handler in discord_handlers:
            logger.removeHandler(handler)
        ai_logger = get_ai_logger()
        ai_logger.info("Discord 핸들러 비활성화됨")
        return False
    
    return len([h for h in logger.handlers if isinstance(h, DiscordHandler)]) > 0

# Initialize all logging configurations
def initialize_logging():
    """Initialize all logging configurations consistently"""
    setup_third_party_logging()
    return get_ai_logger()

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
    
    # Discord 핸들러 토글 테스트
    print(f"현재 Discord 상태: {toggle_discord_handler()}")
    toggle_discord_handler(False)
    logger.warning("비활성화된 상태의 경고")  # Discord로 가지 않아야 함
    toggle_discord_handler(True)
    logger.warning("다시 활성화된 상태의 경고")  # Discord로 가야 함
