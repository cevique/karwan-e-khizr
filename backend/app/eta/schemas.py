from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ETAFeatures(BaseModel):
    """Feature vector for ETA prediction.

    This schema is the stable contract between training data generation
    and inference. Both synthetic and real training data must populate
    these same fields.
    """

    route_id: int
    stop_id: int
    time_of_day: str = Field(description="HH:MM format, e.g. '08:00'")
    day_of_week: str = Field(description="Lowercase day name, e.g. 'monday'")
    scheduled_duration_s: int = Field(description="Scheduled trip duration in seconds")
    distance_remaining_m: float = Field(description="Remaining distance to next stop in meters")
    delay_seconds: Optional[int] = Field(default=None, description="Known delay in seconds, if available")


class ETAPrediction(BaseModel):
    """Output from an ETA prediction.

    Returns None when no coverage — never a low-confidence guess.
    """

    predicted_eta_seconds: float
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    provenance: Literal["ml", "deterministic"] = "ml"


class TrainingSample(BaseModel):
    """A single training observation.

    Generated from synthetic simulation data or real vehicle observations.
    The feature schema matches ETAFeatures exactly; the target is
    actual_duration_s (the ground-truth travel time).
    """

    route_id: int
    stop_id: int
    time_of_day: str
    day_of_week: str
    scheduled_duration_s: int
    distance_remaining_m: float
    delay_seconds: Optional[int] = None
    actual_duration_s: float = Field(description="Ground-truth travel time in seconds")
    source: Literal["synthetic", "real"] = "synthetic"
    generated_at: Optional[datetime] = None


class ModelArtifact(BaseModel):
    """Metadata about a trained model artifact."""

    version: str
    trained_at: datetime
    source: Literal["synthetic", "real", "mixed"]
    sample_count: int
    feature_columns: list[str]
    training_mae_seconds: float
    baseline_mae_seconds: float
    lightgbm_model_path: Optional[str] = None
    linear_model_path: Optional[str] = None
