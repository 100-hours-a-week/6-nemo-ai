# import sentry_sdk
# from src.config import SENTRY_DSN, SENTRY_ENVIRONMENT
# from sentry_sdk.integrations.fastapi import FastApiIntegration
#
#
# def init_sentry():
#     if not SENTRY_DSN:
#         return  # DSN이 없으면 초기화 안 함
#
#     sentry_sdk.init(
#         dsn=SENTRY_DSN,
#         environment=SENTRY_ENVIRONMENT,
#         integrations=[FastApiIntegration()],
#         send_default_pii=True,  # 사용자 정보 등 포함
#         traces_sample_rate=1.0  # 퍼포먼스 추적
#     )