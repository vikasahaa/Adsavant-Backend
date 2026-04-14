"""
AdSavant — FastAPI Backend
Serves the ML engagement prediction model as a REST API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.ml.model_service import ModelService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model on startup, release on shutdown."""
    logger.info("Loading ML model artifacts...")
    model_service = ModelService()
    model_service.load(settings.MODEL_PATH)
    app.state.model_service = model_service
    logger.info("Model loaded successfully.")
    yield
    logger.info("Shutting down — releasing model resources.")


app = FastAPI(
    title="AdSavant API",
    description=(
        "Instagram engagement prediction API for Sri Lankan fashion SMEs. "
        "Upload an image and caption to receive predicted engagement rate, "
        "classification, and confidence score."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "model_loaded": hasattr(app.state, "model_service")}
