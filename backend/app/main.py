import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .api.routes import router  # noqa: E402

app = FastAPI(
    title="Hybrid B2B Opportunity Prioritization",
    description="Calibrated ML scoring with grounded GenAI explanations",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")
    if origin.strip()
]
allowed_origin_regex = os.getenv(
    "CORS_ALLOWED_ORIGIN_REGEX",
    r"^https://genai-lead-scoring-agent(?:-[a-z0-9-]+)?\.vercel\.app$",
).strip() or None
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Hybrid B2B Opportunity Prioritization API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
