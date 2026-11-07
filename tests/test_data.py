"""Data-loading and summary sanity tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest

from src.config import DAILY_PATH, SUMMARY_PATH
from src.data import city_cards, load_daily, load_hourly, load_summary


@pytest.mark.skipif(not DAILY_PATH.exists(), reason="processed data not built")
def test_hourly_loads_and_has_columns():
    df = load_hourly()
    assert not df.empty
    for col in ["timestamp", "city", "pm25", "pm10", "temp_c", "humidity_pct"]:
        assert col in df.columns, f"missing {col}"
    assert df["city"].nunique() == 5


@pytest.mark.skipif(not DAILY_PATH.exists(), reason="processed data not built")
def test_daily_has_aqi_and_city_columns():
    df = load_daily()
    assert not df.empty
    for col in ["date", "city", "pm25", "pm10", "aqi", "category", "season"]:
        assert col in df.columns, f"missing {col}"
    assert set(df["city"].unique()) == {
        "Lagos",
        "Abuja",
        "Benin City",
        "Osogbo",
        "Anyigba",
    }


@pytest.mark.skipif(not SUMMARY_PATH.exists(), reason="summary not built")
def test_summary_keys():
    summary = load_summary()
    assert "cities" in summary and "urban_vs_rural" in summary and "totals" in summary
    uvr = summary["urban_vs_rural"]
    assert uvr["urban_pm25_mean"] > uvr["rural_pm25_mean"]
    assert abs(uvr["ratio"] - uvr["urban_pm25_mean"] / uvr["rural_pm25_mean"]) < 0.01


@pytest.mark.skipif(not DAILY_PATH.exists(), reason="processed data not built")
def test_city_cards_returned_for_all_cities():
    summary = load_summary()
    cards = city_cards(summary)
    assert len(cards) == 5
    assert set(cards["city"]) == {
        "Lagos",
        "Abuja",
        "Benin City",
        "Osogbo",
        "Anyigba",
    }
    assert (cards["kind"] == "Rural").sum() == 1
    assert (cards["kind"] == "Urban").sum() == 4


@pytest.mark.skipif(not DAILY_PATH.exists(), reason="processed data not built")
def test_daily_date_range_covers_study_period():
    df = load_daily()
    assert df["date"].min() <= pd.Timestamp("2021-05-01")
    assert df["date"].max() >= pd.Timestamp("2023-04-30")
