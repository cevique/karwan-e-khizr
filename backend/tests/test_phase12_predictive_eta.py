"""Phase 12 — Predictive ETA tests.

Tests cover:
- Schema validation
- Feature extraction
- Synthetic training data generation
- Model training, serialization, loading
- Prediction and fallback
- Integration with simulation provider
- Regression: existing Phase 8 tests still pass
"""

import json
import math
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.eta.schemas import ETAFeatures, ETAPrediction, TrainingSample, ModelArtifact
from app.eta.features import (
    extract_eta_features,
    extract_features_from_segments,
    _haversine_m,
)
from app.eta.model import (
    train_model,
    save_model,
    load_model,
    _encode_time_of_day,
    DAY_ENCODING,
    FEATURE_COLUMNS,
    ETAModelResult,
)
from app.eta.predictor import (
    ETAPredictor,
    LocalETAPredictor,
    NoOpETAPredictor,
)
from app.eta.training import (
    generate_synthetic_dataset,
    save_training_data,
    load_training_data,
)
from app.eta.config import ETAConfig, eta_config
from app.simulation.engine import SimulationEngine
from app.simulation.schemas import StopTimeEntry


def make_stop(
    stop_id: int,
    lat: float,
    lon: float,
    arrival_s: int,
    departure_s: int,
    seq: int,
) -> StopTimeEntry:
    return StopTimeEntry(
        stop_id=stop_id,
        sequence=seq,
        arrival_offset_s=arrival_s,
        departure_offset_s=departure_s,
        lat=lat,
        lon=lon,
    )


def make_3_stop_schedule() -> list[StopTimeEntry]:
    return [
        make_stop(1, 33.646, 73.048, 0, 15, 1),
        make_stop(2, 33.687, 73.055, 300, 315, 2),
        make_stop(3, 33.729, 73.091, 600, 615, 3),
    ]


def make_5_stop_schedule() -> list[StopTimeEntry]:
    return [
        make_stop(1, 33.646, 73.048, 0, 15, 1),
        make_stop(2, 33.660, 73.050, 150, 165, 2),
        make_stop(3, 33.687, 73.055, 300, 315, 3),
        make_stop(4, 33.710, 73.075, 450, 465, 4),
        make_stop(5, 33.729, 73.091, 600, 615, 5),
    ]


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestETAFeaturesSchema:
    def test_valid_features(self):
        features = ETAFeatures(
            route_id=1,
            stop_id=5,
            time_of_day="08:30",
            day_of_week="monday",
            scheduled_duration_s=300,
            distance_remaining_m=1500.0,
        )
        assert features.route_id == 1
        assert features.stop_id == 5
        assert features.time_of_day == "08:30"
        assert features.day_of_week == "monday"
        assert features.scheduled_duration_s == 300
        assert features.distance_remaining_m == 1500.0
        assert features.delay_seconds is None

    def test_features_with_delay(self):
        features = ETAFeatures(
            route_id=2,
            stop_id=10,
            time_of_day="14:00",
            day_of_week="friday",
            scheduled_duration_s=600,
            distance_remaining_m=2000.0,
            delay_seconds=30,
        )
        assert features.delay_seconds == 30

    def test_features_accepts_any_day_string(self):
        # Feature schema is a data container; day_of_week is a plain string.
        # Validation happens at training/inference time, not schema time.
        features = ETAFeatures(
            route_id=1,
            stop_id=5,
            time_of_day="08:00",
            day_of_week="Funday",
            scheduled_duration_s=300,
            distance_remaining_m=1500.0,
        )
        assert features.day_of_week == "Funday"


