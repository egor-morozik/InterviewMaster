from fastapi import FastAPI

from app.api.endpoints import core


app = FastAPI(title="InterviewMaster API")


app.include_router(core.router, prefix="/core", tags=["core"])
