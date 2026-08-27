from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import settings


class ETAConfig:
    """Configuration for the ETA prediction subsystem."""

    # Provider selection: "local" or "none"
    PROVIDER: str = settings.ETA_PROVIDER

    # Model directory (relative to backend root)
    MODEL_DIR: Path = Path(__file__).parent.parent.parent / "data" / "eta_models"

    # Default model version
    DEFAULT_VERSION: str = "v1"

    # Confidence threshold below which ML predictions are rejected
    CONFIDENCE_THRESHOLD: float = 0.3

    # Whether to attempt model loading on startup
    LAZY_LOAD: bool = True

    @classmethod
    def get_model_dir(cls) -> Path:
        return cls.MODEL_DIR

    @classmethod
    def is_ml_enabled(cls) -> bool:
        return cls.PROVIDER == "local"


eta_config = ETAConfig()
