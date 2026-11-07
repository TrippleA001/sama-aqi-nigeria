"""Project-wide configuration: paths, city metadata and AQI definitions."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODEL_DIR = PROJECT_ROOT / "models"
ASSET_DIR = PROJECT_ROOT / "assets"

HOURLY_PATH = PROCESSED_DIR / "hourly.parquet"
DAILY_PATH = PROCESSED_DIR / "daily.parquet"
SUMMARY_PATH = PROCESSED_DIR / "summary.json"
METRICS_PATH = MODEL_DIR / "metrics.json"

STUDY_START = "2021-05-01"
STUDY_END = "2023-04-30"

# ---------------------------------------------------------------------------
# Cities
# ---------------------------------------------------------------------------
# `kind` drives the urban vs rural narrative. Anyigba is the rural /
# semi-urban comparator in the original study; the other four are cities.
CITIES = {
    "Lagos": {
        "name": "Lagos",
        "state": "Lagos State",
        "kind": "Urban",
        "lat": 6.5244,
        "lon": 3.3792,
        "population_m": 15.4,
        "blurb": "Nigeria's commercial megacity: traffic, ports, industry and dense residential energy use.",
        "source_file": "Reworked Lagos Hourly.xlsx",
        "source_sheet": "Lagos hourly conformed",
        "has_wind_direction": False,
    },
    "Abuja": {
        "name": "Abuja",
        "state": "Federal Capital Territory",
        "kind": "Urban",
        "lat": 9.0765,
        "lon": 7.3986,
        "population_m": 3.6,
        "blurb": "The federal capital: rapid construction, government fleets and a fast-growing population.",
        "source_file": "Abuja's Data.xlsx",
        "source_sheet": "Hourly",
        "has_wind_direction": True,
    },
    "Benin City": {
        "name": "Benin City",
        "state": "Edo State",
        "kind": "Urban",
        "lat": 6.3350,
        "lon": 5.6037,
        "population_m": 1.8,
        "blurb": "A historic southern city where traffic, biomass burning and artisanal refining overlap.",
        "source_file": "Benin City's Data.xlsx",
        "source_sheet": "Benin City Hourly",
        "has_wind_direction": True,
    },
    "Osogbo": {
        "name": "Osogbo",
        "state": "Osun State",
        "kind": "Urban",
        "lat": 7.7827,
        "lon": 4.5418,
        "population_m": 0.5,
        "blurb": "A growing state capital surrounded by agriculture, with traffic and biomass emissions.",
        "source_file": "Osogbo's Data.xlsx",
        "source_sheet": "Osogbo Hourly",
        "has_wind_direction": True,
    },
    "Anyigba": {
        "name": "Anyigba",
        "state": "Kogi State",
        "kind": "Rural",
        "lat": 7.5000,
        "lon": 7.1667,
        "population_m": 0.1,
        "blurb": "A semi-urban savanna town: the study's rural comparator, dominated by biomass and agricultural sources.",
        "source_file": "Anyigba's Data.xlsx",
        "source_sheet": "Anyigba Hourly",
        "has_wind_direction": True,
    },
}

CITY_ORDER = ["Lagos", "Abuja", "Benin City", "Osogbo", "Anyigba"]
URBAN_CITIES = [c for c in CITY_ORDER if CITIES[c]["kind"] == "Urban"]
RURAL_CITIES = [c for c in CITY_ORDER if CITIES[c]["kind"] == "Rural"]

# ---------------------------------------------------------------------------
# AQI
# ---------------------------------------------------------------------------
# US EPA breakpoints. `study` = 2006 table used in Odubanjo et al. (2024);
# `current` = the 2024 PM2.5 revision. PM10 is unchanged.
BREAKPOINTS = {
    "pm25": {
        "study": [
            (0.0, 15.4, 0, 50),
            (15.5, 40.4, 51, 100),
            (40.5, 65.4, 101, 150),
            (65.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300),
            (250.5, 350.4, 301, 400),
            (350.5, 500.4, 401, 500),
        ],
        "current": [
            (0.0, 9.0, 0, 50),
            (9.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150),
            (55.5, 125.4, 151, 200),
            (125.5, 225.4, 201, 300),
            (225.5, 325.4, 301, 400),
            (325.5, 500.4, 401, 500),
        ],
    },
    "pm10": {
        "study": [
            (0, 54, 0, 50),
            (55, 154, 51, 100),
            (155, 254, 101, 150),
            (255, 354, 151, 200),
            (355, 424, 201, 300),
            (425, 504, 301, 400),
            (505, 604, 401, 500),
        ],
        "current": [
            (0, 54, 0, 50),
            (55, 154, 51, 100),
            (155, 254, 101, 150),
            (255, 354, 151, 200),
            (355, 424, 201, 300),
            (425, 504, 301, 400),
            (505, 604, 401, 500),
        ],
    },
}

AQI_BANDS = [
    ("Good", 0, 50, "#3DDC97", "Air quality is satisfactory and poses little or no risk."),
    (
        "Moderate",
        51,
        100,
        "#F5D547",
        "Acceptable, though unusually sensitive people may feel effects.",
    ),
    (
        "Unhealthy for sensitive groups",
        101,
        150,
        "#FF9F45",
        "Sensitive groups may feel effects; the general public is less likely to.",
    ),
    (
        "Unhealthy",
        151,
        200,
        "#FF5D5D",
        "Everyone may begin to feel effects; sensitive groups feel them more strongly.",
    ),
    (
        "Very unhealthy",
        201,
        300,
        "#B06AB3",
        "Health alert: serious effects are possible for everyone.",
    ),
    ("Hazardous", 301, 500, "#C1465C", "Emergency conditions: everyone is at risk."),
]

AQI_COLORS = {name: color for name, _, _, color, _ in AQI_BANDS}

# WHO 2021 24-hour guideline values, used for exposure flags.
WHO_24H = {"pm25": 15.0, "pm10": 45.0}

# National standards used in the source study.
FMENV_24H = {"pm25": 40.0, "pm10": 150.0}
NAAQS_24H = {"pm25": 35.0, "pm10": 150.0}
