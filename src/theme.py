"""Visual system: palette, CSS, hero and small HTML components."""

from __future__ import annotations

import streamlit as st

from .config import AQI_BANDS

INK = "#E9F1ED"
MUTED = "#92A89E"
ACCENT = "#6EE7B7"
BG = "#06110D"


def inject_css() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg: #06110D;
  --bg-2: #0A1A14;
  --card: rgba(13, 29, 23, 0.72);
  --line: rgba(233, 241, 237, 0.09);
  --line-strong: rgba(233, 241, 237, 0.16);
  --ink: #E9F1ED;
  --muted: #92A89E;
  --accent: #6EE7B7;
  --accent-soft: rgba(110, 231, 183, 0.12);
  --amber: #FFB86B;
}

html, body, [class*="css"] {
  font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--ink);
}
.stApp {
  background:
    radial-gradient(1100px 700px at 8% -8%, rgba(33, 94, 72, 0.55) 0%, transparent 58%),
    radial-gradient(900px 600px at 96% 2%, rgba(34, 64, 52, 0.38) 0%, transparent 48%),
    radial-gradient(700px 500px at 60% 100%, rgba(16, 49, 38, 0.45) 0%, transparent 60%),
    var(--bg);
  background-attachment: fixed;
}
[data-testid="stHeader"] {
  background: rgba(6, 17, 13, 0.72);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--line);
}
[data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
[data-testid="stToolbar"] { background: transparent !important; }
/* Keep the sidebar expand control reachable after collapsing the nav. */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  z-index: 1000000 !important;
}
.block-container {
  padding: 1.4rem 1.6rem 3.5rem 1.6rem;
  max-width: 1280px;
}
h1, h2, h3, h4 { font-family: 'Sora', sans-serif; letter-spacing: -0.03em; color: var(--ink); }
p, li, div { line-height: 1.65; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
::selection { background: rgba(110, 231, 183, 0.28); color: #fff; }

/* ---------- top navigation ---------- */
[data-testid="stNavSection"] { gap: 4px; }
[data-testid="stNavLink"] {
  font-family: 'Manrope', sans-serif !important;
  font-size: 0.84rem !important;
  letter-spacing: 0.01em;
  border-radius: 999px !important;
  padding: 6px 13px !important;
  color: var(--muted) !important;
}
[data-testid="stNavLink"]:hover { color: var(--ink) !important; background: rgba(255,255,255,0.04) !important; }
[data-testid="stNavLink"][aria-current="page"] {
  color: #06110D !important;
  background: var(--accent) !important;
  font-weight: 700 !important;
}
[data-testid="stSidebar"] { background: #081611; border-right: 1px solid var(--line); }
[data-testid="stSidebarNavLink"] {
  border-radius: 10px !important;
  padding: 9px 12px !important;
  font-size: 0.9rem !important;
}
[data-testid="stSidebarNavLink"]:hover { background: rgba(255,255,255,0.045) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: var(--accent) !important;
  color: #06110D !important;
  font-weight: 700 !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: #06110D !important; }
[data-testid="stSidebarNavLink"] span { white-space: nowrap; }

/* ---------- hero ---------- */
.hero {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 30px;
  padding: 3.1rem 3rem 2.6rem 3rem;
  margin: 0.4rem 0 1.5rem 0;
  background:
    linear-gradient(120deg, rgba(15, 42, 33, 0.92) 0%, rgba(8, 25, 19, 0.78) 48%, rgba(12, 36, 28, 0.9) 100%);
  box-shadow: 0 30px 80px -40px rgba(0, 0, 0, 0.9), inset 0 1px 0 rgba(255,255,255,0.05);
}
.hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.028) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(circle at 70% 20%, black, transparent 72%);
  pointer-events: none;
}
.hero::after {
  content: "";
  position: absolute;
  right: -140px;
  top: -190px;
  width: 520px;
  height: 520px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(110,231,183,0.22) 0%, rgba(110,231,183,0.04) 45%, transparent 68%);
  filter: blur(6px);
  pointer-events: none;
}
.hero > * { position: relative; z-index: 1; }
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 1.35rem;
}
.pulse {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(110, 231, 183, 0.55);
  animation: pulse 2.4s infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(110,231,183,0.55); }
  70% { box-shadow: 0 0 0 11px rgba(110,231,183,0); }
  100% { box-shadow: 0 0 0 0 rgba(110,231,183,0); }
}
.hero h1 {
  font-size: clamp(2.6rem, 6.2vw, 5.1rem);
  line-height: 0.97;
  font-weight: 600;
  margin: 0 0 1.15rem 0;
  max-width: 900px;
}
.hero h1 span {
  background: linear-gradient(95deg, #6EE7B7 0%, #C6F6E4 45%, #FFD9A8 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.lede {
  font-size: 1.06rem;
  color: #B9CCC3;
  max-width: 680px;
  margin: 0 0 1.6rem 0;
  font-weight: 400;
}
.hero-meta { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line-strong);
  background: rgba(255,255,255,0.035);
  color: #CBDAD3;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.76rem;
  font-weight: 500;
  white-space: nowrap;
}
.chip b { color: var(--ink); font-weight: 700; }
.chip.accent { border-color: rgba(110,231,183,0.35); color: var(--accent); background: rgba(110,231,183,0.07); }

