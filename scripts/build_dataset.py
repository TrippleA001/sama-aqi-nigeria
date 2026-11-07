"""Build the clean hourly + daily datasets used by the Sama app.

Run from the repository root:

    python scripts/build_dataset.py

The script is intentionally explicit about every cleaning decision so the
pipeline can be audited. It reads the raw CAR-NASRDA / PurpleAir exports from
``data/raw`` and writes three files to ``data/processed``:

    hourly.parquet   one row per city-hour (2021-05-01 → 2023-04-30)
    daily.parquet    one row per city-day, with EPA AQI and exposure flags
    summary.json     headline statistics, data-quality facts and validation
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aqi import aqi_category, aqi_from_concentration, dominant_pollutant  # noqa: E402
from src.config import (  # noqa: E402
    CITIES,
    CITY_ORDER,
    DAILY_PATH,
    HOURLY_PATH,
    PROCESSED_DIR,
    RAW_DIR,
    STUDY_END,
    STUDY_START,
    SUMMARY_PATH,
    WHO_24H,
)

NUMERIC_COLS = [
    "temp_c",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_ms",
    "wind_dir_deg",
    "pm1",
    "pm25",
    "pm10",
]

# Physical plausibility windows. Values outside these are treated as sentinels
# (the raw files contain things like -273.15 °C and 1010.5 % humidity).
VALID_RANGES = {
    "temp_c": (-5.0, 55.0),
    "humidity_pct": (0.0, 100.0),
    "pressure_hpa": (900.0, 1100.0),
    "wind_speed_ms": (0.0, 40.0),
    "wind_dir_deg": (0.0, 360.0),
    "pm1": (0.0, 1000.0),
    "pm25": (0.0, 1000.0),
    "pm10": (0.0, 1200.0),
}

STUDY_START_TS = pd.Timestamp(STUDY_START)
STUDY_END_TS = pd.Timestamp(STUDY_END) + pd.Timedelta(hours=23)


def _time_to_hour(series: pd.Series, is_fraction: bool) -> pd.Series:
    """Normalise the many shapes the Time column takes across the exports."""
    if pd.api.types.is_numeric_dtype(series):
        values = pd.to_numeric(series, errors="coerce")
        hours = values * 24 if is_fraction else values
        return np.round(hours).astype("Int64") % 24

    def parse_one(value):
        if pd.isna(value):
            return pd.NA
        if isinstance(value, (pd.Timedelta, np.timedelta64)):
            return int(pd.Timedelta(value).total_seconds() // 3600) % 24
        if hasattr(value, "hour"):
            return int(value.hour)
        text = str(value).strip()
        if "day" in text.lower():
            text = text.split(",")[-1].strip()
        if ":" in text:
            return int(text.split(":")[0])
        try:
            return int(round(float(text)))
        except ValueError:
            return pd.NA

    return series.map(parse_one).astype("Int64")


def load_city(city: str) -> tuple[pd.DataFrame, dict]:
    meta = CITIES[city]
    path = RAW_DIR / meta["source_file"]
    if not path.exists():
        raise FileNotFoundError(f"Missing raw file: {path}")

    raw = pd.read_excel(path, sheet_name=meta["source_sheet"])
    raw = raw.drop(columns=[c for c in raw.columns if str(c).startswith("Unnamed")], errors="ignore")

    has_wd = any("wind direction" in str(c).lower() for c in raw.columns)
    keep = list(raw.columns[: 10 if has_wd else 9])
    frame = raw[keep].copy()

    if has_wd:
        frame.columns = [
            "date",
            "time",
            "temp_c",
            "humidity_pct",
            "pressure_hpa",
            "wind_speed_ms",
            "wind_dir_deg",
            "pm1",
            "pm25",
            "pm10",
        ]
    else:
        frame.columns = [
            "date",
            "time",
            "temp_c",
            "humidity_pct",
            "pressure_hpa",
            "wind_speed_ms",
            "pm1",
            "pm25",
            "pm10",
        ]
        frame["wind_dir_deg"] = np.nan

    audit = {
        "raw_rows": int(len(frame)),
        "source_file": meta["source_file"],
        "source_sheet": meta["source_sheet"],
    }

    # ---- timestamps ------------------------------------------------------
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if pd.api.types.is_numeric_dtype(frame["date"]):
        dates = pd.to_datetime(frame["date"], unit="D", origin="1899-12-30", errors="coerce")
    is_fraction = True
    if city == "Lagos":
        is_fraction = False
    hours = _time_to_hour(frame["time"], is_fraction=is_fraction)
    frame["timestamp"] = dates.dt.normalize() + pd.to_timedelta(hours.astype("float"), unit="h")

    # Lagos' original export leaves the date blank for most rows. The
    # "Reworked Lagos Hourly" sheet repeats it, but forward-fill as a guard.
    if frame["timestamp"].isna().any():
        frame["date"] = frame["date"].ffill()
        dates = pd.to_datetime(frame["date"], errors="coerce")
        if pd.api.types.is_numeric_dtype(frame["date"]):
            dates = pd.to_datetime(frame["date"], unit="D", origin="1899-12-30", errors="coerce")
        frame["timestamp"] = dates.dt.normalize() + pd.to_timedelta(hours.astype("float"), unit="h")

    # ---- numeric coercion + sentinel removal -----------------------------
    for col in NUMERIC_COLS:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    invalid_counts = {}
    for col, (low, high) in VALID_RANGES.items():
        bad = frame[col].notna() & ~frame[col].between(low, high)
        invalid_counts[col] = int(bad.sum())
        frame.loc[bad, col] = np.nan

    # A PM1 value cannot exceed PM2.5 by much; if the ordering is broken we
    # keep PM2.5 (the health-relevant measurement) and drop the inconsistent PM1.
    frame.loc[frame["pm1"] > frame["pm25"] + 5, "pm1"] = np.nan
    frame.loc[frame["pm25"] > frame["pm10"] + 5, "pm25"] = np.nan

    # Flag extreme sensor spikes with the same 3xIQR rule used in the source
    # study. Raw values are kept for transparency; the `_clean` columns feed
    # the daily averages, AQI and models.
    outlier_summary = {}
    for col in ["pm1", "pm25", "pm10"]:
        q1, q3 = frame[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        low, high = q1 - 3 * iqr, q3 + 3 * iqr
        flag = frame[col].notna() & ~frame[col].between(low, high)
        frame[f"{col}_outlier"] = flag
        frame[f"{col}_clean"] = frame[col].mask(flag)
        outlier_summary[col] = {
            "flagged": int(flag.sum()),
            "lower": round(float(low), 2),
            "upper": round(float(high), 2),
        }
    audit["outliers"] = outlier_summary

    frame = frame.dropna(subset=["timestamp"])
    frame = frame[(frame["timestamp"] >= STUDY_START_TS) & (frame["timestamp"] <= STUDY_END_TS)]
    frame = frame.sort_values("timestamp")

    dupes = int(frame.duplicated(subset=["timestamp"]).sum())
    frame = frame.drop_duplicates(subset=["timestamp"], keep="first")
    audit["duplicates_removed"] = dupes
    audit["invalid_values"] = invalid_counts

    # ---- complete hourly grid -------------------------------------------
    full_index = pd.date_range(STUDY_START_TS, STUDY_END_TS, freq="h", name="timestamp")
    frame = frame.set_index("timestamp")
    for col in ["pm1", "pm25", "pm10"]:
        audit[f"{col}_missing_before_reindex"] = int(frame[col].isna().sum())
    frame = frame.reindex(full_index)

    # Short meteorological gaps are interpolated (max 3 h). Pollution values
    # are never invented: they stay NaN and are handled by daily coverage rules.
    for col in ["temp_c", "humidity_pct", "pressure_hpa", "wind_speed_ms"]:
        frame[col] = frame[col].interpolate(method="time", limit=3, limit_area="inside")
    frame["wind_dir_deg"] = frame["wind_dir_deg"].interpolate(limit=3, limit_area="inside")

    frame = frame.reset_index()
    for col in ["pm1", "pm25", "pm10"]:
        frame[f"{col}_outlier"] = frame[f"{col}_outlier"].fillna(False).astype(bool)
    frame.insert(0, "city", city)
    frame["kind"] = meta["kind"]

    audit["rows_after_cleaning"] = int(len(frame))
    audit["coverage_pct"] = round(100 * frame["pm25"].notna().sum() / len(frame), 2)
    audit["pm25_valid_hours"] = int(frame["pm25"].notna().sum())
    audit["pm10_valid_hours"] = int(frame["pm10"].notna().sum())
    return frame, audit


def build_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    hourly = hourly.copy()
    hourly["date"] = hourly["timestamp"].dt.floor("D")

    grouped = hourly.groupby(["city", "date", "kind"], observed=True)

    daily = grouped.agg(
        pm1=("pm1", "mean"),
        pm25=("pm25", "mean"),
        pm10=("pm10", "mean"),
        temp_c=("temp_c", "mean"),
        humidity_pct=("humidity_pct", "mean"),
        pressure_hpa=("pressure_hpa", "mean"),
        wind_speed_ms=("wind_speed_ms", "mean"),
        n_pm25=("pm25", "count"),
        n_pm10=("pm10", "count"),
        n_pm25_outliers=("pm25_outlier", "sum"),
        n_pm10_outliers=("pm10_outlier", "sum"),
        n_wind=("wind_dir_deg", "count"),
    ).reset_index()

    # Circular mean of wind direction.
    radians = np.deg2rad(hourly["wind_dir_deg"])
    hourly["_sin"] = np.sin(radians)
    hourly["_cos"] = np.cos(radians)
    wind = hourly.groupby(["city", "date"], observed=True)[["_sin", "_cos"]].mean().reset_index()
    wind["wind_dir_deg"] = (np.degrees(np.arctan2(wind["_sin"], wind["_cos"])) + 360) % 360
    daily = daily.merge(wind[["city", "date", "wind_dir_deg"]], on=["city", "date"], how="left")

    daily["coverage_pm25"] = daily["n_pm25"] / 24
    daily["coverage_pm10"] = daily["n_pm10"] / 24

    # EPA requires at least 75% of hourly values for a valid daily average.
    valid25 = daily["n_pm25"] >= 18
    valid10 = daily["n_pm10"] >= 18
    daily["pm25_daily"] = daily["pm25"].where(valid25)
    daily["pm10_daily"] = daily["pm10"].where(valid10)

    daily["aqi_pm25"] = aqi_from_concentration(daily["pm25_daily"], "pm25", "current")
    daily["aqi_pm10"] = aqi_from_concentration(daily["pm10_daily"], "pm10", "current")
    daily["aqi_pm25_study"] = aqi_from_concentration(daily["pm25_daily"], "pm25", "study")
    daily["aqi_pm10_study"] = aqi_from_concentration(daily["pm10_daily"], "pm10", "study")

    daily["aqi"] = daily[["aqi_pm25", "aqi_pm10"]].max(axis=1, skipna=True)
    daily["dominant"] = dominant_pollutant(daily["aqi_pm25"], daily["aqi_pm10"])
    daily["category"] = daily["aqi"].map(aqi_category)
    daily["month"] = daily["date"].dt.month
    daily["year"] = daily["date"].dt.year
    daily["month_name"] = daily["date"].dt.strftime("%b")
    daily["day_of_week"] = daily["date"].dt.day_of_week
    daily["is_weekend"] = daily["day_of_week"] >= 5
    daily["season"] = np.where(daily["month"].isin([11, 12, 1, 2, 3]), "Dry", "Rainy")
    daily["exceeds_who_pm25"] = daily["pm25_daily"] > WHO_24H["pm25"]
    daily["exceeds_who_pm10"] = daily["pm10_daily"] > WHO_24H["pm10"]
    daily["who_multiple_pm25"] = daily["pm25_daily"] / WHO_24H["pm25"]
    daily["who_multiple_pm10"] = daily["pm10_daily"] / WHO_24H["pm10"]
    return daily.sort_values(["date", "city"]).reset_index(drop=True)


def build_summary(hourly: pd.DataFrame, daily: pd.DataFrame, audits: dict) -> dict:
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "study_start": STUDY_START,
        "study_end": STUDY_END,
        "cities": {},
        "totals": {
            "hourly_rows": int(len(hourly)),
            "daily_rows": int(len(daily)),
            "valid_pm25_hours": int(hourly["pm25"].notna().sum()),
            "days_with_aqi": int(daily["aqi"].notna().sum()),
        },
    }

    for city in CITY_ORDER:
        c_daily = daily[daily["city"] == city]
        c_hourly = hourly[hourly["city"] == city]
        aqi = c_daily["aqi"].dropna()
        pm25 = c_daily["pm25_daily"].dropna()
        pm10 = c_daily["pm10_daily"].dropna()
        meta = CITIES[city]
        summary["cities"][city] = {
            **{k: meta[k] for k in ("state", "kind", "lat", "lon", "population_m", "blurb")},
            "hourly_rows": int(len(c_hourly)),
            "valid_pm25_hours": int(c_hourly["pm25"].notna().sum()),
            "coverage_pm25_pct": round(100 * c_hourly["pm25"].notna().sum() / max(len(c_hourly), 1), 2),
            "outlier_hours": int(c_hourly["pm25_outlier"].sum()),
            "days": int(c_daily["aqi"].notna().sum()),
            "pm25_mean": round(float(pm25.mean()), 2) if len(pm25) else None,
            "pm25_median": round(float(pm25.median()), 2) if len(pm25) else None,
            "pm25_p95": round(float(pm25.quantile(0.95)), 2) if len(pm25) else None,
            "pm10_mean": round(float(pm10.mean()), 2) if len(pm10) else None,
            "aqi_mean": round(float(aqi.mean()), 1) if len(aqi) else None,
            "aqi_p95": round(float(aqi.quantile(0.95)), 1) if len(aqi) else None,
            "aqi_max": int(aqi.max()) if len(aqi) else None,
            "who_pm25_exceedance_pct": round(float((pm25 > WHO_24H["pm25"]).mean() * 100), 1) if len(pm25) else None,
            "dry_pm25": round(float(c_daily.loc[c_daily["season"] == "Dry", "pm25_daily"].dropna().mean()), 2)
            if c_daily["season"].eq("Dry").any()
            else None,
            "rainy_pm25": round(float(c_daily.loc[c_daily["season"] == "Rainy", "pm25_daily"].dropna().mean()), 2)
            if c_daily["season"].eq("Rainy").any()
            else None,
            "audit": audits[city],
        }

    urban = daily[daily["kind"] == "Urban"]["pm25_daily"].dropna()
    rural = daily[daily["kind"] == "Rural"]["pm25_daily"].dropna()
    summary["urban_vs_rural"] = {
        "urban_pm25_mean": round(float(urban.mean()), 2),
        "rural_pm25_mean": round(float(rural.mean()), 2),
        "ratio": round(float(urban.mean() / rural.mean()), 2),
        "urban_aqi_mean": round(float(daily[daily["kind"] == "Urban"]["aqi"].dropna().mean()), 1),
        "rural_aqi_mean": round(float(daily[daily["kind"] == "Rural"]["aqi"].dropna().mean()), 1),
        "urban_who_exceedance_pct": round(float((urban > WHO_24H["pm25"]).mean() * 100), 1),
        "rural_who_exceedance_pct": round(float((rural > WHO_24H["pm25"]).mean() * 100), 1),
    }
    return summary


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    hourly_frames = []
    audits = {}
    for city in CITY_ORDER:
        print(f"Loading {city} ...", end=" ", flush=True)
        frame, audit = load_city(city)
        hourly_frames.append(frame)
        audits[city] = audit
        print(f"{len(frame):,} rows | PM2.5 coverage {audit['coverage_pct']}%")

    hourly = pd.concat(hourly_frames, ignore_index=True)
    hourly = hourly.drop(columns=["date", "time"], errors="ignore")
    daily = build_daily(hourly)

    hourly.to_parquet(HOURLY_PATH, index=False)
    daily.to_parquet(DAILY_PATH, index=False)

    summary = build_summary(hourly, daily, audits)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nWrote:")
    for path in (HOURLY_PATH, DAILY_PATH, SUMMARY_PATH):
        print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size / 1e6:.2f} MB)")

    print("\nHeadline means (daily, study period):")
    for city in CITY_ORDER:
        s = summary["cities"][city]
        print(
            f"  {city:<11} PM2.5 {s['pm25_mean']:>6.2f}  PM10 {s['pm10_mean']:>6.2f}  "
            f"AQI {s['aqi_mean']:>5.1f}  WHO exceedance {s['who_pm25_exceedance_pct']:>4.1f}%  "
            f"days {s['days']}"
        )
    print(
        f"\nUrban PM2.5 mean {summary['urban_vs_rural']['urban_pm25_mean']} vs rural "
        f"{summary['urban_vs_rural']['rural_pm25_mean']} "
        f"({summary['urban_vs_rural']['ratio']}x)"
    )


if __name__ == "__main__":
    main()
