from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import structlog
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

from app.eta.schemas import TrainingSample

logger = structlog.get_logger(__name__)

# Default model directory
DEFAULT_MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "eta_models"

# Feature columns used for training (must match ETAFeatures)
FEATURE_COLUMNS = [
    "route_id",
    "stop_id",
    "hour_of_day",
    "day_of_week_encoded",
    "scheduled_duration_s",
    "distance_remaining_m",
    "delay_seconds",
]

# Day-of-week encoding
DAY_ENCODING = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _encode_time_of_day(time_of_day: str) -> int:
    """Extract hour from HH:MM format."""
    parts = time_of_day.split(":")
    return int(parts[0]) if len(parts) == 2 else 0


def _samples_to_numpy(
    samples: list[TrainingSample],
) -> tuple[np.ndarray, np.ndarray]:
    """Convert training samples to numpy arrays for model training."""
    X = []
    y = []
    for s in samples:
        row = [
            s.route_id,
            s.stop_id,
            _encode_time_of_day(s.time_of_day),
            DAY_ENCODING.get(s.day_of_week, 0),
            s.scheduled_duration_s,
            s.distance_remaining_m,
            s.delay_seconds if s.delay_seconds is not None else 0,
        ]
        X.append(row)
        y.append(s.actual_duration_s)
    return np.array(X, dtype=np.float64), np.array(y, dtype=np.float64)


def train_model(
    samples: list[TrainingSample],
    model_version: str = "v1",
    test_size: float = 0.2,
    random_state: int = 42,
) -> ETAModelResult:
    """Train both LightGBM (if available) and LinearRegression models.

    Args:
        samples: Training data
        model_version: Version string for the model artifact
        test_size: Fraction of data for test evaluation
        random_state: Random seed for reproducibility

    Returns:
        ETAModelResult with trained models and evaluation metrics
    """
    if len(samples) < 10:
        raise ValueError(f"Need at least 10 samples, got {len(samples)}")

    X, y = _samples_to_numpy(samples)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state,
    )

    # Train LightGBM if available
    lgb_model = None
    lgb_mae = float("inf")
    if HAS_LIGHTGBM:
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

        params = {
            "objective": "regression",
            "metric": "mae",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "seed": random_state,
        }

        lgb_model = lgb.train(
            params,
            train_data,
            num_boost_round=200,
            valid_sets=[valid_data],
            callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(0)],
        )

        lgb_pred = lgb_model.predict(X_test)
        lgb_mae = float(mean_absolute_error(y_test, lgb_pred))
        lgb_rmse = float(np.sqrt(mean_squared_error(y_test, lgb_pred)))
        lgb_r2 = float(r2_score(y_test, lgb_pred))

        logger.info(
            "lightgbm_trained",
            mae=lgb_mae,
            rmse=lgb_rmse,
            r2=lgb_r2,
            train_samples=len(X_train),
            test_samples=len(X_test),
        )

    # Train Linear Regression baseline
    lr_model = LinearRegression()
    lr_model.fit(X_train, y_train)

    lr_pred = lr_model.predict(X_test)
    lr_mae = float(mean_absolute_error(y_test, lr_pred))
    lr_rmse = float(np.sqrt(mean_squared_error(y_test, lr_pred)))
    lr_r2 = float(r2_score(y_test, lr_pred))

    # Baseline: predict scheduled_duration_s for all samples
    baseline_pred = X_test[:, FEATURE_COLUMNS.index("scheduled_duration_s")]
    baseline_mae = float(mean_absolute_error(y_test, baseline_pred))

    # Compute feature importances from LightGBM if available
    feature_importances = {}
    if lgb_model is not None:
        importances = lgb_model.feature_importance(importance_type="gain")
        for name, imp in zip(FEATURE_COLUMNS, importances):
            feature_importances[name] = float(imp)
    else:
        # Linear regression coefficients
        for name, coef in zip(FEATURE_COLUMNS, lr_model.coef_):
            feature_importances[name] = float(abs(coef))

    logger.info(
        "linear_baseline_trained",
        mae=lr_mae,
        rmse=lr_rmse,
        r2=lr_r2,
        baseline_mae=baseline_mae,
        improvement_pct=((baseline_mae - lgb_mae) / baseline_mae * 100)
        if HAS_LIGHTGBM
        else ((baseline_mae - lr_mae) / baseline_mae * 100),
    )

    return ETAModelResult(
        model_version=model_version,
        lightgbm_model=lgb_model,
        linear_model=lr_model,
        feature_columns=FEATURE_COLUMNS,
        evaluation={
            "lightgbm": {
                "mae": lgb_mae,
                "rmse": lgb_rmse,
                "r2": lgb_r2,
            } if HAS_LIGHTGBM else None,
            "linear": {
                "mae": lr_mae,
                "rmse": lr_rmse,
                "r2": lr_r2,
            },
            "baseline_mae": baseline_mae,
        },
        feature_importances=feature_importances,
        sample_count=len(samples),
    )


