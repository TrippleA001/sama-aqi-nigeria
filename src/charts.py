"""Plotly chart builders with one consistent dark visual language."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .aqi import aqi_category
from .config import AQI_BANDS, AQI_COLORS, CITIES, WHO_24H
from .model import FEATURE_LABELS

FONT = "Manrope, -apple-system, sans-serif"
ACCENT = "#6EE7B7"
MUTED = "#8FA79D"
INK = "#E9F1ED"
GRID = "rgba(255,255,255,0.055)"

AQI_SCALE = [
    [0.00, "#3DDC97"],
    [0.10, "#3DDC97"],
    [0.12, "#F5D547"],
    [0.20, "#F5D547"],
    [0.22, "#FF9F45"],
    [0.30, "#FF9F45"],
    [0.32, "#FF5D5D"],
    [0.40, "#FF5D5D"],
    [0.42, "#B06AB3"],
    [0.60, "#B06AB3"],
    [0.62, "#C1465C"],
    [1.00, "#C1465C"],
]

CONC_SCALE = [
    [0.00, "#3DDC97"],
    [0.14, "#B9E769"],
    [0.24, "#F5D547"],
    [0.36, "#FF9F45"],
    [0.56, "#FF5D5D"],
    [0.78, "#B06AB3"],
    [1.00, "#C1465C"],
]

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _layout(height: int = 360, **overrides) -> dict:
    layout = dict(
        height=height,
        margin=dict(l=6, r=6, t=14, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color="#C7D6CF", size=12),
        hoverlabel=dict(
            bgcolor="#0D1F18",
            bordercolor="rgba(255,255,255,0.16)",
            font=dict(family=FONT, color=INK, size=12),
        ),
        xaxis=dict(
            gridcolor=GRID,
            zeroline=False,
            linecolor="rgba(255,255,255,0.09)",
            tickfont=dict(size=11),
            title=None,
        ),
        yaxis=dict(
            gridcolor=GRID,
            zeroline=False,
            linecolor="rgba(255,255,255,0.09)",
            tickfont=dict(size=11),
            title=None,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#A9BDB4"),
        ),
        showlegend=False,
    )
    layout.update(overrides)
    return layout


def _bands(fig: go.Figure, axis: str = "y") -> None:
    for _name, low, high, color, _ in AQI_BANDS:
        kwargs = dict(fillcolor=color, opacity=0.045, line_width=0, layer="below")
        if axis == "y":
            fig.add_hrect(y0=low, y1=high, **kwargs)
        else:
            fig.add_vrect(x0=low, x1=high, **kwargs)


def aqi_timeseries(daily: pd.DataFrame, height: int = 400) -> go.Figure:
    frame = daily.dropna(subset=["aqi"]).sort_values("date")
    smooth = frame.set_index("date")["aqi"].rolling("7D", min_periods=2).mean()

    fig = go.Figure()
    _bands(fig)
    fig.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame["aqi"],
            mode="markers",
            marker=dict(size=3.5, color="rgba(233,241,237,0.28)"),
            name="Daily AQI",
            hovertemplate="%{x|%d %b %Y}<br><b>AQI %{y:.0f}</b><extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=smooth.index,
            y=smooth.values,
            mode="lines",
            line=dict(color=ACCENT, width=2.6, shape="spline", smoothing=0.45),
            fill="tozeroy",
            fillcolor="rgba(110,231,183,0.07)",
            name="7-day average",
            hovertemplate="%{x|%d %b %Y}<br>7-day AQI <b>%{y:.0f}</b><extra></extra>",
        )
    )

    peak_idx = frame["aqi"].idxmax()
    peak = frame.loc[peak_idx]
    fig.add_trace(
        go.Scatter(
            x=[peak["date"]],
            y=[peak["aqi"]],
            mode="markers+text",
            marker=dict(size=9, color="#FF8A8A", line=dict(color="#1a0c0c", width=2)),
            text=[f"Peak {peak['aqi']:.0f}"],
            textposition="top center",
            textfont=dict(size=11, color="#FFB4B4"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.update_layout(
        **_layout(
            height,
            hovermode="x unified",
            yaxis=dict(
                gridcolor=GRID,
                zeroline=False,
                title=dict(text="US EPA AQI", font=dict(size=11, color=MUTED)),
                range=[0, max(120, float(frame["aqi"].max()) * 1.12)],
            ),
            xaxis=dict(gridcolor=GRID, zeroline=False, tickformat="%b %Y"),
        )
    )
    return fig


def concentration_timeseries(daily: pd.DataFrame, pollutant: str = "pm25", height: int = 380) -> go.Figure:
    label = "PM2.5" if pollutant == "pm25" else "PM10"
    frame = daily.dropna(subset=[pollutant]).sort_values("date")
    smooth = frame.set_index("date")[pollutant].rolling("7D", min_periods=2).mean()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["date"],
            y=frame[pollutant],
            mode="markers",
            marker=dict(size=3, color="rgba(233,241,237,0.2)"),
            name="Daily mean",
            hovertemplate="%{x|%d %b %Y}<br>" + f"{label} %{{y:.1f}} µg/m³<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=smooth.index,
            y=smooth.values,
            mode="lines",
            line=dict(color=ACCENT if pollutant == "pm25" else "#9ED8FF", width=2.4, shape="spline"),
            name="7-day average",
            hovertemplate="%{x|%d %b %Y}<br>7-day " + f"{label} %{{y:.1f}} µg/m³<extra></extra>",
        )
    )
    fig.add_hline(
        y=WHO_24H[pollutant],
        line=dict(color="#FFB86B", width=1.2, dash="dot"),
        annotation_text=f"WHO 24h guideline · {WHO_24H[pollutant]:.0f}",
        annotation_position="top left",
        annotation_font=dict(size=10, color="#FFB86B"),
    )
    fig.update_layout(
        **_layout(
            height,
            hovermode="x unified",
            yaxis=dict(
                gridcolor=GRID,
                zeroline=False,
                title=dict(text="µg/m³", font=dict(size=11, color=MUTED)),
            ),
            xaxis=dict(gridcolor=GRID, zeroline=False, tickformat="%b %Y"),
        )
    )
    return fig


def calendar_heatmap(daily: pd.DataFrame, pollutant: str = "pm25", height: int = 260) -> go.Figure:
    frame = daily.dropna(subset=[pollutant]).copy()
    frame["week"] = frame["date"].dt.to_period("W-SUN").dt.start_time
    frame["weekday"] = frame["date"].dt.day_of_week
    weeks = sorted(frame["week"].unique())
    lookup = {(row["week"], row["weekday"]): row for _, row in frame.iterrows()}

    z = np.full((7, len(weeks)), np.nan)
    dates = np.full((7, len(weeks)), "", dtype=object)
    values = np.full((7, len(weeks)), np.nan)
    for (week, weekday), row in lookup.items():
        j = weeks.index(week)
        z[weekday, j] = row[pollutant]
        values[weekday, j] = row[pollutant]
        dates[weekday, j] = row["date"].strftime("%d %b %Y")

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=weeks,
            y=WEEKDAYS,
            customdata=np.dstack([dates, values]),
            colorscale=CONC_SCALE,
            zmin=0,
            zmax=np.nanpercentile(z, 98),
            xgap=2.5,
            ygap=2.5,
            hovertemplate="%{customdata[0]}<br><b>%{z:.1f} µg/m³</b><extra></extra>",
            colorbar=dict(
                title=dict(text="µg/m³", font=dict(size=10, color=MUTED)),
                thickness=8,
                len=0.7,
                tickfont=dict(size=9, color=MUTED),
                outlinewidth=0,
            ),
        )
    )
    tick_weeks = [w for i, w in enumerate(weeks) if w.month != weeks[i - 1].month] if weeks else []
    fig.update_layout(
        **_layout(
            height,
            xaxis=dict(
                gridcolor="rgba(0,0,0,0)",
                tickmode="array",
                tickvals=tick_weeks,
                ticktext=[w.strftime("%b") for w in tick_weeks],
                showgrid=False,
            ),
            yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=10)),
            margin=dict(l=6, r=6, t=8, b=6),
        )
    )
    return fig


def diurnal_profile(hourly: pd.DataFrame, pollutant: str = "pm25", height: int = 360) -> go.Figure:
    frame = hourly.dropna(subset=[pollutant]).copy()
    frame["hour"] = frame["timestamp"].dt.hour
    grouped = frame.groupby("hour")[pollutant]
    mean = grouped.mean()
    p25 = grouped.quantile(0.25)
    p75 = grouped.quantile(0.75)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=p75.index,
            y=p75.values,
            mode="lines",
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=p25.index,
            y=p25.values,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(110,231,183,0.10)",
            name="25th–75th percentile",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=mean.index,
            y=mean.values,
            mode="lines+markers",
            line=dict(color=ACCENT, width=2.4, shape="spline"),
            marker=dict(size=5, color=ACCENT, line=dict(color="#06110D", width=1)),
            name="Mean",
            hovertemplate="%{x}:00<br><b>%{y:.1f} µg/m³</b><extra></extra>",
        )
    )
    peak_hour = int(mean.idxmax())
    fig.add_annotation(
        x=peak_hour,
        y=float(mean.max()),
        text=f"Peak {peak_hour:02d}:00",
        showarrow=False,
        yshift=16,
        font=dict(size=10, color="#C9F7E5"),
        bgcolor="rgba(110,231,183,0.12)",
        bordercolor="rgba(110,231,183,0.3)",
        borderpad=4,
    )
    fig.update_layout(
        **_layout(
            height,
            xaxis=dict(
                gridcolor=GRID,
                tickmode="array",
                tickvals=list(range(0, 24, 3)),
                ticktext=[f"{h:02d}" for h in range(0, 24, 3)],
                title=dict(text="Hour of day (local time)", font=dict(size=11, color=MUTED)),
            ),
            yaxis=dict(gridcolor=GRID, title=dict(text="µg/m³", font=dict(size=11, color=MUTED))),
            hovermode="x",
        )
    )
    return fig


def monthly_bars(daily: pd.DataFrame, pollutant: str = "pm25", height: int = 360) -> go.Figure:
    frame = daily.dropna(subset=[pollutant]).copy()
    grouped = frame.groupby("month")[pollutant].mean().reindex(range(1, 13))
    colors = []
    for value in grouped.values:
        if np.isnan(value):
            colors.append("#24352D")
        else:
            # Colour by the WHO multiple so the seasonal story reads at a glance.
            multiple = value / WHO_24H[pollutant]
            if multiple < 1:
                colors.append("#3DDC97")
            elif multiple < 2:
                colors.append("#F5D547")
            elif multiple < 3:
                colors.append("#FF9F45")
            elif multiple < 5:
                colors.append("#FF5D5D")
            else:
                colors.append("#B06AB3")

    fig = go.Figure(
        go.Bar(
            x=MONTHS,
            y=grouped.values,
            marker=dict(color=colors, line=dict(width=0)),
            hovertemplate="%{x}<br><b>%{y:.1f} µg/m³</b><extra></extra>",
            text=[f"{v:.0f}" if not np.isnan(v) else "" for v in grouped.values],
            textposition="outside",
            textfont=dict(size=9, color="#A9BDB4"),
        )
    )
    fig.add_hline(
        y=WHO_24H[pollutant],
        line=dict(color="#FFB86B", width=1, dash="dot"),
        annotation_text="WHO",
        annotation_position="top right",
        annotation_font=dict(size=9, color="#FFB86B"),
    )
    fig.update_layout(
        **_layout(
            height,
            yaxis=dict(gridcolor=GRID, title=dict(text="µg/m³", font=dict(size=11, color=MUTED))),
            xaxis=dict(gridcolor="rgba(0,0,0,0)", showgrid=False),
            bargap=0.32,
            margin=dict(l=6, r=6, t=22, b=6),
        )
    )
    return fig


def wind_rose(hourly: pd.DataFrame, pollutant: str = "pm25", height: int = 360) -> go.Figure | None:
    frame = hourly.dropna(subset=[pollutant, "wind_dir_deg"])
    if frame.empty:
        return None
    bins = np.arange(0, 361, 22.5)
    labels = [f"{(bins[i] + bins[i + 1]) / 2:.0f}°" for i in range(len(bins) - 1)]
    frame["sector"] = pd.cut(frame["wind_dir_deg"], bins=bins, labels=labels, include_lowest=True)
    grouped = frame.groupby("sector", observed=False)[pollutant].mean()
    values = grouped.values

    fig = go.Figure(
        go.Barpolar(
            r=values,
            theta=labels,
            width=[22.5] * len(labels),
            marker=dict(
                color=values,
                colorscale=CONC_SCALE,
                line=dict(color="rgba(6,17,13,0.5)", width=0.5),
            ),
            hovertemplate="Wind from %{theta}<br><b>%{r:.1f} µg/m³</b><extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            height,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    gridcolor=GRID,
                    linecolor="rgba(255,255,255,0.08)",
                    tickfont=dict(size=9, color=MUTED),
                    angle=45,
                ),
                angularaxis=dict(
                    gridcolor=GRID,
                    linecolor="rgba(255,255,255,0.08)",
                    tickfont=dict(size=10, color="#A9BDB4"),
                    direction="clockwise",
                ),
            ),
            margin=dict(l=30, r=30, t=20, b=10),
        )
    )
    return fig


def city_distribution(daily: pd.DataFrame, pollutant: str = "pm25", height: int = 380) -> go.Figure:
    frame = daily.dropna(subset=[pollutant]).copy()
    medians = frame.groupby("city")[pollutant].median().sort_values()
    order = list(medians.index)
    fig = go.Figure()
    palette = {"Urban": "#6EE7B7", "Rural": "#FFB86B"}
    for city in order:
        subset = frame[frame["city"] == city]
        kind = CITIES[city]["kind"]
        fig.add_trace(
            go.Violin(
                y=subset[pollutant],
                name=city,
                box_visible=True,
                meanline_visible=True,
                points=False,
                line=dict(color=palette[kind], width=1.3),
                fillcolor="rgba(110,231,183,0.10)" if kind == "Urban" else "rgba(255,184,107,0.10)",
                hoveron="violins",
                hovertemplate=f"{city}<br>%{{y:.1f}} µg/m³<extra></extra>",
            )
        )
    fig.add_hline(
        y=WHO_24H[pollutant],
        line=dict(color="#FFB86B", width=1, dash="dot"),
        annotation_text="WHO 24h guideline",
        annotation_position="top left",
        annotation_font=dict(size=10, color="#FFB86B"),
    )
    fig.update_layout(
        **_layout(
            height,
            yaxis=dict(gridcolor=GRID, title=dict(text="µg/m³", font=dict(size=11, color=MUTED))),
            xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10)),
            violingap=0.28,
            violinmode="overlay",
            margin=dict(l=6, r=6, t=22, b=6),
        )
    )
    return fig


def urban_rural_bars(city_cards: pd.DataFrame, height: int = 380) -> go.Figure:
    frame = city_cards.sort_values("pm25", ascending=True)
    colors = ["#FFB86B" if kind == "Rural" else "#6EE7B7" for kind in frame["kind"]]
    fig = go.Figure(
        go.Bar(
            x=frame["pm25"],
            y=frame["city"],
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:.1f}" for v in frame["pm25"]],
            textposition="outside",
            textfont=dict(size=10, color="#CFE0D7"),
            hovertemplate="%{y}<br><b>%{x:.1f} µg/m³</b><extra></extra>",
        )
    )
    rural = frame.loc[frame["kind"] == "Rural", "pm25"]
    if not rural.empty:
        fig.add_vline(
            x=float(rural.iloc[0]),
            line=dict(color="#FFB86B", width=1, dash="dash"),
            annotation_text="Rural comparator",
            annotation_position="top right",
            annotation_font=dict(size=9, color="#FFB86B"),
        )
    fig.update_layout(
        **_layout(
            height,
            xaxis=dict(
                gridcolor=GRID,
                title=dict(text="Mean daily PM2.5 (µg/m³)", font=dict(size=11, color=MUTED)),
            ),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11)),
            margin=dict(l=6, r=46, t=18, b=6),
        )
    )
    return fig


def aqi_donut(daily: pd.DataFrame, height: int = 320) -> go.Figure:
    frame = daily.dropna(subset=["category"])
    counts = frame["category"].value_counts()
    order = [name for name, *_ in AQI_BANDS]
    counts = counts.reindex(order).dropna()
    fig = go.Figure(
        go.Pie(
            labels=counts.index,
            values=counts.values,
            hole=0.68,
            marker=dict(colors=[AQI_COLORS[c] for c in counts.index], line=dict(color="#08150F", width=2)),
            textinfo="none",
            hovertemplate="%{label}<br><b>%{value} days</b> (%{percent})<extra></extra>",
            sort=False,
        )
    )
    total = int(counts.sum())
    fig.add_annotation(
        text=f"<b>{total:,}</b><br><span style='font-size:10px;color:#8FA79D'>city-days</span>",
        showarrow=False,
        font=dict(size=22, color=INK, family="Sora"),
    )
    fig.update_layout(**_layout(height, margin=dict(l=8, r=8, t=8, b=8), showlegend=False))
    return fig


def city_map(city_cards: pd.DataFrame, height: int = 430) -> go.Figure:
    frame = city_cards.copy()
    sizes = 16 + (frame["pm25"] / frame["pm25"].max()) * 34
    fig = go.Figure(
        go.Scattermap(
            lat=frame["lat"],
            lon=frame["lon"],
            mode="markers+text",
            marker=dict(
                size=sizes,
                color=frame["aqi"],
                colorscale=AQI_SCALE,
                cmin=0,
                cmax=200,
                opacity=0.9,
                colorbar=dict(
                    title=dict(text="AQI", font=dict(size=10, color=MUTED)),
                    thickness=8,
                    len=0.65,
                    tickfont=dict(size=9, color=MUTED),
                    outlinewidth=0,
                ),
            ),
            text=frame["city"],
            textposition="top center",
            textfont=dict(size=11, color="#E9F1ED", family="Manrope"),
            customdata=np.stack([frame["kind"], frame["pm25"], frame["pm10"], frame["aqi"], frame["state"]], axis=-1),
            hovertemplate=(
                "<b>%{text}</b> · %{customdata[4]}<br>"
                "%{customdata[0]}<br>"
                "PM2.5 %{customdata[1]:.1f} µg/m³<br>"
                "PM10 %{customdata[2]:.1f} µg/m³<br>"
                "AQI %{customdata[3]:.0f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        **_layout(
            height,
            map=dict(
                style="carto-darkmatter",
                center=dict(lat=7.6, lon=5.2),
                zoom=4.7,
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )
    )
    return fig


def aqi_gauge(value: float, height: int = 250) -> go.Figure:
    category = aqi_category(value) or "Good"
    color = AQI_COLORS[category]
    steps = [
        {
            "range": [lo, hi],
            "color": color.replace("#", "rgba(") if False else _rgba(band_color, 0.22),
        }
        for _, lo, hi, band_color, _ in AQI_BANDS
        if lo <= 500
    ]
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number=dict(font=dict(size=44, color=INK, family="Sora"), suffix=""),
            gauge=dict(
                axis=dict(range=[0, 300], tickwidth=0, tickfont=dict(size=9, color=MUTED)),
                bar=dict(color=color, thickness=0.24),
                bgcolor="rgba(255,255,255,0.03)",
                borderwidth=0,
                steps=steps,
            ),
            domain=dict(x=[0, 1], y=[0, 1]),
        )
    )
    fig.add_annotation(
        text=f"<span style='color:{color};font-weight:700'>{category}</span>",
        x=0.5,
        y=0.06,
        showarrow=False,
        font=dict(size=12),
    )
    fig.update_layout(**_layout(height, margin=dict(l=18, r=18, t=8, b=4)))
    return fig


def _rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def model_scatter(predictions: pd.DataFrame, height: int = 380) -> go.Figure:
    frame = predictions.dropna(subset=["actual", "predicted"])
    max_val = float(max(frame["actual"].max(), frame["predicted"].max())) * 1.06
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["actual"],
            y=frame["predicted"],
            mode="markers",
            marker=dict(size=5, color="rgba(110,231,183,0.55)", line=dict(width=0)),
            hovertemplate="Actual %{x:.1f}<br>Predicted %{y:.1f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            line=dict(color="rgba(233,241,237,0.35)", width=1, dash="dash"),
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        **_layout(
            height,
            xaxis=dict(
                gridcolor=GRID,
                title=dict(text="Actual next-day PM2.5 (µg/m³)", font=dict(size=11, color=MUTED)),
                range=[0, max_val],
            ),
            yaxis=dict(
                gridcolor=GRID,
                title=dict(text="Predicted (µg/m³)", font=dict(size=11, color=MUTED)),
                range=[0, max_val],
            ),
            hovermode="closest",
        )
    )
    return fig


def model_leaderboard(record: dict, height: int = 300) -> go.Figure:
    models = record["models"]
    order = [
        "Ensemble (deployed)",
        "Ridge",
        "Random forest",
        "Gradient boosting",
        "Persistence (today)",
        "Median baseline",
    ]
    labels = [m for m in order if m in models]
    values = [models[m]["r2"] for m in labels]
    colors = [ACCENT if m == "Ensemble (deployed)" else "rgba(233,241,237,0.28)" for m in labels]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:.2f}" for v in values],
            textposition="outside",
            textfont=dict(size=10, color="#CFE0D7"),
            hovertemplate="%{y}<br>R² %{x:.3f}<extra></extra>",
        )
    )
    fig.add_vline(x=0, line=dict(color="rgba(255,255,255,0.18)", width=1))
    fig.update_layout(
        **_layout(
            height,
            xaxis=dict(
                gridcolor=GRID,
                title=dict(text="Holdout R²", font=dict(size=11, color=MUTED)),
                range=[min(-0.1, min(values) * 1.1), 1.0],
            ),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10), autorange="reversed"),
            margin=dict(l=6, r=38, t=8, b=6),
        )
    )
    return fig


def importance_bars(record: dict, height: int = 320, top: int = 8) -> go.Figure:
    rows = record["feature_importance"][:top][::-1]
    labels = [FEATURE_LABELS.get(row["feature"], row["feature"]) for row in rows]
    values = [row["share"] for row in rows]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color="rgba(110,231,183,0.7)", line=dict(width=0)),
            text=[f"{v:.1f}%" for v in values],
            textposition="outside",
            textfont=dict(size=9, color="#CFE0D7"),
            hovertemplate="%{y}<br>%{x:.1f}% of importance<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            height,
            xaxis=dict(
                gridcolor=GRID,
                title=dict(text="Share of permutation importance (%)", font=dict(size=10, color=MUTED)),
                range=[0, max(values) * 1.25],
            ),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10)),
            margin=dict(l=6, r=34, t=8, b=6),
        )
    )
    return fig


def season_compare(daily: pd.DataFrame, pollutant: str = "pm25", height: int = 320) -> go.Figure:
    frame = daily.dropna(subset=[pollutant]).copy()
    grouped = frame.groupby(["city", "season"])[pollutant].mean().reset_index()
    fig = go.Figure()
    palette = {"Dry": "#FFB86B", "Rainy": "#6EE7B7"}
    for season in ["Dry", "Rainy"]:
        subset = grouped[grouped["season"] == season]
        fig.add_trace(
            go.Bar(
                x=subset["city"],
                y=subset[pollutant],
                name=season,
                marker=dict(color=palette[season], line=dict(width=0)),
                hovertemplate="%{x}<br>" + season + " <b>%{y:.1f} µg/m³</b><extra></extra>",
            )
        )
    fig.update_layout(
        **_layout(
            height,
            barmode="group",
            bargap=0.3,
            legend=dict(
                orientation="h",
                y=1.08,
                x=0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=10, color="#A9BDB4"),
            ),
            showlegend=True,
            yaxis=dict(gridcolor=GRID, title=dict(text="µg/m³", font=dict(size=11, color=MUTED))),
            xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10)),
        )
    )
    return fig
