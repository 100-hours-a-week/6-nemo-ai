from fastapi import FastAPI
from router.v1 import groups

app = FastAPI()

app.include_router(groups.router)


