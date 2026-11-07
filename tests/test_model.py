"""Model bundle and forecast feature tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.config import MODEL_DIR
from src.model import FORECAST_FEATURES, ModelBundle, features_from_inputs


@pytest.mark.skipif(not MODEL_DIR.exists(), reason="models not trained")
def test_model_bundles_exist():
    expected = {
        f"{c}_{p}.joblib" for c in ["lagos", "abuja", "benin_city", "osogbo", "anyigba"] for p in ["pm25", "pm10"]
    }
    found = {p.name for p in MODEL_DIR.glob("*.joblib")}
    missing = expected - found
    assert not missing, f"missing model bundles: {missing}"


@pytest.mark.skipif(not MODEL_DIR.exists(), reason="models not trained")
def test_lagos_pm25_predict_ranges():
    import joblib

    bundle: ModelBundle = joblib.load(MODEL_DIR / "lagos_pm25.joblib")
    assert bundle.features == FORECAST_FEATURES
    X = features_from_inputs(
        today=35.0,
        week_average=32.0,
        temp_c=27.5,
        humidity_pct=80.0,
        pressure_hpa=1012.0,
        wind_speed_ms=2.5,
        wind_dir_deg=180,
        month=7,
        day_of_week=2,
    )
    point, low, high = bundle.predict(X)
    assert 0 < point < 300
    assert 0 <= low <= point <= high


def test_features_from_inputs_shape_and_bounds():
    X = features_from_inputs(
        today=10.0,
        week_average=10.0,
        temp_c=25.0,
        humidity_pct=70.0,
        pressure_hpa=1010.0,
        wind_speed_ms=3.0,
        wind_dir_deg=0,
        month=1,
        day_of_week=0,
    )
    assert list(X.columns) == FORECAST_FEATURES
    assert len(X) == 1
    # sin/cos in [-1, 1]
    for col in ["wind_dir_sin", "wind_dir_cos", "month_sin", "month_cos", "dow_sin", "dow_cos"]:
        assert -1.0 <= X[col].iloc[0] <= 1.0


def test_metrics_json_has_all_city_pollutants():
    import json

    path = MODEL_DIR / "metrics.json"
    if not path.exists():
        pytest.skip("metrics.json not trained")
    metrics = json.loads(path.read_text())
    cities = ["Lagos", "Abuja", "Benin City", "Osogbo", "Anyigba"]
    pollutants = ["PM2.5", "PM10"]
    for city in cities:
        for pol in pollutants:
            key = f"{city}|{pol}"
            assert key in metrics["models"], f"missing {key}"
            rec = metrics["models"][key]
            assert "Ensemble (deployed)" in rec["models"]
            assert "Persistence (today)" in rec["models"]
            assert 0 <= rec["interval_coverage_pct"] <= 100
