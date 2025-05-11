from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from time import time
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

class AILoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/ai/v1/"):
            start_time = time()
            response: Response = await call_next(request)
            process_time = time() - start_time

            ai_logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")

            if 400 <= response.status_code < 500:
                ai_logger.warning(f"[Client Error] {request.method} {request.url.path} - {response.status_code}")
            elif response.status_code >= 500:
                ai_logger.error(f"[Server Error] {request.method} {request.url.path} - {response.status_code}")

            return response
        else:
            return await call_next(request)
