"""US EPA Air Quality Index helpers (vectorised)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AQI_BANDS, AQI_COLORS, BREAKPOINTS, WHO_24H


def _prepare(conc, pollutant: str) -> np.ndarray:
    c = np.asarray(conc, dtype="float64")
    decimals = 1 if pollutant == "pm25" else 0
    factor = 10**decimals
    # EPA truncates rather than rounds the concentration before indexing.
    return np.floor(c * factor) / factor


def aqi_from_concentration(conc, pollutant: str = "pm25", standard: str = "current") -> np.ndarray:
    """Convert a PM concentration (µg/m³) to a US EPA AQI value.

    Parameters
    ----------
    conc : array-like
        Concentration in µg/m³.
    pollutant : {"pm25", "pm10"}
    standard : {"current", "study"}
        ``current`` uses the 2024 PM2.5 breakpoints; ``study`` reproduces the
        2006 table used by Odubanjo et al. (2024).
    """
    c = _prepare(conc, pollutant)
    table = BREAKPOINTS[pollutant][standard]
    out = np.full(c.shape, np.nan, dtype="float64")

    for lo, hi, i_lo, i_hi in table:
        mask = (c >= lo) & (c <= hi)
        out[mask] = (i_hi - i_lo) / (hi - lo) * (c[mask] - lo) + i_lo

    # Concentrations above the last breakpoint are capped at 500; negative
    # values are sensor noise and become missing.
    out = np.where(c > table[-1][1], 500.0, out)
    out = np.where(c < 0, np.nan, out)
    return np.round(out).astype("float64")


def aqi_category(value) -> str | None:
    """Return the EPA category label for one or more AQI values."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    v = float(value)
    for name, lo, hi, *_ in AQI_BANDS:
        if lo <= v <= hi:
            return name
    return "Hazardous" if v > 500 else "Good"


def aqi_color(value) -> str:
    name = aqi_category(value)
    return AQI_COLORS.get(name, "#8A9A96")


def dominant_pollutant(aqi_pm25, aqi_pm10):
    """Return the pollutant driving the overall AQI."""
    a25 = np.asarray(aqi_pm25, dtype="float64")
    a10 = np.asarray(aqi_pm10, dtype="float64")
    result = np.where(a25 >= a10, "PM2.5", "PM10")
    result = np.where(np.isnan(a25) & np.isnan(a10), None, result)
    result = np.where(np.isnan(a25) & ~np.isnan(a10), "PM10", result)
    result = np.where(~np.isnan(a25) & np.isnan(a10), "PM2.5", result)
    return result


def category_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"category": name, "low": lo, "high": hi, "color": color, "advice": advice}
            for name, lo, hi, color, advice in AQI_BANDS
        ]
    )


def who_exceedance(daily: pd.DataFrame, pollutant: str = "pm25") -> float:
    values = daily[pollutant].dropna()
    if values.empty:
        return float("nan")
    return float((values > WHO_24H[pollutant]).mean() * 100)


def aqi_summary(daily: pd.DataFrame) -> dict:
    """Compact, presentation-ready summary for a city's daily frame."""
    pm25 = daily["pm25"].dropna()
    pm10 = daily["pm10"].dropna()
    aqi = daily["aqi"].dropna()
    return {
        "pm25_mean": float(pm25.mean()) if not pm25.empty else float("nan"),
        "pm10_mean": float(pm10.mean()) if not pm10.empty else float("nan"),
        "aqi_mean": float(aqi.mean()) if not aqi.empty else float("nan"),
        "aqi_max": float(aqi.max()) if not aqi.empty else float("nan"),
        "days": int(daily["aqi"].notna().sum()),
        "who_pm25_exceedance": who_exceedance(daily, "pm25"),
        "who_pm10_exceedance": who_exceedance(daily, "pm10"),
        "worst_category": aqi_category(aqi.max()) if not aqi.empty else None,
    }
