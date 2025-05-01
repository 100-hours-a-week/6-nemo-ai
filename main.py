from fastapi import FastAPI
from router.v1 import groups
from router.v2 import persona, recommend
from router.v3 import search

app = FastAPI()

app.include_router(groups.router, prefix="/api/v1")
app.include_router(persona.router, prefix="/api/v2")
app.include_router(recommend.router, prefix="/api/v2")
app.include_router(search.router, prefix="/api/v3")