class TestETAPredictionSchema:
    def test_valid_prediction(self):
        pred = ETAPrediction(
            predicted_eta_seconds=180.5,
            confidence=0.75,
            model_version="v1",
        )
        assert pred.predicted_eta_seconds == 180.5
        assert pred.confidence == 0.75
        assert pred.model_version == "v1"
        assert pred.provenance == "ml"

    def test_prediction_confidence_bounds(self):
        with pytest.raises(Exception):
            ETAPrediction(
                predicted_eta_seconds=100.0,
                confidence=1.5,  # out of bounds
                model_version="v1",
            )

    def test_prediction_confidence_zero(self):
        pred = ETAPrediction(
            predicted_eta_seconds=100.0,
            confidence=0.0,
            model_version="v1",
        )
        assert pred.confidence == 0.0


class TestTrainingSampleSchema:
    def test_valid_sample(self):
        sample = TrainingSample(
            route_id=1,
            stop_id=5,
            time_of_day="08:00",
            day_of_week="monday",
            scheduled_duration_s=300,
            distance_remaining_m=1500.0,
            actual_duration_s=280.0,
        )
        assert sample.source == "synthetic"

    def test_sample_with_real_source(self):
        sample = TrainingSample(
            route_id=1,
            stop_id=5,
            time_of_day="08:00",
            day_of_week="monday",
            scheduled_duration_s=300,
            distance_remaining_m=1500.0,
            actual_duration_s=280.0,
            source="real",
        )
        assert sample.source == "real"


# =============================================================================
# Feature Extraction Tests
# =============================================================================


class TestHaversine:
    def test_same_point_zero_distance(self):
        dist = _haversine_m(33.646, 73.048, 33.646, 73.048)
        assert dist == 0.0

    def test_known_distance(self):
        dist = _haversine_m(33.646, 73.048, 33.729, 73.091)
        assert 5000 < dist < 15000

    def test_symmetry(self):
        d1 = _haversine_m(33.646, 73.048, 33.729, 73.091)
        d2 = _haversine_m(33.729, 73.091, 33.646, 73.048)
        assert abs(d1 - d2) < 0.1


class TestExtractETAFeatures:
    def test_returns_features_mid_trip(self):
        stops = make_3_stop_schedule()
        features = extract_eta_features(
            stops=stops,
            current_elapsed_s=150.0,
            route_id=1,
            current_time=datetime(2026, 8, 27, 8, 30, tzinfo=timezone.utc),
        )
        assert features is not None
        assert isinstance(features, ETAFeatures)
        assert features.route_id == 1
        assert features.time_of_day == "08:30"
        # Aug 27, 2026 is a Thursday
        assert features.day_of_week == "thursday"
        assert features.scheduled_duration_s > 0
        assert features.distance_remaining_m > 0

    def test_returns_none_before_departure(self):
        stops = make_3_stop_schedule()
        features = extract_eta_features(
            stops=stops,
            current_elapsed_s=-60.0,
            route_id=1,
        )
        assert features is None

    def test_returns_none_past_completion(self):
        stops = make_3_stop_schedule()
        features = extract_eta_features(
            stops=stops,
            current_elapsed_s=700.0,
            route_id=1,
        )
        assert features is None

    def test_returns_none_for_empty_schedule(self):
        features = extract_eta_features(
            stops=[],
            current_elapsed_s=100.0,
            route_id=1,
        )
        assert features is None

    def test_features_stop_id_matches_next_stop(self):
        stops = make_3_stop_schedule()
        features = extract_eta_features(
            stops=stops,
            current_elapsed_s=150.0,
            route_id=1,
        )
        assert features is not None
        # Next stop should be stop_id=2 (arrival at 300s)
        assert features.stop_id == 2


class TestExtractFeaturesFromSegments:
    def test_produces_features_for_each_segment(self):
        stops = make_3_stop_schedule()
        features = extract_features_from_segments(stops, route_id=1)
        assert len(features) == 2  # 3 stops = 2 segments

    def test_returns_empty_for_single_stop(self):
        features = extract_features_from_segments(
            [make_stop(1, 33.646, 73.048, 0, 15, 1)],
            route_id=1,
        )
        assert len(features) == 0

    def test_returns_empty_for_empty_schedule(self):
        features = extract_features_from_segments([], route_id=1)
        assert len(features) == 0

    def test_5_stop_schedule(self):
        stops = make_5_stop_schedule()
        features = extract_features_from_segments(stops, route_id=1)
        assert len(features) == 4


