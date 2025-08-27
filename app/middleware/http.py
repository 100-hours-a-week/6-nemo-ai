from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

async def log_requests(request: Request, call_next):
    ai_logger.debug(f"Incoming {request.method} request to {request.url.path}")
    ai_logger.debug(f"Headers: {dict(request.headers)}")

    body = await request.body()
    ai_logger.debug(f"Body: {body.decode('utf-8', errors='ignore')}")

    response = await call_next(request)
    return response

class LogRequestsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ai_logger.debug(f"Incoming {request.method} request to {request.url.path}")
        ai_logger.debug(f"Headers: {dict(request.headers)}")

        body = await request.body()
        ai_logger.debug(f"Body: {body.decode('utf-8', errors='ignore')}")

        # Capture the response
        response = await call_next(request)

        # Read the response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        # Log the response body
        ai_logger.debug(f"Response body: {response_body.decode('utf-8', errors='ignore')}")

        # Rebuild the response to return
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
