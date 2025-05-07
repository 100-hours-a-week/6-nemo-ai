from fastapi import FastAPI
from router.v1 import tag_extraction, group_writer, vector_db, group_information
from src.config import *
import logging
logging.getLogger("pyngrok").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
app = FastAPI()
@app.get("/")
def root():
    return {"message": "Hello World: Version 1 API is running"}

# app.include_router(chroma_routes.router, prefix="/ai/v1")
# app.include_router(tag_extraction.router, prefix="/ai/v1")
# app.include_router(group_writer.router, prefix="/ai/v1")
app.include_router(group_information.router, prefix="/ai/v1")


if __name__ == "__main__":
    import nest_asyncio
    from pyngrok import ngrok
    import uvicorn
    # ngrok 초기화
    ngrok.kill()
    nest_asyncio.apply()
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)

    # 포트 연결 및 공개 주소 획득
    port = 8000
    public_url = ngrok.connect(port, bind_tls=True)
    print(f"ngrok 공개 주소: {public_url}")
    print(f"Swagger UI: {public_url}/docs")

    # FastAPI 실행
    uvicorn.run(app, host="0.0.0.0", port=port)