from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol

import numpy as np
import structlog

from app.eta.model import (
    FEATURE_COLUMNS,
    DAY_ENCODING,
    _encode_time_of_day,
    load_model,
)
from app.eta.schemas import ETAFeatures, ETAPrediction

logger = structlog.get_logger(__name__)


class ETAPredictor(Protocol):
    """Protocol for ETA prediction providers.

    Implementations must return None when they have no coverage for the
    given features — never a low-confidence guess.
    """

    def predict(self, features: ETAFeatures) -> Optional[ETAPrediction]:
        """Predict ETA for the given features.

        Returns None if no coverage — never a low-confidence guess.
        """
        ...

    @property
    def is_available(self) -> bool:
        """Whether the predictor has a loaded model and can make predictions."""
        ...

    @property
    def model_version(self) -> Optional[str]:
        """Version of the loaded model, if any."""
        ...


class LocalETAPredictor:
    """Local in-process ETA predictor using trained model artifacts.

    Loads a pre-trained model (LightGBM preferred, LinearRegression fallback)
    and serves predictions locally without any cloud ML infrastructure.

    Architecture:
        ML ETA OR deterministic ETA fallback

    When no model is loaded or the model cannot cover the requested features,
    predict() returns None so the caller can fall back to deterministic ETA.
    """

    def __init__(
        self,
        model_dir: Optional[Path] = None,
        version: str = "v1",
        confidence_threshold: float = 0.3,
    ):
        self._model_dir = model_dir
        self._version = version
        self._confidence_threshold = confidence_threshold
        self._lgb_model = None
        self._linear_model = None
        self._metadata: dict = {}
        self._load_attempted = False

    def _ensure_loaded(self) -> None:
        """Lazy-load model on first prediction attempt."""
        if self._load_attempted:
            return
        self._load_attempted = True

        result = load_model(self._model_dir, self._version)
        if result is None:
            logger.info("no_model_found", version=self._version)
            return

        self._lgb_model, self._linear_model, self._metadata = result
        logger.info(
            "model_loaded",
            version=self._metadata.get("version", self._version),
            has_lightgbm=self._lgb_model is not None,
            has_linear=self._linear_model is not None,
        )

    def _features_to_array(self, features: ETAFeatures) -> np.ndarray:
        """Convert ETAFeatures to numpy array for model prediction."""
        row = [
            features.route_id,
            features.stop_id,
            _encode_time_of_day(features.time_of_day),
            DAY_ENCODING.get(features.day_of_week, 0),
            features.scheduled_duration_s,
            features.distance_remaining_m,
            features.delay_seconds if features.delay_seconds is not None else 0,
        ]
        return np.array([row], dtype=np.float64)

    def predict(self, features: ETAFeatures) -> Optional[ETAPrediction]:
        """Predict ETA for the given features.

        Returns None if no model loaded or no coverage for this feature set.
        Never returns a low-confidence guess.
        """
        self._ensure_loaded()

        if self._linear_model is None:
            return None

        X = self._features_to_array(features)

        # Use LightGBM if available, fallback to linear
        if self._lgb_model is not None:
            prediction = float(self._lgb_model.predict(X)[0])
            confidence = 0.7  # LightGBM generally higher confidence
        else:
            prediction = float(self._linear_model.predict(X)[0])
            confidence = 0.5  # Linear regression baseline confidence

        # Validate prediction is reasonable
        if prediction <= 0 or prediction > 7200:  # max 2 hours
            logger.warning(
                "unreasonable_prediction",
                prediction=prediction,
                features=features.model_dump(),
            )
            return None

        # Compute confidence based on prediction distance from scheduled
        scheduled = features.scheduled_duration_s
        if scheduled > 0:
            deviation = abs(prediction - scheduled) / scheduled
            if deviation > 0.5:
                confidence *= 0.8
            elif deviation > 0.3:
                confidence *= 0.9

        # Ensure confidence is within bounds
        confidence = max(0.0, min(1.0, confidence))

        return ETAPrediction(
            predicted_eta_seconds=prediction,
            confidence=confidence,
            model_version=self._metadata.get("version", self._version),
            provenance="ml",
        )

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._linear_model is not None

    @property
    def model_version(self) -> Optional[str]:
        self._ensure_loaded()
        return self._metadata.get("version") if self._metadata else None

    @property
    def model_info(self) -> dict:
        """Return model metadata for health/status endpoints."""
        self._ensure_loaded()
        return {
            "available": self.is_available,
            "version": self._metadata.get("version"),
            "source": self._metadata.get("source"),
            "sample_count": self._metadata.get("sample_count"),
            "evaluation": self._metadata.get("evaluation"),
            "has_lightgbm": self._lgb_model is not None,
            "has_linear": self._linear_model is not None,
        }


class NoOpETAPredictor:
    """Placeholder predictor when no ML model is configured.

    Always returns None — the caller must use deterministic ETA.
    """

    def predict(self, features: ETAFeatures) -> Optional[ETAPrediction]:
        return None

    @property
    def is_available(self) -> bool:
        return False

    @property
    def model_version(self) -> Optional[str]:
        return None

    @property
    def model_info(self) -> dict:
        return {"available": False, "version": None}
