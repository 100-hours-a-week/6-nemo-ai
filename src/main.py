from fastapi import FastAPI
from router.v1 import tag_extraction, group_writer, group_information, vector_db
from src.config import *
import logging
import src.core.vertex_client

# 로깅 설정
logging.getLogger("chromadb").setLevel(logging.WARNING)

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World: Version 1 API is running"}

#정상 작동
# app.include_router(vector_db.router, prefix="/ai/v1")
# app.include_router(tag_extraction.router, prefix="/ai/v1")
# app.include_router(group_writer.router, prefix="/ai/v1")
app.include_router(group_information.router, prefix="/ai/v1")


if __name__ == "__main__":
    # import nest_asyncio
    # from pyngrok import ngrok
    import uvicorn
    # # ngrok 초기화
    # ngrok.kill()
    # nest_asyncio.apply()
    # ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    #
    # # 포트 연결 및 공개 주소 획득
    port = 8000
    # public_url = ngrok.connect(port, bind_tls=True)
    # print(f"ngrok 공개 주소: {public_url}")
    # print(f"Swagger UI: {public_url}/docs")

    # FastAPI 실행
    uvicorn.run(app, host="0.0.0.0", port=port)

    #예시
    """
    {
    "name": "토익 스터디 모임",
    "goal": "이 모임은 멍청한 사람들 모아놓고 얼마나 비효율적인지 관찰하려고 만든 겁니다. 괜히 시간 낭비하지 마시고, 본인 해당되면 그냥 나오세요. 수준 낮은 애들끼리 노는 거예요.",
    "category": "학습/자기계발",
    "period": "6개월",
    "isPlanCreated": false
    }
    """