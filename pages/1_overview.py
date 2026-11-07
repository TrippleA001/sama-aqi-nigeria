"""Overview page — headline story, live conditions and study-area map."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src.theme import hero, kpi, section, note, footer
from src.data import load_daily, load_summary, city_cards, live_air_quality
from src.charts import city_map, urban_rural_bars, aqi_donut, concentration_timeseries
from src.config import CITY_ORDER, URBAN_CITIES

daily = load_daily()
summary = load_summary()
cards = city_cards(summary)
totals = summary["totals"]
uvr = summary["urban_vs_rural"]

hero(
    "SAMA · NIGERIA AIR OBSERVATORY",
    "Five cities.<br><span>One shared sky.</span>",
    "Two years of hourly PM2.5 and PM10 measurements from CAR-NASRDA PurpleAir sensors "
    "across Nigeria's four largest cities and its rural comparator, May 2021 – April 2023. "
    "Built from Odubanjo et al. (2024). AQI uses the US EPA scale; live readings come from "
    "Open-Meteo (no API key).",
    [
        "71,339 valid hours",
        f"{len(CITY_ORDER)} cities",
        "May 2021 – Apr 2023",
        "US EPA AQI",
        "Open-Meteo live",
    ],
)

# ------------------------------------------------------------------ headline KPIs
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    kpi(
        "Cities monitored",
        f"{len(CITY_ORDER)}",
        "4 urban · 1 rural comparator",
    )
with k2:
    kpi(
        "Days with data",
        f"{int(daily['date'].nunique()):,}",
        "Every day in the study window",
    )
with k3:
    kpi(
        "Urban vs Rural PM2.5",
        f"{uvr['ratio']:.2f}×",
        f"{uvr['urban_pm25_mean']:.1f} vs {uvr['rural_pm25_mean']:.1f} µg/m³",
    )
with k4:
    kpi(
        "Urban WHO exceedance",
        f"{uvr['urban_who_exceedance_pct']:.0f}%",
        "of city-days above 15 µg/m³",
    )
with k5:
    kpi(
        "Rural WHO exceedance",
        f"{uvr['rural_who_exceedance_pct']:.0f}%",
        "of Anyigba days above 15 µg/m³",
    )

# --------------------------------------------------------------- live conditions
section("00", "Live conditions", "Independent Open-Meteo readings — not part of the 2021–2023 study.")
try:
    live, error = live_air_quality()
    if error:
        st.warning(f"Live feed unavailable ({error}). Historical pages below still work.")
    cols = st.columns(5)
    for col, (_, row) in zip(cols, live.iterrows(), strict=False):
        with col:
            color = row["color"] or "#8A9A96"
            cat = row["category"] or "—"
            pm25 = "—" if pd.isna(row["pm25"]) else f"{row['pm25']:.1f}"
            pm10 = "—" if pd.isna(row["pm10"]) else f"{row['pm10']:.1f}"
            aqi_value = "—" if pd.isna(row["aqi"]) else f"{row['aqi']:.0f}"
            st.markdown(
                f"""
                <div class="kpi" style="border-color:{color}22">
                  <div class="kpi-label" style="color:{color};font-weight:700">{row["city"]}</div>
                  <div class="kpi-value" style="font-size:1.9rem">{aqi_value}</div>
                  <div class="kpi-sub" style="color:{color};font-weight:700">{cat}</div>
                  <div class="kpi-sub">PM2.5 {pm25} · PM10 {pm10} µg/m³</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
except Exception as exc:  # pragma: no cover - network dependent
    st.warning(f"Live feed unavailable ({exc}).")

# --------------------------------------------------------------- map + headline
section(
    "01",
    "Where the sensors are",
    "Study-area monitor locations, sized by mean PM2.5 and coloured by mean AQI.",
)
map_col, bars_col = st.columns([0.56, 0.44], gap="large")
with map_col:
    with st.container(border=True):
        st.plotly_chart(city_map(cards), use_container_width=True)
with bars_col:
    with st.container(border=True):
        st.plotly_chart(urban_rural_bars(cards), use_container_width=True)

# --------------------------------------------------------------- urban vs rural
section(
    "02",
    "The headline finding",
    "Urban air carries roughly 2.6× the fine-particle load of the rural comparator.",
)
left, right = st.columns([0.55, 0.45], gap="large")
with left:
    with st.container(border=True):
        st.plotly_chart(
            concentration_timeseries(daily[daily["city"].isin(URBAN_CITIES)], "pm25"),
            use_container_width=True,
        )
        st.caption("Urban 4-city average daily PM2.5 (7-day average line).")
with right:
    with st.container(border=True):
        st.plotly_chart(aqi_donut(daily), use_container_width=True)
        st.caption("Share of all city-days by EPA AQI category.")

note(
    "Takeaway: every urban city exceeds the WHO 24-hour PM2.5 guideline on most days "
    f"({uvr['urban_who_exceedance_pct']:.0f}% average), while the rural comparator stays "
    f"below it on most days ({100 - uvr['rural_who_exceedance_pct']:.0f}% of days compliant). "
    "This is the core story behind every other page in the app."
)

footer()
