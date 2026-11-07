"""Forecast Lab — next-day PM2.5 / PM10 outlook from today's air and weather."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from src.theme import page_header, kpi, section, note, footer
from src.data import load_daily, load_metrics, load_model
from src.model import features_from_inputs
from src.charts import model_scatter, model_leaderboard, importance_bars, aqi_gauge
from src.config import CITY_ORDER
from src.aqi import aqi_from_concentration, aqi_category, aqi_color

daily = load_daily()
metrics = load_metrics()

page_header(
    "PAGE 03 · FORECAST LAB",
    "Tomorrow's air, from today's readings",
    "Given today's concentration, a recent weekly average and tomorrow's weather, the model "
    "forecasts the next 24-hour mean PM2.5 or PM10. Trained with a time-ordered holdout "
    "(last 20% of days never seen in training) — no random-split flattery.",
)

# ------------------------------------------------------------------ model choice
c1, c2 = st.columns([0.5, 0.5], gap="large")
with c1:
    city = st.selectbox("City", CITY_ORDER, index=0, key="fc_city")
with c2:
    pollutant = st.radio(
        "Pollutant",
        ["pm25", "pm10"],
        format_func=lambda p: "PM2.5" if p == "pm25" else "PM10",
        horizontal=True,
        key="fc_poll",
    )
label = "PM2.5" if pollutant == "pm25" else "PM10"

key = f"{city}|{label}"
record = metrics["models"].get(key)
if record is None:
    st.error(f"No trained model for {city} / {label}. Run `python scripts/train_models.py`.")
    st.stop()

bundle = load_model(city, pollutant)
if bundle is None:
    st.error("Model bundle missing.")
    st.stop()

# --------------------------------------------------------------- model report card
deployed = record["models"]["Ensemble (deployed)"]
persistence = record["models"]["Persistence (today)"]
median_base = record["models"]["Median baseline"]

section("00", f"{record['city']} · {record['pollutant']} forecast model", "Honest holdout performance.")
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    kpi("Deployed model", "Ensemble", "Ridge + RF + GB", compact=True)
with m2:
    kpi(
        "Holdout R²",
        f"{deployed['r2']:.2f}",
        f"RMSE {deployed['rmse']:.1f}",
    )
with m3:
    kpi("Vs persistence", f"{persistence['r2']:.2f}", "tomorrow = today")
with m4:
    kpi("Vs median", f"{median_base['r2']:.2f}", "city median")
with m5:
    kpi(
        "80% band",
        f"{record['interval_coverage_pct']:.0f}%",
        "holdout coverage",
    )

st.caption(
    f"Trained on {record['train_rows']} days ({record['train_end']}), tested on {record['test_rows']} days "
    f"({record['test_start']} to {record['test_end']}). The notebooks' random-split R² figures "
    f"(up to ~0.89) are not comparable — this is a genuine forecast task."
)

# --------------------------------------------------------------- input form
section("01", "Set tomorrow's scenario", "Sliders default to this city's observed medians.")
city_daily = daily[daily["city"] == city].dropna(subset=[pollutant])
med_today = float(city_daily[pollutant].median())
pmax = float(np.percentile(city_daily[pollutant], 99.5))

with st.form("forecast_form"):
    f1, f2, f3 = st.columns(3)
    with f1:
        today = st.slider(
            f"Today's {label} (µg/m³)",
            0.0,
            round(pmax, 1),
            med_today,
            0.5,
            help="Most recent 24-hour mean.",
        )
        week_avg = st.slider(
            "7-day average (µg/m³)",
            0.0,
            round(pmax, 1),
            med_today,
            0.5,
            help="Rolling mean feeding the persistence features.",
        )
        temp = st.slider("Temperature (°C)", 15.0, 40.0, 27.5, 0.5)
    with f2:
        hum = st.slider("Relative humidity (%)", 30.0, 100.0, 78.0, 1.0)
        pres = st.slider("Pressure (hPa)", 960.0, 1030.0, 1012.0, 1.0)
        wind_spd = st.slider("Wind speed (m/s)", 0.0, 10.0, 2.5, 0.5)
    with f3:
        wind_dir = st.slider("Wind direction (°)", 0, 360, 180, 15)
        month = st.selectbox(
            "Month",
            list(range(1, 13)),
            index=date.today().month - 1,
            format_func=lambda m: date(2000, m, 1).strftime("%B"),
        )
        dow = st.selectbox(
            "Day of week",
            list(range(7)),
            index=2,
            format_func=lambda d: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d],
        )
    submitted = st.form_submit_button("Forecast tomorrow", type="primary")

# --------------------------------------------------------------- prediction output
if submitted:
    X = features_from_inputs(today, week_avg, temp, hum, pres, wind_spd, wind_dir, month, dow)
    point, low, high = bundle.predict(X)
    point = max(point, 0.0)
    low = max(low, 0.0)
    aqi_point = float(aqi_from_concentration([point], pollutant)[0])
    aqi_low = float(aqi_from_concentration([low], pollutant)[0]) if low is not None else np.nan
    aqi_high = float(aqi_from_concentration([high], pollutant)[0]) if high is not None else np.nan
    cat = aqi_category(aqi_point)
    color = aqi_color(aqi_point)

    st.markdown(
        f"""
        <div style="border:1px solid rgba(255,255,255,0.09);border-radius:20px;padding:1.4rem 1.5rem;background:linear-gradient(160deg,rgba(17,38,30,0.85) 0%,rgba(8,21,16,0.7) 100%);margin:1rem 0">
          <div style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap">
            <div style="flex:1;min-width:220px">
              <div style="font-size:0.7rem;letter-spacing:0.13em;text-transform:uppercase;color:#92A89E;font-weight:600">Forecast — tomorrow's mean {label}</div>
              <div style="font-family:'Sora',sans-serif;font-size:3.2rem;font-weight:600;letter-spacing:-0.03em">{point:.1f}</div>
              <div style="font-size:0.85rem;color:#8FA79E">µg/m³  ·  AQI <b style="color:{color}">{aqi_point:.0f} — {cat}</b></div>
            </div>
            <div style="flex:0 0 250px">
              <div style="font-size:0.7rem;letter-spacing:0.13em;text-transform:uppercase;color:#92A89E;font-weight:600">80% uncertainty band</div>
              <div style="font-family:'Sora',sans-serif;font-size:2rem;font-weight:600">{low:.1f} – {high:.1f}</div>
              <div style="font-size:0.85rem;color:#8FA79E">µg/m³  (AQI ≈ {aqi_low:.0f} – {aqi_high:.0f})</div>
            </div>
            <div style="flex:0 0 220px">
              <div style="font-size:0.7rem;letter-spacing:0.13em;text-transform:uppercase;color:#92A89E;font-weight:600">Vs today ({today:.1f} µg/m³)</div>
              <div style="font-family:'Sora',sans-serif;font-size:2rem;font-weight:600;color:{color}">
                {point - today:+.1f} µg/m³
              </div>
              <div style="font-size:0.85rem;color:#8FA79E">{"worse" if point > today else "better" if point < today else "unchanged"} air quality expected</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    g1, g2 = st.columns([0.42, 0.58], gap="large")
    with g1:
        with st.container(border=True):
            st.plotly_chart(aqi_gauge(aqi_point), use_container_width=True)
    with g2:
        with st.container(border=True):
            st.caption("What drives this forecast (permutation importance on the holdout set).")
            st.plotly_chart(importance_bars(record), use_container_width=True)

    # validation scatter for this model
    preds = pd.read_parquet(Path(__file__).resolve().parents[1] / "models" / "validation_predictions.parquet")
    mine = preds[(preds["city"] == city) & (preds["pollutant"] == label)]
    section("02", "Holdout validation", "Actual vs predicted on the unseen 20% of days.")
    v1, v2 = st.columns(2, gap="large")
    with v1:
        with st.container(border=True):
            st.plotly_chart(model_scatter(mine), use_container_width=True)
    with v2:
        with st.container(border=True):
            st.plotly_chart(model_leaderboard(record), use_container_width=True)

note(
    "Honest limitations: this is a weather-and-persistence forecast, not a chemistry model. "
    "Skill is modest for small towns (Anyigba) and weakest where day-to-day swings are driven "
    "by sources the weather cannot explain (fires, traffic episodes, generator use). "
    "Treat the band as directional guidance, never as a health advisory.",
)

footer()
