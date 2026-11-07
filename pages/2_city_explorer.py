"""City Explorer — deep dive per city: time series, diurnal, monthly, calendar."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.theme import page_header, kpi, section, note, footer
from src.data import load_daily, load_hourly, city_frame, window, window_hourly
from src.charts import (
    concentration_timeseries,
    aqi_timeseries,
    diurnal_profile,
    monthly_bars,
    calendar_heatmap,
    wind_rose,
    city_distribution,
)
from src.config import CITIES, CITY_ORDER, AQI_COLORS, WHO_24H
from src.aqi import aqi_category

daily = load_daily()
hourly = load_hourly()

page_header(
    "PAGE 01 · CITY EXPLORER",
    "Explore one city in detail",
    "Pick a city, a pollutant and a date range. Charts below update together.",
)

city = st.selectbox("City", CITY_ORDER, index=0, key="city_pick")
pollutant = st.segmented_control(
    "Pollutant",
    options=["pm25", "pm10"],
    format_func=lambda p: "PM2.5 (fine)" if p == "pm25" else "PM10 (coarse)",
    default="pm25",
    key="poll_pick",
)
label = "PM2.5" if pollutant == "pm25" else "PM10"

city_daily = city_frame(daily, city)
city_hourly = hourly[hourly["city"] == city]

# Date range slider
dmin, dmax = city_daily["date"].min(), city_daily["date"].max()
start, end = st.date_input(
    "Date range",
    value=(dmin.date(), dmax.date()),
    min_value=dmin.date(),
    max_value=dmax.date(),
    key="date_pick",
)
frame = window(city_daily, start, end)
hframe = window_hourly(city_hourly, start, end)

if frame.empty:
    st.warning("No data in the selected window.")
    st.stop()

# --------------------------------------------------------------- city KPIs
pm_vals = frame[pollutant].dropna()
aqi_vals = frame["aqi"].dropna()
who = WHO_24H[pollutant]
exceed = (pm_vals > who).mean() * 100 if not pm_vals.empty else 0.0
worst = frame.loc[aqi_vals.idxmax()] if not aqi_vals.empty else None

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    kpi(f"Mean {label}", f"{pm_vals.mean():.1f}", f"µg/m³ over {len(pm_vals)} days")
with k2:
    kpi("Mean AQI", f"{aqi_vals.mean():.0f}", aqi_category(aqi_vals.mean()) or "—")
with k3:
    kpi("Peak AQI", f"{aqi_vals.max():.0f}", str(worst["date"].date()) if worst is not None else "—")
with k4:
    kpi("WHO exceedance", f"{exceed:.0f}%", f"of days above {who} µg/m³")
with k5:
    kpi(
        "Data coverage",
        f"{frame['coverage_pm25' if pollutant == 'pm25' else 'coverage_pm10'].mean() * 100:.0f}%",
        "hourly coverage avg",
    )

# --------------------------------------------------------------- charts row 1
section("02", f"{label} through time", "Daily mean concentration with the 7-day rolling average.")
t1, t2 = st.columns(2, gap="large")
with t1:
    with st.container(border=True):
        st.plotly_chart(concentration_timeseries(frame, pollutant), use_container_width=True)
with t2:
    with st.container(border=True):
        st.plotly_chart(aqi_timeseries(frame), use_container_width=True)

# --------------------------------------------------------------- charts row 2
section("03", "Daily rhythm & seasonal pattern", "Average concentration by hour of day and by month.")
c1, c2 = st.columns(2, gap="large")
with c1:
    with st.container(border=True):
        st.plotly_chart(diurnal_profile(hframe, pollutant), use_container_width=True)
        st.caption("Hourly average with 25th–75th percentile band.")
with c2:
    with st.container(border=True):
        st.plotly_chart(monthly_bars(frame, pollutant), use_container_width=True)
        st.caption("Monthly mean; WHO guideline shown as dotted line.")

section("04", "Calendar view & distribution", "Each cell is one day, coloured by concentration.")
d1, d2 = st.columns(2, gap="large")
with d1:
    with st.container(border=True):
        st.plotly_chart(calendar_heatmap(frame, pollutant), use_container_width=True)
        st.caption("Weeks × weekdays; colour scaled to the 98th percentile of this window.")
with d2:
    with st.container(border=True):
        st.plotly_chart(city_distribution(daily, pollutant), use_container_width=True)
        st.caption("This city's daily distribution against all five cities.")

# --------------------------------------------------------------- wind rose
if CITIES[city]["has_wind_direction"] and not hframe.empty:
    section("05", "Where the air comes from", "Mean concentration by wind direction (where measured).")
    rose = wind_rose(hframe, pollutant)
    if rose is not None:
        with st.container(border=True):
            st.plotly_chart(rose, use_container_width=True)
    else:
        st.info("No usable wind data in this window.")
else:
    st.info(f"Wind direction is not recorded for {city} in the source file.")

# --------------------------------------------------------------- worst days table
section("06", "Most polluted days", "Top ten days in the selected window.")
worst_days = frame.nlargest(10, pollutant)[
    ["date", pollutant, "aqi", "category", "temp_c", "humidity_pct", "wind_speed_ms"]
]
worst_days = worst_days.rename(
    columns={
        "date": "Date",
        pollutant: f"{label} (µg/m³)",
        "aqi": "AQI",
        "category": "Category",
        "temp_c": "Temp (°C)",
        "humidity_pct": "Humidity (%)",
        "wind_speed_ms": "Wind (m/s)",
    }
)
worst_days["Date"] = worst_days["Date"].dt.strftime("%d %b %Y")
worst_days["Category"] = worst_days["Category"].apply(
    lambda c: f"<span style='color:{AQI_COLORS.get(c, '#8A9A96')}'>{c}</span>"
)
st.markdown(
    worst_days.to_html(escape=False, index=False),
    unsafe_allow_html=True,
)

note(
    "Source: CAR-NASRDA PurpleAir record, cleaned per the pipeline in `scripts/build_dataset.py`. "
    "PM values are never interpolated; a day needs ≥18 valid hours (75% rule) to receive an AQI."
)

footer()