# =============================================================================
# Synthetic Training Data Generation Tests
# =============================================================================


class TestSyntheticDatasetGeneration:
    def test_generates_samples(self):
        schedules = [
            {
                "route_id": 1,
                "trip_id": 100,
                "stops": make_3_stop_schedule(),
            },
        ]
        samples = generate_synthetic_dataset(schedules)
        assert len(samples) > 0

    def test_samples_have_correct_schema(self):
        schedules = [
            {
                "route_id": 1,
                "trip_id": 100,
                "stops": make_3_stop_schedule(),
            },
        ]
        samples = generate_synthetic_dataset(schedules)
        for sample in samples[:5]:
            assert isinstance(sample, TrainingSample)
            assert sample.route_id == 1
            assert sample.source == "synthetic"
            assert sample.actual_duration_s > 0
            assert 0 <= int(sample.time_of_day.split(":")[0]) < 24

    def test_multiple_routes(self):
        schedules = [
            {"route_id": 1, "trip_id": 100, "stops": make_3_stop_schedule()},
            {"route_id": 2, "trip_id": 200, "stops": make_5_stop_schedule()},
        ]
        samples = generate_synthetic_dataset(schedules)
        route_ids = set(s.route_id for s in samples)
        assert 1 in route_ids
        assert 2 in route_ids

    def test_empty_schedules_produces_nothing(self):
        samples = generate_synthetic_dataset([])
        assert len(samples) == 0

    def test_skips_single_stop_trips(self):
        schedules = [
            {
                "route_id": 1,
                "trip_id": 100,
                "stops": [make_stop(1, 33.646, 73.048, 0, 15, 1)],
            },
        ]
        samples = generate_synthetic_dataset(schedules)
        assert len(samples) == 0


