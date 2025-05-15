import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

class AILoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response: Response = await call_next(request)
        process_time = round(time.time() - start_time, 4)

        method = request.method
        path = request.url.path
        status_code = response.status_code

        # 성공 로그
        if status_code < 400:
            ai_logger.info(f"[AI] {method} {path} - {status_code} - {process_time}s")
        # 클라이언트 에러이지만 422는 제외 (중복 방지)
        elif 400 <= status_code < 500 and status_code != 422:
            ai_logger.warning(f"[Client Error] {method} {path} - {status_code}")
        # 서버 에러
        elif status_code >= 500:
            ai_logger.error(f"[Server Error] {method} {path} - {status_code}")

        return response
