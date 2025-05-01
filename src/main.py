from fastapi import FastAPI
from router.v1 import chroma_routes

app = FastAPI()
app.include_router(chroma_routes.router)
