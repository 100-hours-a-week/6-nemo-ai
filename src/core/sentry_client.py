from src.config import SENTRY_DSN, SENTRY_PROFILE_LIFETIME, SENTRY_PROFILE_SAMPLE_RATE, SENTRY_RELEASE, SENTRY_ENV, SENTRY_SAMPLE_RATE
from sentry_sdk.integrations.fastapi import FastApiIntegration
import sentry_sdk

def init_sentry():
    if not SENTRY_DSN:
        return
    sentry_sdk.init(
        dsn= SENTRY_DSN,
        environment= SENTRY_ENV,
        integrations=[FastApiIntegration()],
        release= SENTRY_RELEASE,
        traces_sample_rate= SENTRY_SAMPLE_RATE,
        profile_session_sample_rate=SENTRY_PROFILE_SAMPLE_RATE,
        profile_lifecycle=SENTRY_PROFILE_LIFETIME,
    )