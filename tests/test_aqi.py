"""AQI conversion tests: round-trip sanity and known breakpoints."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.aqi import aqi_category, aqi_from_concentration


def test_pm25_breakpoints_current():
    cases = [
        (9.0, 50),
        (9.1, 51),
        (35.4, 100),
        (35.5, 101),
        (55.4, 150),
        (55.5, 151),
        (125.4, 200),
        (125.5, 201),
        (225.4, 300),
        (225.5, 301),
        (325.4, 400),
        (325.5, 401),
        (500.4, 500),
    ]
    for conc, expected in cases:
        got = int(aqi_from_concentration([conc], "pm25", "current")[0])
        assert got == expected, f"{conc} -> {got}, expected {expected}"


def test_pm25_above_range_caps_at_500():
    assert int(aqi_from_concentration([999.0], "pm25", "current")[0]) == 500


def test_negative_is_nan():
    assert np.isnan(aqi_from_concentration([-1.0], "pm25", "current")[0])


def test_pm10_breakpoints_unchanged():
    cases = [
        (54.0, 50),
        (55.0, 51),
        (154.0, 100),
        (155.0, 101),
        (254.0, 150),
        (255.0, 151),
        (354.0, 200),
        (355.0, 201),
        (424.0, 300),
        (425.0, 301),
        (504.0, 400),
        (505.0, 401),
        (604.0, 500),
    ]
    for conc, expected in cases:
        got = int(aqi_from_concentration([conc], "pm10", "current")[0])
        assert got == expected, f"{conc} -> {got}, expected {expected}"


def test_study_vs_current_diverge_at_30():
    # 30 µg/m³ PM2.5: study-era AQI ≈ 75, current-era AQI = 100 (boundary shift)
    study = int(aqi_from_concentration([30.0], "pm25", "study")[0])
    current = int(aqi_from_concentration([30.0], "pm25", "current")[0])
    assert current > study


def test_category_labels():
    assert aqi_category(25) == "Good"
    assert aqi_category(75) == "Moderate"
    assert aqi_category(125) == "Unhealthy for sensitive groups"
    assert aqi_category(175) == "Unhealthy"
    assert aqi_category(250) == "Very unhealthy"
    assert aqi_category(400) == "Hazardous"
    assert aqi_category(float("nan")) is None
    assert aqi_category(None) is None


def test_vectorised_input():
    out = aqi_from_concentration([0.0, 10.0, 500.0], "pm25", "current")
    assert len(out) == 3
    assert int(out[0]) == 0
    assert int(out[1]) == 53  # 10.0 µg/m³ sits inside the 51–100 band
    assert int(out[2]) == 500
