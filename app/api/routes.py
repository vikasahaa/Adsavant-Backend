"""
API Routes — prediction and scenario comparison endpoints.
"""

import logging
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from PIL import Image

from app.api.schemas import (
    BrandType,
    ConfidenceLevel,
    EngagementClass,
    PredictionResponse,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    ScenarioResult,
)
from app.core.config import settings

router = APIRouter(tags=["Predictions"])
logger = logging.getLogger(__name__)


async def _read_image(file: Optional[UploadFile]) -> Optional[Image.Image]:
    """Validate and load an uploaded image file."""
    if file is None:
        return None

    # Validate content type
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. "
            f"Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}",
        )

    # Validate file size
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large ({size_mb:.1f}MB). Max: {settings.MAX_IMAGE_SIZE_MB}MB",
        )

    try:
        image = Image.open(BytesIO(contents)).convert("RGB")
        return image
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not process image: {str(e)}",
        )


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Predict engagement for a single post",
    description=(
        "Upload an Instagram campaign image and caption to receive "
        "predicted engagement rate, classification, and confidence."
    ),
)
async def predict_engagement(
    request: Request,
    caption: str = Form(
        ...,
        description="Instagram post caption",
        examples=["New summer collection dropping tomorrow! Link in bio 🔥"],
    ),
    brand_type: BrandType = Form(
        ...,
        description="Brand category",
    ),
    followers: int = Form(
        ...,
        gt=0,
        description="Follower count",
    ),
    image: Optional[UploadFile] = File(
        None,
        description="Campaign image (JPEG/PNG, max 10MB)",
    ),
):
    """Predict engagement rate for a single Instagram post."""
    model_service = request.app.state.model_service
    if not model_service.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded yet.")

    pil_image = await _read_image(image)

    try:
        result = model_service.predict(
            caption=caption,
            brand_type=brand_type.value,
            followers=followers,
            image=pil_image,
        )
    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error: {str(e)}",
        )

    return PredictionResponse(
        predicted_engagement_rate=result["predicted_engagement_rate"],
        regression_classification=EngagementClass(result["regression_classification"]),
        direct_classification=EngagementClass(result["direct_classification"]),
        confidence=ConfidenceLevel(result["confidence"]),
        feature_summary=result["feature_summary"],
    )


@router.post(
    "/compare",
    response_model=ScenarioComparisonResponse,
    summary="Compare multiple post scenarios",
    description=(
        "Submit 2-5 caption/brand/follower scenarios to compare "
        "their predicted engagement rates side by side."
    ),
)
async def compare_scenarios(
    request: Request,
    body: ScenarioComparisonRequest,
):
    """What-if scenario comparison — no images (text + metadata only)."""
    model_service = request.app.state.model_service
    if not model_service.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded yet.")

    results = []
    for scenario in body.scenarios:
        try:
            pred = model_service.predict(
                caption=scenario.caption,
                brand_type=scenario.brand_type.value,
                followers=scenario.followers,
                image=None,
            )
            results.append(
                ScenarioResult(
                    label=scenario.label,
                    predicted_er=pred["predicted_engagement_rate"],
                    classification=EngagementClass(pred["regression_classification"]),
                    confidence=ConfidenceLevel(pred["confidence"]),
                )
            )
        except Exception as e:
            logger.exception(f"Scenario '{scenario.label}' failed")
            raise HTTPException(
                status_code=500,
                detail=f"Prediction failed for scenario '{scenario.label}': {str(e)}",
            )

    # Compute relative differences against the best
    best_result = max(results, key=lambda r: r.predicted_er)
    for r in results:
        if r.label != best_result.label:
            diff = (
                (r.predicted_er - best_result.predicted_er)
                / best_result.predicted_er
                * 100
            )
            r.relative_difference = f"{diff:+.1f}% vs best"
        else:
            r.relative_difference = "Best"

    return ScenarioComparisonResponse(
        results=results,
        best_scenario=best_result.label,
    )
