"""Sama: Nigeria Air Quality Observatory.

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
import streamlit.components.v1 as components  # noqa: E402

from src.theme import inject_css  # noqa: E402

st.set_page_config(
    page_title="Sama · Nigeria Air Quality Observatory",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="auto",
)

inject_css()

# Streamlit keeps the sidebar open after a page change. On phones the sidebar is
# an overlay that covers the content, so collapse it once a destination is picked.
# The script runs inside a one-pixel component iframe and reaches the app document
# through the parent window.
components.html(
    """
<script>
(function () {
  const doc = window.parent.document;
  const win = window.parent;
  if (win.__samaSidebarNavBound) return;
  win.__samaSidebarNavBound = true;

  doc.addEventListener(
    "click",
    function (event) {
      const link =
        event.target.closest && event.target.closest('[data-testid="stSidebarNavLink"]');
      if (!link) return;
      if (!win.matchMedia("(max-width: 768px)").matches) return;

      // The collapse control is re-rendered after navigation, so retry briefly.
      let attempts = 0;
      function collapseSidebar() {
        const button = doc.querySelector(
          '[data-testid="stSidebarCollapseButton"] button'
        );
        if (button) {
          button.click();
          return;
        }
        if (attempts++ < 20) win.setTimeout(collapseSidebar, 60);
      }
      collapseSidebar();
    },
    false
  );
})();
</script>
""",
    height=1,
)

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
