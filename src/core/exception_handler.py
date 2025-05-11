from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        default_messages = {
            400: "잘못된 요청입니다.",
            409: "이미 존재하는 리소스입니다.",
            429: "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
            503: "일시적으로 서비스를 사용할 수 없습니다.",
        }

        if exc.status_code == 422:
            message = str(exc.detail)
        else:
            message = default_messages.get(exc.status_code, str(exc.detail))

        ai_logger.warning("[AI] [예외 처리] HTTP 예외 발생", extra={
            "status_code": exc.status_code,
            "detail": str(exc.detail),
            "path": request.url.path
        })

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": message,
                "data": None
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        ai_logger.warning("[AI] [예외 처리] Request Validation 예외 발생", extra={
            "errors": exc.errors(),
            "path": request.url.path
        })

        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": "요청 형식이 잘못되었습니다. 필수 입력값을 확인해주세요.", "data": None},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        ai_logger.exception("[AI] [예외 처리] 알 수 없는 서버 예외 발생", extra={
            "path": request.url.path
        })

        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "서버 내부 오류 발생", "data": None},
        )