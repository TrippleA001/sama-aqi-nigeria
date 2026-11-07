"""Cached data access and lightweight derived views for the app."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from .aqi import aqi_category, aqi_color, aqi_from_concentration
from .config import (
    CITIES,
    DAILY_PATH,
    HOURLY_PATH,
    METRICS_PATH,
    MODEL_DIR,
    SUMMARY_PATH,
)


def _require(path: Path) -> Path:
    if not path.exists():
        st.error(
            f"Missing data file: `{path.name}`. Run `python scripts/build_dataset.py` "
            "from the repository root, then reload."
        )
        st.stop()
    return path


@st.cache_data(show_spinner=False)
def load_hourly() -> pd.DataFrame:
    frame = pd.read_parquet(_require(HOURLY_PATH))
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame


@st.cache_data(show_spinner=False)
def load_daily() -> pd.DataFrame:
    frame = pd.read_parquet(_require(DAILY_PATH))
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


@st.cache_data(show_spinner=False)
def load_summary() -> dict:
    return json.loads(_require(SUMMARY_PATH).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_metrics() -> dict:
    return json.loads(_require(METRICS_PATH).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_predictions() -> pd.DataFrame:
    path = MODEL_DIR / "validation_predictions.parquet"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_parquet(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame


@st.cache_resource(show_spinner=False)
def load_model(city: str, pollutant: str):
    slug = city.lower().replace(" ", "_")
    path = MODEL_DIR / f"{slug}_{pollutant}.joblib"
    if not path.exists():
        return None
    import joblib

    return joblib.load(path)


def city_frame(daily: pd.DataFrame, city: str) -> pd.DataFrame:
    return daily[daily["city"] == city].sort_values("date").reset_index(drop=True)


def window(daily: pd.DataFrame, start, end) -> pd.DataFrame:
    return daily[(daily["date"] >= pd.Timestamp(start)) & (daily["date"] <= pd.Timestamp(end))]


def window_hourly(frame: pd.DataFrame, start, end) -> pd.DataFrame:
    return frame[(frame["timestamp"] >= pd.Timestamp(start)) & (frame["timestamp"] <= pd.Timestamp(end))]


def city_cards(summary: dict) -> pd.DataFrame:
    rows = []
    for city, values in summary["cities"].items():
        rows.append(
            {
                "city": city,
                "state": values["state"],
                "kind": values["kind"],
                "lat": values["lat"],
                "lon": values["lon"],
                "pm25": values["pm25_mean"],
                "pm10": values["pm10_mean"],
                "aqi": values["aqi_mean"],
                "aqi_max": values["aqi_max"],
                "coverage": values["coverage_pm25_pct"],
                "days": values["days"],
                "who": values["who_pm25_exceedance_pct"],
                "category": aqi_category(values["aqi_mean"]),
                "color": aqi_color(values["aqi_mean"]),
                "population_m": values["population_m"],
            }
        )
    order = {name: i for i, name in enumerate(CITIES)}
    return pd.DataFrame(rows).sort_values("city", key=lambda s: s.map(order)).reset_index(drop=True)


@st.cache_data(ttl=900, show_spinner=False)
def live_air_quality() -> tuple[pd.DataFrame, str | None]:
    """Small live check from Open-Meteo (no API key required).

    This is deliberately separate from the 2021–2023 study data and is always
    labelled as an independent live reading.
    """
    rows = []
    error = None
    for city, meta in CITIES.items():
        params = {
            "latitude": meta["lat"],
            "longitude": meta["lon"],
            "current": "pm2_5,pm10",
            "timezone": "Africa/Lagos",
        }
        try:
            response = requests.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params=params,
                timeout=6,
                headers={"User-Agent": "Sama-AQI-Observatory/1.0"},
            )
            response.raise_for_status()
            payload = response.json()
            current = payload.get("current", {})
            pm25 = current.get("pm2_5")
            pm10 = current.get("pm10")
            aqi25 = aqi_from_concentration([pm25], "pm25", "current")[0] if pm25 is not None else None
            aqi10 = aqi_from_concentration([pm10], "pm10", "current")[0] if pm10 is not None else None
            aqi = max([v for v in (aqi25, aqi10) if v is not None], default=None)
            rows.append(
                {
                    "city": city,
                    "kind": meta["kind"],
                    "pm25": pm25,
                    "pm10": pm10,
                    "aqi": aqi,
                    "observed_at": current.get("time"),
                    "category": aqi_category(aqi),
                    "color": aqi_color(aqi) if aqi is not None else "#7A8C86",
                }
            )
        except Exception as exc:  # pragma: no cover - network dependent
            error = str(exc)
    return pd.DataFrame(rows), error
