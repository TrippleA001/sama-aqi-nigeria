"""Urban vs Rural — the headline comparison across the study."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import streamlit as st

from src.theme import page_header, kpi, section, note, footer
from src.data import load_daily, city_cards, load_summary
from src.charts import (
    urban_rural_bars,
    season_compare,
    aqi_donut,
    city_distribution,
)
from src.config import URBAN_CITIES, RURAL_CITIES, WHO_24H

daily = load_daily()
summary = load_summary()
cards = city_cards(summary)
uvr = summary["urban_vs_rural"]

page_header(
    "PAGE 02 · URBAN VS RURAL",
    "The city–countryside divide",
    "Four urban cities (Lagos, Abuja, Benin City, Osogbo) against the rural comparator Anyigba.",
)

# --------------------------------------------------------------- headline KPIs
k1, k2, k3, k4 = st.columns(4)
with k1:
    kpi("Urban PM2.5 mean", f"{uvr['urban_pm25_mean']:.1f}", "µg/m³, 4-city average")
with k2:
    kpi("Rural PM2.5 mean", f"{uvr['rural_pm25_mean']:.1f}", "µg/m³, Anyigba")
with k3:
    kpi("Urban : Rural ratio", f"{uvr['ratio']:.2f}×", "fine particles in urban air")
with k4:
    kpi(
        "Mean AQI gap",
        f"{uvr['urban_aqi_mean'] - uvr['rural_aqi_mean']:.0f}",
        "AQI points urban minus rural",
    )

# --------------------------------------------------------------- bars + donut
section(
    "01",
    "Mean daily PM2.5 by city",
    "Bars coloured by kind; dashed line marks the rural comparator.",
)
b1, b2 = st.columns([0.52, 0.48], gap="large")
with b1:
    with st.container(border=True):
        st.plotly_chart(urban_rural_bars(cards), use_container_width=True)
with b2:
    with st.container(border=True):
        st.plotly_chart(aqi_donut(daily[daily["city"].isin(URBAN_CITIES)]), use_container_width=True)
        st.caption("Urban cities only — share of city-days by EPA AQI category.")

# --------------------------------------------------------------- seasonality
section("02", "Seasonal pattern by kind", "Dry season (Nov–Mar) vs rainy season (Apr–Oct), all cities.")
s1, s2 = st.columns(2, gap="large")
with s1:
    with st.container(border=True):
        st.plotly_chart(season_compare(daily, "pm25"), use_container_width=True)
        st.caption("Grouped bars by city and season.")
with s2:
    with st.container(border=True):
        st.plotly_chart(season_compare(daily, "pm10"), use_container_width=True)
        st.caption("PM10 follows the same dry-season rhythm.")

# --------------------------------------------------------------- distribution
section("03", "Daily distributions", "Each violin is one city's daily concentrations across the study.")
with st.container(border=True):
    st.plotly_chart(city_distribution(daily, "pm25"), use_container_width=True)
    st.caption("WHO 24-hour PM2.5 guideline (15 µg/m³) shown as dotted line.")

# --------------------------------------------------------------- comparison table
section("04", "By the numbers", "Study-period means and guideline exceedance.")
urban_daily = daily[daily["city"].isin(URBAN_CITIES)]
rural_daily = daily[daily["city"].isin(RURAL_CITIES)]


def agg(frame, kind_label):
    return {
        "kind": kind_label,
        "pm25_mean": frame["pm25"].mean(),
        "pm10_mean": frame["pm10"].mean(),
        "aqi_mean": frame["aqi"].mean(),
        "who_pm25": (frame["pm25"] > WHO_24H["pm25"]).mean() * 100,
        "who_pm10": (frame["pm10"] > WHO_24H["pm10"]).mean() * 100,
        "fmenv_pm25": (frame["pm25"] > 40).mean() * 100,
        "days": int(frame["aqi"].notna().sum()),
    }


rows = [agg(urban_daily, "Urban (4 cities)"), agg(rural_daily, "Rural (Anyigba)")]
table = pd.DataFrame(rows)
table["ratio"] = [np.nan, table.loc[0, "pm25_mean"] / table.loc[1, "pm25_mean"]]
fmt = {
    "kind": "Group",
    "pm25_mean": "PM2.5 mean (µg/m³)",
    "pm10_mean": "PM10 mean (µg/m³)",
    "aqi_mean": "Mean AQI",
    "who_pm25": "WHO PM2.5 exceedance",
    "who_pm10": "WHO PM10 exceedance",
    "fmenv_pm25": "FMENV PM2.5 > 40 exceedance",
    "days": "Days with AQI",
    "ratio": "Urban : Rural",
}
styled = table.rename(columns=fmt).set_index("Group").T
for c in styled.columns:
    styled[c] = styled[c].map(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
st.dataframe(styled, use_container_width=True, hide_index=False)

note(
    "FMENV = Nigeria's Federal Ministry of Environment 24-hour PM2.5 standard (40 µg/m³). "
    "Urban cities exceed the WHO guideline on nearly every day with data; Anyigba exceeds it "
    "on roughly one day in four."
)

footer()
