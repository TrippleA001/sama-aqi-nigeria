# Sama: Nigeria Air Quality Observatory

**Sama** means "sky" in Hausa. This is a production-quality Streamlit observatory built from the
CAR-NASRDA PurpleAir record for urban and rural Nigeria (1 May 2021 to 30 April 2023), covering
Lagos, Abuja, Benin City, Osogbo (urban) and Anyigba (rural).

Source study: [Odubanjo et al. (2024)](https://doi.org/10.46481/jnsps.2024.2120),
*Journal of the Nigerian Society of Physical Sciences* 6, 2120.

## What it does

| Page | Purpose |
|------|---------|
| **Overview** | Headline story: urban PM2.5 averages about 2.6 times the rural level, live conditions from Open-Meteo, monitor map |
| **City Explorer** | Per-city time series, diurnal rhythm, monthly profile, calendar heatmap, wind rose |
| **Urban vs Rural** | Seasonal comparison, distributions, guideline exceedance table |
| **Forecast Lab** | Next-day PM2.5 and PM10 forecast from today's air and weather, with uncertainty bands |
| **Method** | Pipeline, AQI standards, paper reproduction, documented model limitations |

## Why this exists

The source notebooks used a random train/test split, which inflates performance (R² up to ~0.89) by
leaking time. This app uses a **time-ordered holdout** (the last 20% of days per city, never used in
training). The deployed ensemble (Ridge + Random Forest + Gradient Boosting) averages R² ≈ 0.39
against a persistence benchmark of ≈ 0.14. That skill is modest and is reported in full, including
the low-skill rural site (Anyigba). Model metrics, limitations and data-quality caveats are
documented throughout rather than omitted.

## Stack

Streamlit · Plotly · scikit-learn · pandas · pyarrow · Open-Meteo Air Quality API (live, keyless)

## Quick start

```bash
git clone https://github.com/TrippleA001/sama-aqi-nigeria.git
cd sama-aqi-nigeria
python -m venv .venv
.venv\Scripts\activate          # Windows
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Data

Raw Excel files are **not** committed (`data/raw/` is gitignored). Processed parquet and trained
model bundles are committed so the app runs immediately:

- `data/processed/hourly.parquet`: cleaned hourly record (71,339 valid PM2.5 hours)
- `data/processed/daily.parquet`: daily aggregation with AQI (2,834 city-days)
- `models/*.joblib`: per-city next-day forecast bundles
- `models/metrics.json`: holdout metrics for every city and pollutant

To regenerate from raw sources:

```bash
python scripts/build_dataset.py
python scripts/train_models.py
```

## Deployment

Deployed on [Streamlit Community Cloud](https://sama-aqi-nigeria.streamlit.app/) from this repository.
Connect the repository, point the entrypoint at `app.py`, and add no secrets (Open-Meteo is keyless).

```
runtime: python-3.12
requirements: requirements.txt
entrypoint: app.py
```

## Method highlights

- **Cleaning:** sentinel removal (-273.15 °C, humidity >100 %, pressure outliers, negative wind),
  duplicate removal, full hourly grid reindexed; PM values are never interpolated; EPA 75 % rule
  (at least 18 valid hours) for a daily AQI.
- **AQI:** US EPA breakpoints. The current 2024 PM2.5 revision is used in the app; the study-era
  2006 table is reproduced on the Method page for validation against Odubanjo et al. (2024).
- **Forecast:** next-day daily mean from today's concentration, 7-day average, weather and
  seasonality; time-ordered 80/20 holdout; 99th-percentile target cap; 80 % uncertainty band from
  random-forest tree spread.
- **Comparison:** urban four-city PM2.5 mean 37.35 µg/m³ against rural Anyigba 14.11 µg/m³ (2.65
  times); WHO 24-hour PM2.5 exceedance 93.0 % urban against 26.6 % rural.

## Limitations

Observational PurpleAir sensor data (not regulatory-grade), PM-only AQI (no O₃, NO₂, SO₂ or CO),
humidity can bias PurpleAir high, Anyigba has about 69 % PM2.5 coverage, and the forecast is a
statistical nowcast, not a health advisory.

## Citation

Odubanjo et al. (2024), *Journal of the Nigerian Society of Physical Sciences* 6, 2120. Source
study and data (CAR-NASRDA / PurpleAir).

## License

MIT
