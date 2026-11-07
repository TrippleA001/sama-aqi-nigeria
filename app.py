"""Sama — Nigeria Air Quality Observatory.

Streamlit entry point. Configures the page, injects the dark environmental
theme and wires up `st.navigation` across five pages.

Run locally:

    streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

from src.theme import inject_css  # noqa: E402

st.set_page_config(
    page_title="Sama · Nigeria Air Quality Observatory",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="auto",
)

inject_css()

PAGES = [
    st.Page(
        "pages/1_overview.py",
        title="Overview",
        icon=":material/public:",
        default=True,
    ),
    st.Page(
        "pages/2_city_explorer.py",
        title="City Explorer",
        icon=":material/location_city:",
    ),
    st.Page(
        "pages/3_urban_rural.py",
        title="Urban vs Rural",
        icon=":material/compare_arrows:",
    ),
    st.Page(
        "pages/4_forecast.py",
        title="Forecast Lab",
        icon=":material/psychology:",
    ),
    st.Page("pages/5_method.py", title="Method", icon=":material/science:"),
]

pg = st.navigation(PAGES, position="sidebar")
pg.run()
