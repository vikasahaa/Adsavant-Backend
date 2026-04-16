"""
API Routes — prediction and scenario comparison endpoints.
"""

import logging
import cv2
import numpy as np
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from PIL import Image
from app.api.schemas import VisualMetricsResponse, VisualMetrics, ColorInfo
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


@router.post("/visual-metrics", response_model=VisualMetricsResponse, tags=["Visual Insights"])
async def get_visual_metrics(file: UploadFile = File(...)):
    """
    Computes purely mathematical visual metrics from an uploaded image.
    Strictly uses OpenCV/NumPy without any Machine Learning models.
    """
    # 1. Validate it's an image using your existing settings
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type. Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}",
        )

    try:
        # 2. Read the image file into memory for OpenCV
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image.")

        # Convert to Grayscale for mathematical analysis
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 3. Calculate Metrics (Normalized to 0-100)
        # Lighting: Mean intensity (0-255)
        mean_intensity = cv2.mean(gray)[0]
        lighting_quality = (mean_intensity / 255.0) * 100

        # Contrast: Standard Deviation (Max realistic ~127.5)
        std_dev = cv2.meanStdDev(gray)[1][0][0]
        contrast_score = min((std_dev / 128.0) * 100, 100.0)

        # Focus/Sharpness: Laplacian Variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_threshold = 500.0  # Threshold to cap at 100%
        focus_score = min((laplacian_var / sharpness_threshold) * 100, 100.0)

        # Composite Score
        visual_quality = (lighting_quality + contrast_score + focus_score) / 3.0

        # ---------------------------------------------------------
        # NEW: Mathematical Dominant Color Extraction
        # ---------------------------------------------------------
        # Shrink image to speed up math, then flatten to a list of RGB pixels
        small_img = cv2.resize(img, (100, 100))
        # Convert BGR (OpenCV default) to RGB for accurate web hex codes
        rgb_img = cv2.cvtColor(small_img, cv2.COLOR_BGR2RGB)
        pixels = np.float32(rgb_img.reshape(-1, 3))

        # Perform mathematical clustering (Vector Quantization) to find top 3 colors
        n_colors = 3
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 0.1)
        _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        # Calculate percentages
        _, counts = np.unique(labels, return_counts=True)

        dominant_colors = []
        for i in range(n_colors):
            # Convert RGB tuple to Hex String
            r, g, b = palette[i]
            hex_color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            pct = (counts[i] / sum(counts)) * 100
            dominant_colors.append(ColorInfo(hex_code=hex_color, percentage=round(pct, 1)))

        # Sort so the highest percentage is first
        dominant_colors = sorted(dominant_colors, key=lambda x: x.percentage, reverse=True)

        return {
            "metrics": {
                "lighting_quality": round(lighting_quality, 2),
                "colour_contrast": round(contrast_score, 2),
                "subject_focus": round(focus_score, 2),
                "visual_quality_composite": round(visual_quality, 2),
                "dominant_colors": dominant_colors
            }
        }

    except Exception as e:
        logger.exception("Visual metrics calculation failed")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


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
