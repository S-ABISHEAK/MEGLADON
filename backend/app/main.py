from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.api import jobs, websocket, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(websocket.router)
app.include_router(system.router)

# Serve job artifacts (frames, keyframes, models, etc.) statically for the frontend/viewer.
settings.JOBS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/jobs", StaticFiles(directory=str(settings.JOBS_DIR)), name="jobs")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
