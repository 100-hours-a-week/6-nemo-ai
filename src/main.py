from fastapi import FastAPI
from src.config import *
from router.v1 import tag
app = FastAPI()
app.include_router(tag.router)


if __name__ == "__main__":
    import nest_asyncio
    from pyngrok import ngrok
    import uvicorn
    # ✅ ngrok 초기화
    ngrok.kill()
    nest_asyncio.apply()
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)

    # ✅ 포트 연결 및 공개 주소 획득
    port = 8000
    public_url = ngrok.connect(port, bind_tls=True)
    print(f"🚀 ngrok 공개 주소: {public_url}")
    print(f"📘 Swagger UI: {public_url}/docs")

    # ✅ FastAPI 실행
    uvicorn.run(app, host="0.0.0.0", port=port)