import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db
from app.db.seed import seed_doctors
from app.routes import appointments, livekit_routes, summary

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_doctors()
    yield


app = FastAPI(
    title="Hospital AI Voice Booking API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(livekit_routes.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(summary.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Hospital AI Voice Booking"}
