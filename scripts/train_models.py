"""Train the next-day PM2.5 / PM10 forecasters.

Design choices that matter
--------------------------
* **Time-ordered holdout.** The last 20% of days are never seen in training,
  so metrics reflect a real forecast rather than a random split.
* **Persistence is the benchmark.** A forecast only earns its place if it beats
  "tomorrow will look like today". The app shows both.
* **Ensemble.** Ridge (linear persistence), a random forest (non-linear
  interactions) and gradient boosting are averaged. This is more stable across
  five very different cities than picking a single family.
* **Winsorised target.** Sensors occasionally saturate near 1,000 µg/m³. The
  99th percentile cap is learned on the training window only.
* **Uncertainty.** The 10th–90th percentile spread of the random-forest trees
  is reported as an 80% band, and its empirical coverage is checked.

Run from the repository root:

    python scripts/train_models.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import CITY_ORDER, DAILY_PATH, METRICS_PATH, MODEL_DIR  # noqa: E402
from src.model import FORECAST_FEATURES, ModelBundle, add_forecast_features  # noqa: E402

TARGETS = {"pm25": "PM2.5", "pm10": "PM10"}
SPLIT_FRACTION = 0.8
RANDOM_STATE = 42
CAP_QUANTILE = 0.99

# What the original notebooks reported (tuned Random Forest, random split,
# hourly target). Included for context, not as a like-for-like benchmark.
REFERENCE = {
    "Lagos|PM2.5": {"r2": 0.735, "rmse": 12.02, "task": "hourly, random split"},
    "Lagos|PM10": {"r2": 0.756, "rmse": 13.90, "task": "hourly, random split"},
    "Abuja|PM2.5": {"r2": 0.714, "rmse": 10.19, "task": "hourly, random split"},
    "Abuja|PM10": {"r2": 0.766, "rmse": 13.22, "task": "hourly, random split"},
    "Benin City|PM2.5": {"r2": 0.417, "rmse": 15.77, "task": "hourly, random split"},
    "Benin City|PM10": {"r2": 0.458, "rmse": 22.15, "task": "hourly, random split"},
    "Osogbo|PM2.5": {"r2": 0.783, "rmse": 6.82, "task": "hourly, random split"},
    "Osogbo|PM10": {"r2": 0.823, "rmse": 8.31, "task": "hourly, random split"},
    "Anyigba|PM2.5": {"r2": 0.882, "rmse": 3.76, "task": "hourly, random split"},
    "Anyigba|PM10": {"r2": 0.892, "rmse": 4.21, "task": "hourly, random split"},
}


def _slug(city: str) -> str:
    return city.lower().replace(" ", "_")


def _metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype="float64")
    y_pred = np.asarray(y_pred, dtype="float64")
    mask = y_true > 1.0
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100) if mask.any() else float("nan")
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape": mape,
        "n": int(len(y_true)),
    }


def _estimators() -> dict:
    imputer = lambda: SimpleImputer(strategy="median", keep_empty_features=True)  # noqa: E731
    return {
        "Ridge": Pipeline(
            [
                ("imputer", imputer()),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        ),
        "Random forest": Pipeline(
            [
                ("imputer", imputer()),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=140,
                        min_samples_leaf=4,
                        max_features=0.8,
                        n_jobs=1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "Gradient boosting": Pipeline(
            [
                ("imputer", imputer()),
                (
                    "model",
                    GradientBoostingRegressor(
                        n_estimators=120,
                        max_depth=3,
                        min_samples_leaf=4,
                        learning_rate=0.06,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


def _ensemble() -> VotingRegressor:
    estimators = _estimators()
    return VotingRegressor(
        [
            ("ridge", estimators["Ridge"]),
            ("rf", estimators["Random forest"]),
            ("gb", estimators["Gradient boosting"]),
        ]
    )


def train_one(daily: pd.DataFrame, city: str, pollutant: str, verbose: bool = False) -> tuple[dict, pd.DataFrame]:
    frame = add_forecast_features(daily, pollutant)
    frame = frame.dropna(subset=["y_next", "lag1", "roll7"]).reset_index(drop=True)

    X = frame[FORECAST_FEATURES]
    y = frame["y_next"].astype("float64")
    split = int(len(frame) * SPLIT_FRACTION)
    cap = float(y.iloc[:split].quantile(CAP_QUANTILE))
    y = y.clip(upper=cap)

    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    def log(message: str) -> None:
        if verbose:
            print(f"    {message}", flush=True)

    results = {}
    trained = {}
    for name, pipeline in _estimators().items():
        log(f"fit {name}")
        pipeline.fit(X_train, y_train)
        trained[name] = pipeline
        results[name] = _metrics(y_test, pipeline.predict(X_test))

    log("fit ensemble")
    ensemble = _ensemble()
    ensemble.fit(X_train, y_train)
    results["Ensemble (deployed)"] = _metrics(y_test, ensemble.predict(X_test))

    results["Persistence (today)"] = _metrics(y_test, X_test["lag1"])
    results["Median baseline"] = _metrics(y_test, np.full(len(y_test), float(y_train.median())))

    # 80% band from the forest's individual trees.
    forest = trained["Random forest"].named_steps["model"]
    tree_predictions = np.array([tree.predict(X_test.to_numpy()) for tree in forest.estimators_])
    low = np.quantile(tree_predictions, 0.1, axis=0)
    high = np.quantile(tree_predictions, 0.9, axis=0)
    coverage = float(np.mean((y_test.to_numpy() >= low) & (y_test.to_numpy() <= high)) * 100)

    log("permutation importance")
    importance = permutation_importance(
        ensemble,
        X_test,
        y_test,
        scoring="neg_root_mean_squared_error",
        n_repeats=4,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    raw = np.clip(importance.importances_mean, 0, None)
    share = raw / raw.sum() if raw.sum() else np.zeros_like(raw)
    importance_rows = sorted(
        [
            {"feature": f, "rmse_increase": round(float(v), 4), "share": round(float(s) * 100, 2)}
            for f, v, s in zip(FORECAST_FEATURES, raw, share, strict=False)
        ],
        key=lambda row: row["rmse_increase"],
        reverse=True,
    )

    bundle = ModelBundle(
        model=ensemble,
        features=FORECAST_FEATURES,
        target_cap=cap,
        interval_coverage=round(coverage, 1),
    )
    name = f"{_slug(city)}_{pollutant}"
    joblib.dump(bundle, MODEL_DIR / f"{name}.joblib", compress=3)

    predictions = pd.DataFrame(
        {
            "city": city,
            "pollutant": TARGETS[pollutant],
            "date": frame["date"].iloc[split:].to_numpy(),
            "actual": y_test.to_numpy(),
            "predicted": ensemble.predict(X_test),
            "low": low,
            "high": high,
        }
    )

    record = {
        "city": city,
        "pollutant": TARGETS[pollutant],
        "target": pollutant,
        "task": "next-day daily mean",
        "rows": int(len(frame)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "train_end": str(pd.Timestamp(frame["date"].iloc[split - 1]).date()),
        "test_start": str(pd.Timestamp(frame["date"].iloc[split]).date()),
        "test_end": str(pd.Timestamp(frame["date"].iloc[-1]).date()),
        "target_cap": round(cap, 1),
        "models": results,
        "deployed": "Ensemble (deployed)",
        "interval_coverage_pct": round(coverage, 1),
        "feature_importance": importance_rows,
        "reference_notebook": REFERENCE.get(f"{city}|{TARGETS[pollutant]}"),
        "model_file": f"{name}.joblib",
    }
    return record, predictions


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    daily = pd.read_parquet(DAILY_PATH)

    records = {}
    all_predictions = []
    started = time.perf_counter()

    for city in CITY_ORDER:
        city_daily = daily[daily["city"] == city]
        for pollutant in TARGETS:
            print(f"Training {city} / {TARGETS[pollutant]} ...", flush=True)
            record, predictions = train_one(city_daily, city, pollutant, verbose=True)
            records[f"{city}|{TARGETS[pollutant]}"] = record
            all_predictions.append(predictions)
            deployed = record["models"][record["deployed"]]
            persistence = record["models"]["Persistence (today)"]
            print(
                f"  -> ensemble R2 {deployed['r2']:.3f} | RMSE {deployed['rmse']:.2f} | "
                f"MAE {deployed['mae']:.2f} | persistence R2 {persistence['r2']:.3f} | "
                f"band {record['interval_coverage_pct']}%"
            )

    predictions_frame = pd.concat(all_predictions, ignore_index=True)
    predictions_frame.to_parquet(MODEL_DIR / "validation_predictions.parquet", index=False)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "Next-day daily mean; time-ordered holdout (first 80% train, last 20% test); 99th percentile target cap",
        "features": FORECAST_FEATURES,
        "targets": TARGETS,
        "reference_notebooks": REFERENCE,
        "models": records,
        "average_deployed_r2": round(float(np.mean([r["models"][r["deployed"]]["r2"] for r in records.values()])), 3),
        "average_persistence_r2": round(
            float(np.mean([r["models"]["Persistence (today)"]["r2"] for r in records.values()])), 3
        ),
        "average_deployed_mae": round(float(np.mean([r["models"][r["deployed"]]["mae"] for r in records.values()])), 2),
        "elapsed_seconds": round(time.perf_counter() - started, 1),
    }
    METRICS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"\nSaved metrics -> {METRICS_PATH.relative_to(ROOT)}")
    print(f"Average ensemble R2 {payload['average_deployed_r2']} vs persistence {payload['average_persistence_r2']}")


if __name__ == "__main__":
    main()
