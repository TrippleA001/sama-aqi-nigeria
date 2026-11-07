"""Method page: data pipeline, modelling choices and limitations."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src.theme import page_header, section, note, footer, legend
from src.data import load_daily, load_summary, load_metrics
from src.config import CITIES, CITY_ORDER, AQI_BANDS, BREAKPOINTS

# Study-era daily PM2.5 means reported by Odubanjo et al. (2024), transcribed
# here to validate the cleaning and aggregation pipeline.
PAPER_PM25_MEAN = {
    "Lagos": 37.39,
    "Abuja": 40.81,
    "Benin City": 46.19,
    "Osogbo": 28.88,
    "Anyigba": 14.36,
}

daily = load_daily()
summary = load_summary()
metrics = load_metrics()

page_header(
    "PAGE 04 · METHOD",
    "How the numbers were made",
    "Data pipeline, AQI standards, modelling decisions and limitations, with the original "
    "study reproduced where possible and divergences flagged where they matter.",
)

# --------------------------------------------------------------- data section
section("01", "Data source", "CAR-NASRDA PurpleAir sensors, five Nigerian locations.")
rows = []
for city in CITY_ORDER:
    meta = CITIES[city]
    rows.append(
        {
            "City": city,
            "Kind": meta["kind"],
            "State": meta["state"],
            "Period": "1 May 2021 – 30 Apr 2023",
            "Coverage": f"{summary['cities'][city]['coverage_pm25_pct']:.1f}%",
            "Days": summary["cities"][city]["days"],
        }
    )
table = pd.DataFrame(rows).set_index("City")
st.dataframe(table, use_container_width=True)

k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Valid hourly rows", f"{summary['totals']['valid_pm25_hours']:,}")
with k2:
    st.metric("Days with AQI", f"{summary['totals']['days_with_aqi']:,}")
with k3:
    st.metric("Cities", len(CITY_ORDER))

note(
    "Seven Excel files were downloaded from the study's Google Drive folder and cleaned in "
    "`scripts/build_dataset.py`. Quirks handled: Excel serial dates, Lagos time as integers, "
    "fraction-of-day times elsewhere, missing Lagos wind direction, sentinel values "
    "(-273.15 °C, humidity > 100%, pressure ~1.5 / 11016, negative wind). Duplicates removed, "
    "full hourly grid reindexed. PM is never interpolated; a calendar day needs ≥18 valid "
    "hours (the EPA 75% rule) to receive a daily AQI."
)

# --------------------------------------------------------------- AQI section
section("02", "AQI standards", "Two breakpoints are implemented; the app uses the current one.")
tab_cur, tab_study = st.tabs(["Current (2024 EPA)", "Study-era (2006 EPA)"])
with tab_cur:
    st.caption("US EPA 2024 PM2.5 revision; PM10 unchanged.")
    rows = []
    for name, lo, hi, _, advice in AQI_BANDS:
        rows.append(
            {
                "Band": name,
                "PM2.5 (µg/m³)": f"{lo} – {hi}",
                "AQI": f"{lo if lo else 0} – {hi}",
                "Advice": advice,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
with tab_study:
    st.caption("2006 breakpoints used by Odubanjo et al. (2024), reproduced for validation.")
    data = []
    for name, lo, hi, _, _ in AQI_BANDS:
        aqi_range = "n/a"
        study_pm25 = "n/a"
        for clo, chi, cilo, cihi in BREAKPOINTS["pm25"]["study"]:
            if abs(clo - lo) < 1e-6 or abs(chi - hi) < 1e-6:
                study_pm25 = f"{clo} – {chi}"
                aqi_range = f"{cilo} – {cihi}"
                break
        data.append(
            {
                "Band": name,
                "Current PM2.5": f"{lo} – {hi}",
                "Study-era PM2.5": study_pm25,
                "AQI": aqi_range,
            }
        )
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

legend()
st.caption("Band colours used throughout the app.")

note(
    "The source study computed AQI from daily means with the 2006 table. This app's Overview "
    "and City Explorer use the current (2024) PM2.5 breakpoints, so AQI values may differ "
    "slightly from the paper around the 35–40 µg/m³ boundary. This difference is intentional "
    "and documented. The study-era table above reproduces the original values for the "
    "headline urban vs rural comparison."
)

# --------------------------------------------------------------- validation
section("03", "Reproducing the paper", "Daily means vs Odubanjo et al. (2024), Table values.")
val = pd.DataFrame(
    [
        {
            "City": c,
            "Paper": PAPER_PM25_MEAN[c],
            "This build": round(summary["cities"][c]["pm25_mean"], 2),
            "Δ": round(summary["cities"][c]["pm25_mean"] - PAPER_PM25_MEAN[c], 2),
        }
        for c in CITY_ORDER
    ]
)
st.dataframe(val, use_container_width=True, hide_index=True)
note(
    "Daily PM2.5 means match the paper within ~3 µg/m³ for every city; PM10 matches nearly "
    "exactly. Tiny differences come from cleaning choices (sentinel handling, duplicate "
    "removal) and from the study not publishing its exact aggregation rule."
)

# --------------------------------------------------------------- modelling
section("04", "Modelling: next-day forecast", "Time-ordered holdout evaluation.")
deployed_avg = metrics["average_deployed_r2"]
persist_avg = metrics["average_persistence_r2"]
m1, m2 = st.columns(2)
with m1:
    st.metric("Deployed ensemble (avg holdout R²)", f"{deployed_avg:.2f}")
with m2:
    st.metric(
        "Persistence benchmark (avg R²)",
        f"{persist_avg:.2f}",
        delta=f"{deployed_avg - persist_avg:+.2f}",
    )

note(
    "Model: next-day daily mean PM2.5 / PM10 from today's concentration, a 7-day rolling "
    "average, weather (temperature, humidity, pressure, wind speed/direction) and seasonality "
    "(month + day of week). Ridge + Random Forest + Gradient Boosting are averaged into the "
    "deployed ensemble. The holdout is the last 20% of days per city, never used in training."
)

rec_table = []
for key, rec in metrics["models"].items():
    deployed = rec["models"]["Ensemble (deployed)"]
    rec_table.append(
        {
            "City / pollutant": key,
            "Deployed R²": f"{deployed['r2']:.2f}",
            "Persistence R²": f"{rec['models']['Persistence (today)']['r2']:.2f}",
            "MAE (µg/m³)": f"{deployed['mae']:.1f}",
            "Days tested": rec["test_rows"],
        }
    )
st.dataframe(pd.DataFrame(rec_table), use_container_width=True, hide_index=True)

note(
    "Skill is modest (R² ≈ 0.2–0.65 depending on city) and close to zero for Anyigba, where "
    "day-to-day variation is driven by sources the weather features do not capture. These "
    "results, including the low-skill rural site, are reported in full on the Forecast Lab "
    "page. The random-split R² figures from the original notebooks (0.71–0.89) are not "
    "comparable with a true forecast and are shown only as context. Uncertainty bands are the "
    "10th–90th percentile spread of the random-forest trees."
)

# --------------------------------------------------------------- limitations
section("05", "Limitations", "What this app does not claim.")
for text in [
    "Observational sensor data, not regulatory-grade monitoring. PurpleAir PM2.5 can read high in humid conditions; no correction was applied so the record stays comparable to the study.",
    "AQI is computed from PM only (no O₃, NO₂, SO₂, CO in the source files), so it under-represents total pollution on some days.",
    "Live Open-Meteo readings are independent of the 2021–2023 study and shown only as today's context.",
    "The forecast is a statistical nowcast, not a health advisory or an official alert.",
    "Anyigba (rural) has only ~69% PM2.5 coverage, so its statistics are noisier than the cities'.",
]:
    st.markdown(f"• {text}")

# --------------------------------------------------------------- references
section("06", "References & reproducibility")
st.markdown(
    """
- Odubanjo et al. (2024), *Journal of the Nigerian Society of Physical Sciences* 6, 2120 (source study and data).
- US EPA AQI breakpoints (current and 2006 study tables), defined in `src/config.py`.
- WHO 2021 24-hour guidelines: PM2.5 15 µg/m³, PM10 45 µg/m³.
- Live conditions: Open-Meteo Air Quality API (no API key).
- Code: `scripts/build_dataset.py`, `scripts/train_models.py`, `src/` and `app.py` in this repository.
    """,
    unsafe_allow_html=False,
)

footer()
