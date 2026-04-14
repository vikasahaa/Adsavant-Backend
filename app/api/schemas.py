"""
Pydantic schemas for API request/response validation.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BrandType(str, Enum):
    """Supported brand categories."""

    SPORTS_WEAR = "sports wear"
    CASUAL_WEAR = "casual wear"
    ETHNIC_WEAR = "ethnic wear"


class EngagementClass(str, Enum):
    """Engagement classification tiers."""

    HIGH = "High"
    AVERAGE = "Average"
    LOW = "Low"


class ConfidenceLevel(str, Enum):
    """Prediction confidence levels."""

    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"


class PredictionRequest(BaseModel):
    """Schema for engagement prediction input (JSON fields alongside file upload)."""

    caption: str = Field(
        ...,
        description="Instagram post caption text (supports emojis)",
        examples=["New summer collection dropping tomorrow! Link in bio 🔥"],
    )
    brand_type: BrandType = Field(
        ...,
        description="Type of fashion brand",
    )
    followers: int = Field(
        ...,
        gt=0,
        description="Brand's Instagram follower count",
        examples=[50000],
    )


class PredictionResponse(BaseModel):
    """Schema for engagement prediction output."""

    predicted_engagement_rate: float = Field(
        ...,
        description="Predicted engagement rate as a percentage",
        examples=[2.45],
    )
    regression_classification: EngagementClass = Field(
        ...,
        description="Classification derived from the predicted ER value",
    )
    direct_classification: EngagementClass = Field(
        ...,
        description="Classification from the dedicated classifier head",
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Prediction confidence based on similarity to training data",
    )
    feature_summary: dict = Field(
        default_factory=dict,
        description="Summary of extracted features for transparency",
    )


class ScenarioItem(BaseModel):
    """Single scenario in a comparison."""

    label: str = Field(..., description="User-defined label for this scenario")
    caption: str
    brand_type: BrandType
    followers: int = Field(..., gt=0)


class ScenarioComparisonRequest(BaseModel):
    """Request for comparing multiple post scenarios."""

    scenarios: list[ScenarioItem] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="List of scenarios to compare (2-5)",
    )


class ScenarioResult(BaseModel):
    """Result for a single scenario."""

    label: str
    predicted_er: float
    classification: EngagementClass
    confidence: ConfidenceLevel
    relative_difference: Optional[str] = None


class ScenarioComparisonResponse(BaseModel):
    """Response containing comparison results."""

    results: list[ScenarioResult]
    best_scenario: str = Field(..., description="Label of the highest-ER scenario")


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: Optional[str] = None