/* ---------- page header ---------- */
.page-head { padding: 0.6rem 0 1.1rem 0; border-bottom: 1px solid var(--line); margin-bottom: 1.4rem; }
.page-head .eyebrow { margin-bottom: 0.75rem; }
.page-head h1 { font-size: clamp(2rem, 4vw, 3.15rem); margin: 0 0 0.55rem 0; font-weight: 600; }
.page-head p { color: var(--muted); max-width: 760px; margin: 0; font-size: 0.98rem; }

/* ---------- KPI cards ---------- */
.kpi {
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 1.05rem 1rem 1rem 1rem;
  background: linear-gradient(160deg, rgba(17, 38, 30, 0.85) 0%, rgba(9, 24, 18, 0.7) 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
  min-height: 124px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.kpi-label {
  font-size: 0.66rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
  word-break: keep-all;
  overflow-wrap: normal;
}
.kpi-value {
  font-family: 'Sora', sans-serif;
  font-size: clamp(1.35rem, 2.3vw, 2.05rem);
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.045em;
  margin: 0.55rem 0 0.3rem 0;
  word-break: keep-all;
  overflow-wrap: normal;
}
.kpi-value small { font-size: 0.9rem; color: var(--muted); font-weight: 500; letter-spacing: 0; }
.kpi-value--text { font-size: clamp(1.05rem, 1.7vw, 1.45rem); letter-spacing: -0.02em; line-height: 1.15; }
.kpi-sub { font-size: 0.76rem; color: var(--muted); }
.kpi-sub b { color: var(--accent); font-weight: 600; }
.kpi-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 6px; }

/* ---------- section heading ---------- */
.section-head { display: flex; gap: 14px; align-items: flex-start; margin: 2.1rem 0 0.9rem 0; }
.section-index {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: var(--accent);
  border: 1px solid rgba(110,231,183,0.3);
  background: rgba(110,231,183,0.06);
  padding: 3px 7px;
  border-radius: 7px;
  margin-top: 4px;
}
.section-head h2 { font-size: 1.32rem; margin: 0; font-weight: 600; }
.section-head p { margin: 2px 0 0 0; color: var(--muted); font-size: 0.88rem; }

/* ---------- cards around charts ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(165deg, rgba(14, 31, 24, 0.78) 0%, rgba(8, 21, 16, 0.62) 100%);
  border: 1px solid var(--line) !important;
  border-radius: 22px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.035), 0 18px 50px -40px #000;
}
[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 0.35rem 0.55rem; }

/* ---------- widgets ---------- */
label, [data-testid="stWidgetLabel"] p {
  color: #B7C9C1 !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.01em;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
.stDateInput input,
.stNumberInput input {
  background: rgba(255,255,255,0.035) !important;
  border: 1px solid var(--line-strong) !important;
  border-radius: 12px !important;
  color: var(--ink) !important;
}
div[data-baseweb="select"] > div:hover { border-color: rgba(110,231,183,0.45) !important; }
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background: var(--accent) !important;
  box-shadow: 0 0 0 4px rgba(110,231,183,0.16) !important;
}
.stSlider [data-testid="stTickBar"] { display: none; }
.stButton > button, .stDownloadButton > button {
  border-radius: 999px !important;
  border: 1px solid rgba(110,231,183,0.35) !important;
  background: rgba(110,231,183,0.1) !important;
  color: #C9F7E5 !important;
  font-weight: 700 !important;
  font-size: 0.8rem !important;
  padding: 0.42rem 1rem !important;
  transition: all 0.18s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  background: var(--accent) !important;
  color: #06110D !important;
  border-color: var(--accent) !important;
}
.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  color: #06110D !important;
}
.stSelectbox [data-testid="stMarkdownContainer"] p { color: var(--ink) !important; }

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--line);
  padding: 5px;
  border-radius: 999px;
  width: fit-content;
  margin-bottom: 0.9rem;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 999px;
  padding: 7px 15px;
  height: auto;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 600;
}
.stTabs [aria-selected="true"] { background: var(--accent-soft) !important; color: #B9F6DF !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* ---------- dataframes ---------- */
[data-testid="stDataFrame"] {
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
}
[data-testid="stDataFrame"] * { font-family: 'Manrope', sans-serif !important; }

/* ---------- misc ---------- */
.legend { display: flex; flex-wrap: wrap; gap: 7px; margin: 0.2rem 0 0.8rem 0; }
.legend span {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 0.72rem; color: #A9BDB4;
  border: 1px solid var(--line); border-radius: 999px;
  padding: 4px 9px; background: rgba(255,255,255,0.02);
}
.legend i { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.note {
  border-left: 2px solid rgba(110,231,183,0.55);
  padding: 0.15rem 0 0.15rem 1rem;
  color: var(--muted);
  font-size: 0.86rem;
  margin: 0.5rem 0 1rem 0;
}
.note b { color: var(--ink); }
.source {
  color: #6F857B; font-size: 0.72rem; letter-spacing: 0.01em;
}
.footer {
  margin-top: 3rem; padding-top: 1.3rem; border-top: 1px solid var(--line);
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 1rem;
  color: #6F857B; font-size: 0.74rem;
}
.footer b { color: #A9BDB4; }
.footer a {
  color: #A9BDB4;
  border-bottom: 1px solid rgba(110, 231, 183, 0.35);
  padding-bottom: 1px;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.footer a:hover {
  color: var(--accent);
  border-color: var(--accent);
  text-decoration: none;
}
.mono { font-family: 'JetBrains Mono', monospace; }
.muted { color: var(--muted); }
.small { font-size: 0.8rem; }
.divider { height: 1px; background: var(--line); margin: 1.4rem 0; }
.hl { color: var(--accent); }
.warn { color: var(--amber); }
.quote {
  font-family: 'Sora', sans-serif; font-size: 1.28rem; line-height: 1.45;
  font-weight: 400; letter-spacing: -0.02em; color: #D7E5DE;
  border-left: 2px solid var(--accent); padding-left: 1.1rem; margin: 0.5rem 0 1rem 0;
}
.bar-track { height: 6px; border-radius: 999px; background: rgba(255,255,255,0.07); overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #6EE7B7, #C6F6E4); }

/* Streamlit's own spacing tweaks */
[data-testid="stHorizontalBlock"] { gap: 0.9rem; }
/* The one-pixel helper frame only carries the mobile navigation script. */
[data-testid="stIFrame"] { display: none !important; }
hr { border-color: var(--line); }

/* ---------- responsive ---------- */
@media (max-width: 1024px) {
  /* KPI rows go two-up once the content column gets tight. */
  [data-testid="stHorizontalBlock"]:has(.kpi) { flex-wrap: wrap; }
  [data-testid="stHorizontalBlock"]:has(.kpi) > [data-testid="stColumn"] {
    flex: 0 1 calc(50% - 0.9rem) !important;
    width: calc(50% - 0.9rem) !important;
    min-width: calc(50% - 0.9rem) !important;
  }
  .kpi-value { font-size: clamp(1.3rem, 2.6vw, 1.9rem); }
  .footer { flex-direction: column; gap: 0.45rem; }
}

@media (max-width: 780px) {
  .block-container { padding: 0.9rem 0.85rem 2.5rem 0.85rem; }
  .hero { padding: 1.6rem 1.2rem 1.4rem 1.2rem; border-radius: 20px; }
  .hero h1 { font-size: clamp(1.85rem, 8.5vw, 2.6rem); }
  .hero p { font-size: 0.92rem; }
  .kpi { padding: 0.85rem 0.85rem 0.8rem 0.85rem; min-height: auto; border-radius: 16px; }
  .kpi-label { font-size: 0.6rem; letter-spacing: 0.06em; }
  .kpi-value { font-size: 1.6rem; }
  .kpi-value--text { font-size: 1.15rem; }
  .kpi-sub { font-size: 0.7rem; }
  .section-head { margin: 1.5rem 0 0.75rem 0; }
  .section-head h2 { font-size: 1.15rem; }
  .section-head p { font-size: 0.82rem; }
  .page-head h1 { font-size: clamp(1.7rem, 7vw, 2.2rem); }
  .page-head p { font-size: 0.9rem; }
  .footer { font-size: 0.68rem; }
  /* Stack Streamlit columns so cards and charts stay readable on phones. */
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 100% !important;
  }
  /* Let wide tables scroll instead of breaking the layout. */
  .stMarkdown table { display: block; overflow-x: auto; white-space: nowrap; }
}
</style>
""",
        unsafe_allow_html=True,
    )


def hero(
    eyebrow: str,
    title_html: str,
    lede: str,
    chips: list[str],
) -> None:
    chip_html = "".join(f'<span class="chip">{chip}</span>' for chip in chips)
    st.markdown(
        f"""
<section class="hero">
  <div class="eyebrow"><span class="pulse"></span>{eyebrow}</div>
  <h1>{title_html}</h1>
  <p class="lede">{lede}</p>
  <div class="hero-meta">{chip_html}</div>
</section>
""",
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, description: str) -> None:
    st.markdown(
        f"""
<div class="page-head">
  <div class="eyebrow"><span class="pulse"></span>{eyebrow}</div>
  <h1>{title}</h1>
  <p>{description}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def kpi(
    label: str,
    value: str,
    sub: str = "",
    color: str | None = None,
    compact: bool = False,
) -> None:
    dot = f'<span class="kpi-dot" style="background:{color}"></span>' if color else ""
    value_class = "kpi-value kpi-value--text" if compact else "kpi-value"
    st.markdown(
        f"""
<div class="kpi">
  <div class="kpi-label">{dot}{label}</div>
  <div class="{value_class}">{value}</div>
  <div class="kpi-sub">{sub}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def section(index: str, title: str, description: str = "") -> None:
    st.markdown(
        f"""
<div class="section-head">
  <span class="section-index">{index}</span>
  <div><h2>{title}</h2>{f"<p>{description}</p>" if description else ""}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def legend() -> None:
    items = "".join(f'<span><i style="background:{color}"></i>{name}</span>' for name, _, _, color, _ in AQI_BANDS)
    st.markdown(f'<div class="legend">{items}</div>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def footer() -> None:
    st.markdown(
        """
<div class="footer">
  <div>
    <b>SAMA</b> · Nigeria Air Quality Observatory · Built from the
    <a href="https://doi.org/10.46481/jnsps.2024.2120" target="_blank" rel="noopener">CAR-NASRDA / PurpleAir record, 2021–2023</a>.
  </div>
  <div>
    Data: <a href="https://doi.org/10.46481/jnsps.2024.2120" target="_blank" rel="noopener">Odubanjo et al. (2024)</a>
    · AQI: <a href="https://www.airnow.gov/aqi/aqi-basics/" target="_blank" rel="noopener">US EPA</a>
    · Live: <a href="https://open-meteo.com/" target="_blank" rel="noopener">Open-Meteo</a>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
