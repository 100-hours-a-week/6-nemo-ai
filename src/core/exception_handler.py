from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # 기본 메시지 설정
        default_messages = {
            400: "잘못된 요청입니다.",
            409: "이미 존재하는 리소스입니다.",
            429: "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
            503: "일시적으로 서비스를 사용할 수 없습니다.",
        }

        # 422일 경우 exc.detail을 그대로 사용
        if exc.status_code == 422:
            message = str(exc.detail)
        else:
            message = default_messages.get(exc.status_code, str(exc.detail))

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": message,
                "data": None
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": "요청 형식이 잘못되었습니다. 필수 입력값을 확인해주세요.", "data": None},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "서버 내부 오류 발생", "data": None},
        )
