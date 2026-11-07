"""Feature engineering and the deployed forecast bundle.

The model answers a concrete question: *given today's air and weather, what
will tomorrow's 24-hour particulate level look like?* Persistence features do
most of the work; weather and seasonality add skill on top.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

FORECAST_FEATURES = [
    "lag1",
    "roll7",
    "temp_c",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_ms",
    "wind_dir_sin",
    "wind_dir_cos",
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
]

FEATURE_LABELS = {
    "lag1": "Today's concentration",
    "roll7": "7-day average",
    "temp_c": "Temperature",
    "humidity_pct": "Relative humidity",
    "pressure_hpa": "Pressure",
    "wind_speed_ms": "Wind speed",
    "wind_dir_sin": "Wind direction (E–W)",
    "wind_dir_cos": "Wind direction (N–S)",
    "month_sin": "Season",
    "month_cos": "Season",
    "dow_sin": "Day of week",
    "dow_cos": "Day of week",
}


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add cyclic encodings so the model understands hours and seasons."""
    out = frame.copy()
    ts = pd.to_datetime(out["timestamp"])
    month = ts.dt.month.to_numpy(dtype="float64")
    dow = ts.dt.day_of_week.to_numpy(dtype="float64")
    wind = pd.to_numeric(out.get("wind_dir_deg"), errors="coerce").to_numpy(dtype="float64")

    out["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12)
    out["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12)
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    out["wind_dir_sin"] = np.sin(np.deg2rad(wind))
    out["wind_dir_cos"] = np.cos(np.deg2rad(wind))
    return out


def add_forecast_features(daily: pd.DataFrame, column: str = "pm25") -> pd.DataFrame:
    """Build next-day targets and persistence features for one city."""
    frame = daily.sort_values("date").copy()
    frame["timestamp"] = pd.to_datetime(frame["date"])
    frame = add_time_features(frame)
    frame["lag1"] = frame[column]
    frame["lag2"] = frame[column].shift(1)
    frame["lag3"] = frame[column].shift(2)
    frame["roll7"] = frame[column].rolling(7, min_periods=4).mean()
    frame["roll30"] = frame[column].rolling(30, min_periods=10).mean()
    frame["y_next"] = frame[column].shift(-1)
    return frame


def features_from_inputs(
    today: float,
    week_average: float,
    temp_c: float,
    humidity_pct: float,
    pressure_hpa: float,
    wind_speed_ms: float,
    wind_dir_deg: float,
    month: int,
    day_of_week: int = 2,
) -> pd.DataFrame:
    """Build the one-row feature frame used by the interactive forecaster."""
    month_rad = 2 * np.pi * (month - 1) / 12
    dow_rad = 2 * np.pi * day_of_week / 7
    wind_rad = np.deg2rad(wind_dir_deg)
    row = {
        "lag1": today,
        "roll7": week_average,
        "temp_c": temp_c,
        "humidity_pct": humidity_pct,
        "pressure_hpa": pressure_hpa,
        "wind_speed_ms": wind_speed_ms,
        "wind_dir_sin": np.sin(wind_rad),
        "wind_dir_cos": np.cos(wind_rad),
        "month_sin": np.sin(month_rad),
        "month_cos": np.cos(month_rad),
        "dow_sin": np.sin(dow_rad),
        "dow_cos": np.cos(dow_rad),
    }
    return pd.DataFrame([row])[FORECAST_FEATURES]


@dataclass
class ModelBundle:
    model: object
    features: list[str]
    target_cap: float
    interval_coverage: float

    def _rf(self):
        pipeline = self.model.named_estimators_["rf"]
        return pipeline.named_steps["model"]

    def predict(self, X: pd.DataFrame) -> tuple[float, float, float]:
        point = float(self.model.predict(X)[0])
        forest = self._rf()
        tree_predictions = np.array([tree.predict(X.to_numpy())[0] for tree in forest.estimators_])
        low, high = np.quantile(tree_predictions, [0.1, 0.9])
        low = min(float(low), point)
        high = max(float(high), point)
        return point, low, high