def save_model(
    result: ETAModelResult,
    output_dir: Optional[Path] = None,
    version: Optional[str] = None,
) -> Path:
    """Save trained model artifacts to disk."""
    if output_dir is None:
        output_dir = DEFAULT_MODEL_DIR
    if version is None:
        version = result.model_version

    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir = output_dir / version
    model_dir.mkdir(parents=True, exist_ok=True)

    # Save LightGBM model
    lgb_path = None
    if result.lightgbm_model is not None:
        lgb_path = str(model_dir / "lightgbm_model.txt")
        result.lightgbm_model.save_model(lgb_path)

    # Save Linear model
    lr_path = str(model_dir / "linear_model.joblib")
    joblib.dump(result.linear_model, lr_path)

    # Save metadata
    metadata = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "source": "synthetic",
        "sample_count": result.sample_count,
        "feature_columns": result.feature_columns,
        "evaluation": result.evaluation,
        "feature_importances": result.feature_importances,
        "lightgbm_model_path": lgb_path,
        "linear_model_path": lr_path,
    }

    metadata_path = model_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)

    logger.info(
        "model_saved",
        version=version,
        model_dir=str(model_dir),
    )

    return model_dir


def load_model(
    model_dir: Optional[Path] = None,
    version: str = "v1",
) -> Optional[tuple]:
    """Load trained model artifacts from disk.

    Returns:
        Tuple of (lightgbm_model_or_None, linear_model, metadata_dict)
        or None if model files don't exist.
    """
    if model_dir is None:
        model_dir = DEFAULT_MODEL_DIR / version
    else:
        model_dir = model_dir / version

    metadata_path = model_dir / "metadata.json"
    if not metadata_path.exists():
        logger.warning("model_not_found", path=str(model_dir))
        return None

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Load LightGBM model
    lgb_model = None
    lgb_path = metadata.get("lightgbm_model_path")
    if lgb_path and HAS_LIGHTGBM and Path(lgb_path).exists():
        lgb_model = lgb.Booster(model_file=lgb_path)

    # Load Linear model
    lr_path = metadata.get("linear_model_path")
    if lr_path and Path(lr_path).exists():
        lr_model = joblib.load(lr_path)
    else:
        logger.warning("linear_model_not_found", path=str(lr_path))
        return None

    logger.info(
        "model_loaded",
        version=version,
        has_lightgbm=lgb_model is not None,
        has_linear=lr_model is not None,
    )

    return lgb_model, lr_model, metadata


class ETAModelResult:
    """Container for model training results."""

    def __init__(
        self,
        model_version: str,
        lightgbm_model=None,
        linear_model=None,
        feature_columns: list[str] | None = None,
        evaluation: dict | None = None,
        feature_importances: dict | None = None,
        sample_count: int = 0,
    ):
        self.model_version = model_version
        self.lightgbm_model = lightgbm_model
        self.linear_model = linear_model
        self.feature_columns = feature_columns or FEATURE_COLUMNS
        self.evaluation = evaluation or {}
        self.feature_importances = feature_importances or {}
        self.sample_count = sample_count
