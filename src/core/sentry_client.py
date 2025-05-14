# src/core/sentry_client.py
import sentry_sdk
from src.config import SENTRY_DSN

def init_sentry():
    if not SENTRY_DSN:
        return  # DSN이 없으면 초기화 안 함

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        environment='local',  # ex: "production", "local", "dev"
    )