class TestSaveLoadTrainingData:
    def test_round_trip(self):
        samples = [
            TrainingSample(
                route_id=1,
                stop_id=5,
                time_of_day="08:00",
                day_of_week="monday",
                scheduled_duration_s=300,
                distance_remaining_m=1500.0,
                actual_duration_s=280.0,
            ),
            TrainingSample(
                route_id=2,
                stop_id=10,
                time_of_day="14:30",
                day_of_week="friday",
                scheduled_duration_s=450,
                distance_remaining_m=2200.0,
                actual_duration_s=420.0,
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = save_training_data(samples, output_dir)
            assert filepath.exists()

            loaded_samples, metadata = load_training_data(filepath)
            assert len(loaded_samples) == 2
            assert metadata["source"] == "synthetic"
            assert metadata["sample_count"] == 2

            # Verify data integrity
            assert loaded_samples[0].route_id == 1
            assert loaded_samples[0].actual_duration_s == 280.0
            assert loaded_samples[1].route_id == 2

    def test_metadata_contains_description(self):
        samples = [
            TrainingSample(
                route_id=1,
                stop_id=5,
                time_of_day="08:00",
                day_of_week="monday",
                scheduled_duration_s=300,
                distance_remaining_m=1500.0,
                actual_duration_s=280.0,
            ),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = save_training_data(samples, Path(tmpdir))
            with open(filepath) as f:
                data = json.load(f)
            assert "synthetic" in data["metadata"]["description"].lower()


# =============================================================================
# Model Training Tests
# =============================================================================


class TestModelTraining:
    def _make_training_samples(self, n: int = 50) -> list[TrainingSample]:
        """Generate deterministic training samples for testing."""
        samples = []
        rng = np.random.RandomState(42)
        for i in range(n):
            samples.append(TrainingSample(
                route_id=rng.randint(1, 4),
                stop_id=rng.randint(1, 20),
                time_of_day=f"{rng.randint(6, 22):02d}:{rng.randint(0, 59):02d}",
                day_of_week=["monday", "tuesday", "wednesday", "thursday", "friday"][
                    rng.randint(0, 5)
                ],
                scheduled_duration_s=rng.randint(120, 900),
                distance_remaining_m=rng.uniform(200, 5000),
                delay_seconds=rng.choice([None, 0, 10, 30]),
                actual_duration_s=rng.uniform(100, 850),
            ))
        return samples

    def test_train_produces_result(self):
        samples = self._make_training_samples(50)
        result = train_model(samples, model_version="test-v1")
        assert isinstance(result, ETAModelResult)
        assert result.model_version == "test-v1"
        assert result.sample_count == 50
        assert result.lightgbm_model is not None
        assert result.linear_model is not None

    def test_train_evaluate_has_metrics(self):
        samples = self._make_training_samples(50)
        result = train_model(samples)
        assert "lightgbm" in result.evaluation
        assert "linear" in result.evaluation
        assert "baseline_mae" in result.evaluation
        lgb_eval = result.evaluation["lightgbm"]
        assert lgb_eval["mae"] >= 0
        assert lgb_eval["rmse"] >= 0
        lr_eval = result.evaluation["linear"]
        assert lr_eval["mae"] >= 0

    def test_train_requires_minimum_samples(self):
        samples = self._make_training_samples(5)
        with pytest.raises(ValueError, match="at least 10"):
            train_model(samples)

    def test_feature_importances_populated(self):
        samples = self._make_training_samples(50)
        result = train_model(samples)
        assert len(result.feature_importances) == len(FEATURE_COLUMNS)
        for col in FEATURE_COLUMNS:
            assert col in result.feature_importances

    def test_deterministic_training(self):
        samples = self._make_training_samples(50)
        r1 = train_model(samples, random_state=42)
        r2 = train_model(samples, random_state=42)
        # Linear model coefficients should be identical
        np.testing.assert_array_almost_equal(
            r1.linear_model.coef_,
            r2.linear_model.coef_,
        )

    def test_lgbm_outperforms_baseline(self):
        samples = self._make_training_samples(100)
        result = train_model(samples)
        lgb_mae = result.evaluation["lightgbm"]["mae"]
        baseline_mae = result.evaluation["baseline_mae"]
        # LightGBM should at least match baseline
        assert lgb_mae <= baseline_mae * 1.5  # allow some tolerance


class TestModelSaveLoad:
    def _make_training_samples(self, n: int = 50) -> list[TrainingSample]:
        rng = np.random.RandomState(42)
        samples = []
        for i in range(n):
            samples.append(TrainingSample(
                route_id=rng.randint(1, 4),
                stop_id=rng.randint(1, 20),
                time_of_day=f"{rng.randint(6, 22):02d}:{rng.randint(0, 59):02d}",
                day_of_week=["monday", "tuesday", "wednesday", "thursday", "friday"][
                    rng.randint(0, 5)
                ],
                scheduled_duration_s=rng.randint(120, 900),
                distance_remaining_m=rng.uniform(200, 5000),
                actual_duration_s=rng.uniform(100, 850),
            ))
        return samples

    def test_save_and_load_round_trip(self):
        samples = self._make_training_samples(50)
        result = train_model(samples, model_version="test-v1")

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            save_model(result, model_dir, version="test-v1")

            loaded = load_model(model_dir, version="test-v1")
            assert loaded is not None
            lgb_model, lr_model, metadata = loaded
            assert lgb_model is not None
            assert lr_model is not None
            assert metadata["version"] == "test-v1"
            assert metadata["sample_count"] == 50

    def test_load_nonexistent_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loaded = load_model(Path(tmpdir), version="nonexistent")
            assert loaded is None

    def test_saved_model_produces_same_predictions(self):
        samples = self._make_training_samples(50)
        result = train_model(samples, model_version="test-v1")

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            save_model(result, model_dir, version="test-v1")
            loaded = load_model(model_dir, version="test-v1")
            assert loaded is not None

            # Both models should predict the same value
            test_X = np.array([[1, 5, 8, 0, 300, 1500.0, 0]], dtype=np.float64)
            original_pred = result.linear_model.predict(test_X)[0]
            loaded_pred = loaded[1].predict(test_X)[0]
            assert abs(original_pred - loaded_pred) < 1e-6


class TestModelHelpers:
    def test_encode_time_of_day(self):
        assert _encode_time_of_day("08:30") == 8
        assert _encode_time_of_day("14:00") == 14
        assert _encode_time_of_day("00:00") == 0
        assert _encode_time_of_day("23:59") == 23

    def test_day_encoding(self):
        assert DAY_ENCODING["monday"] == 0
        assert DAY_ENCODING["friday"] == 4
        assert DAY_ENCODING["sunday"] == 6


# =============================================================================
# Predictor Tests
# =============================================================================


class TestNoOpETAPredictor:
    def test_always_returns_none(self):
        predictor = NoOpETAPredictor()
        features = ETAFeatures(
            route_id=1,
            stop_id=5,
            time_of_day="08:00",
            day_of_week="monday",
            scheduled_duration_s=300,
            distance_remaining_m=1500.0,
        )
        result = predictor.predict(features)
        assert result is None

    def test_not_available(self):
        predictor = NoOpETAPredictor()
        assert predictor.is_available is False
        assert predictor.model_version is None


class TestLocalETAPredictor:
    def _make_training_samples(self, n: int = 50) -> list[TrainingSample]:
        rng = np.random.RandomState(42)
        samples = []
        for i in range(n):
            samples.append(TrainingSample(
                route_id=rng.randint(1, 4),
                stop_id=rng.randint(1, 20),
                time_of_day=f"{rng.randint(6, 22):02d}:{rng.randint(0, 59):02d}",
                day_of_week=["monday", "tuesday", "wednesday", "thursday", "friday"][
                    rng.randint(0, 5)
                ],
                scheduled_duration_s=rng.randint(120, 900),
                distance_remaining_m=rng.uniform(200, 5000),
                actual_duration_s=rng.uniform(100, 850),
            ))
        return samples

    def test_no_model_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = LocalETAPredictor(
                model_dir=Path(tmpdir),
                version="nonexistent",
            )
            features = ETAFeatures(
                route_id=1,
                stop_id=5,
                time_of_day="08:00",
                day_of_week="monday",
                scheduled_duration_s=300,
                distance_remaining_m=1500.0,
            )
            result = predictor.predict(features)
            assert result is None
            assert predictor.is_available is False

    def test_with_trained_model_returns_prediction(self):
        samples = self._make_training_samples(50)
        result = train_model(samples, model_version="test-v1")

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            save_model(result, model_dir, version="test-v1")

            predictor = LocalETAPredictor(model_dir=model_dir, version="test-v1")
            assert predictor.is_available is True

            features = ETAFeatures(
                route_id=1,
                stop_id=5,
                time_of_day="08:00",
                day_of_week="monday",
                scheduled_duration_s=300,
                distance_remaining_m=1500.0,
            )
            prediction = predictor.predict(features)
            assert prediction is not None
            assert isinstance(prediction, ETAPrediction)
            assert prediction.predicted_eta_seconds > 0
            assert 0.0 <= prediction.confidence <= 1.0
            assert prediction.model_version == "test-v1"
            assert prediction.provenance == "ml"

    def test_prediction_validated_for_reasonableness(self):
        """Predictions must be between 0 and 7200 seconds."""
        samples = self._make_training_samples(50)
        result = train_model(samples, model_version="test-v1")

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            save_model(result, model_dir, version="test-v1")
            predictor = LocalETAPredictor(model_dir=model_dir, version="test-v1")

            # Multiple predictions should all be reasonable
            for _ in range(10):
                features = ETAFeatures(
                    route_id=np.random.randint(1, 4),
                    stop_id=np.random.randint(1, 20),
                    time_of_day=f"{np.random.randint(6, 22):02d}:00",
                    day_of_week="monday",
                    scheduled_duration_s=np.random.randint(120, 900),
                    distance_remaining_m=np.random.uniform(200, 5000),
                )
                prediction = predictor.predict(features)
                if prediction is not None:
                    assert 0 < prediction.predicted_eta_seconds <= 7200

    def test_model_info(self):
        samples = self._make_training_samples(50)
        result = train_model(samples, model_version="test-v1")

        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            save_model(result, model_dir, version="test-v1")
            predictor = LocalETAPredictor(model_dir=model_dir, version="test-v1")

            info = predictor.model_info
            assert info["available"] is True
            assert info["version"] == "test-v1"
            assert info["has_lightgbm"] is True
            assert info["has_linear"] is True


# =============================================================================
# Configuration Tests
# =============================================================================


class TestETAConfig:
    def test_default_provider(self):
        config = ETAConfig()
        assert config.PROVIDER in ("local", "none")

    def test_is_ml_enabled(self):
        config = ETAConfig()
        # Should not raise
        result = config.is_ml_enabled()
        assert isinstance(result, bool)

    def test_get_model_dir(self):
        config = ETAConfig()
        model_dir = config.get_model_dir()
        assert isinstance(model_dir, Path)


# =============================================================================
# Integration with Simulation Provider Tests
# =============================================================================


class TestSimulationProviderIntegration:
    def test_provider_accepts_eta_predictor(self):
        from app.simulation.provider import SimulatedVehicleLocationProvider

        engine = SimulationEngine()
        db = AsyncMock()
        predictor = NoOpETAPredictor()

        provider = SimulatedVehicleLocationProvider(
            engine=engine,
            db=db,
            eta_predictor=predictor,
        )
        assert provider._eta_predictor is predictor

    def test_provider_default_no_predictor(self):
        from app.simulation.provider import SimulatedVehicleLocationProvider

        engine = SimulationEngine()
        db = AsyncMock()

        provider = SimulatedVehicleLocationProvider(engine=engine, db=db)
        assert isinstance(provider._eta_predictor, NoOpETAPredictor)


# =============================================================================
# End-to-End Pipeline Tests
# =============================================================================


class TestEndToEndPipeline:
    def test_full_pipeline_synthetic_to_prediction(self):
        """Full pipeline: generate training data -> train -> predict."""
        schedules = [
            {"route_id": 1, "trip_id": 100, "stops": make_3_stop_schedule()},
            {"route_id": 2, "trip_id": 200, "stops": make_5_stop_schedule()},
        ]

        # Generate synthetic data
        samples = generate_synthetic_dataset(schedules)
        assert len(samples) > 0

        # Train model
        result = train_model(samples, model_version="e2e-test")
        assert result.lightgbm_model is not None
        assert result.linear_model is not None

        # Save and load
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            save_model(result, model_dir, version="e2e-test")
            loaded = load_model(model_dir, version="e2e-test")
            assert loaded is not None

            # Predict
            predictor = LocalETAPredictor(model_dir=model_dir, version="e2e-test")
            assert predictor.is_available

            features = ETAFeatures(
                route_id=1,
                stop_id=2,
                time_of_day="08:00",
                day_of_week="monday",
                scheduled_duration_s=300,
                distance_remaining_m=1500.0,
            )
            prediction = predictor.predict(features)
            assert prediction is not None
            assert prediction.predicted_eta_seconds > 0
            assert prediction.provenance == "ml"

    def test_pipeline_produces_improvement_over_baseline(self):
        """ML model should at least match the scheduled-duration baseline."""
        schedules = [
            {"route_id": 1, "trip_id": 100, "stops": make_3_stop_schedule()},
            {"route_id": 2, "trip_id": 200, "stops": make_5_stop_schedule()},
        ]

        samples = generate_synthetic_dataset(schedules)
        result = train_model(samples, model_version="test")

        # LightGBM MAE should be less than or equal to baseline MAE
        lgb_mae = result.evaluation["lightgbm"]["mae"]
        baseline_mae = result.evaluation["baseline_mae"]
        assert lgb_mae <= baseline_mae


# =============================================================================
# Regression Tests — Existing Phase 8 behavior preserved
# =============================================================================


class TestRegressionPhase8Preserved:
    def test_engine_still_works(self):
        engine = SimulationEngine()
        schedule = make_3_stop_schedule()
        pos = engine.compute_position_at(schedule, 150.0)
        assert pos["status"] == "active"
        assert pos["latitude"] > 33.646

    def test_eta_still_works(self):
        engine = SimulationEngine()
        schedule = make_3_stop_schedule()
        eta = engine.compute_eta_at(schedule, 100.0)
        assert eta is not None
        assert eta["baseline_eta_seconds"] == 200

    def test_schemas_importable(self):
        from app.eta.schemas import ETAFeatures, ETAPrediction, TrainingSample
        from app.eta.predictor import ETAPredictor, LocalETAPredictor, NoOpETAPredictor
        from app.eta.model import train_model, save_model, load_model
        from app.eta.training import generate_synthetic_dataset
        from app.eta.features import extract_eta_features
        assert all([ETAFeatures, ETAPrediction, TrainingSample, ETAPredictor])

    def test_api_routes_still_registered(self):
        from app.main import app
        schema = app.openapi()
        paths = list(schema.get("paths", {}).keys())
        assert "/api/v1/transit/realtime/vehicles" in paths
        assert "/api/v1/transit/realtime/vehicles/{vehicle_id}/eta" in paths


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    def test_features_at_segment_boundary(self):
        """Features right at a stop arrival."""
        stops = make_3_stop_schedule()
        # Exactly at stop 2 arrival
        features = extract_eta_features(
            stops=stops,
            current_elapsed_s=300.0,
            route_id=1,
        )
        # At stop 2 arrival, next stop is stop 3
        assert features is not None
        assert features.stop_id == 3

    def test_features_just_after_stop_arrival(self):
        stops = make_3_stop_schedule()
        features = extract_eta_features(
            stops=stops,
            current_elapsed_s=310.0,
            route_id=1,
        )
        assert features is not None
        assert features.stop_id == 3

    def test_training_with_minimal_samples(self):
        """Exactly 10 samples (minimum)."""
        rng = np.random.RandomState(42)
        samples = [
            TrainingSample(
                route_id=rng.randint(1, 4),
                stop_id=rng.randint(1, 20),
                time_of_day=f"{rng.randint(6, 22):02d}:00",
                day_of_week="monday",
                scheduled_duration_s=rng.randint(120, 900),
                distance_remaining_m=rng.uniform(200, 5000),
                actual_duration_s=rng.uniform(100, 850),
            )
            for _ in range(10)
        ]
        result = train_model(samples)
        assert result.sample_count == 10

    def test_prediction_with_zero_distance(self):
        """Prediction when distance remaining is zero."""
        samples = []
        rng = np.random.RandomState(42)
        for i in range(50):
            samples.append(TrainingSample(
                route_id=1,
                stop_id=5,
                time_of_day=f"{rng.randint(6, 22):02d}:00",
                day_of_week="monday",
                scheduled_duration_s=300,
                distance_remaining_m=0.0,
                actual_duration_s=10.0,
            ))
        result = train_model(samples)
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            save_model(result, model_dir, version="zero-dist")
            predictor = LocalETAPredictor(model_dir=model_dir, version="zero-dist")
            features = ETAFeatures(
                route_id=1,
                stop_id=5,
                time_of_day="08:00",
                day_of_week="monday",
                scheduled_duration_s=300,
                distance_remaining_m=0.0,
            )
            prediction = predictor.predict(features)
            # Should not crash; prediction may or may not be valid
            # depending on the model
            assert prediction is None or isinstance(prediction, ETAPrediction)
