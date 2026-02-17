from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import get_settings
from app.api.routes import router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - ensure directories exist
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown


app = FastAPI(
    title="PDF AI Suite API",
    description="AI-powered PDF and document extraction - tables, text, images, structure",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# Serve extracted images
if settings.output_dir.exists():
    app.mount("/outputs", StaticFiles(directory=str(settings.output_dir)), name="outputs")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "pdf-ai-suite"}
