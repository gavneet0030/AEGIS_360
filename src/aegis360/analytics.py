"""Pure, deterministic analytical functions used by the UI and reports."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _numeric(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(np.isfinite(values))


def profile_dataset(frame: pd.DataFrame) -> dict[str, object]:
    """Return dataset and per-column quality statistics without changing the input."""
    rows = []
    for name in frame.columns:
        column = frame[name]
        numeric = (
            _numeric(column) if pd.api.types.is_numeric_dtype(column) else pd.Series(dtype=float)
        )
        rows.append(
            {
                "column": str(name),
                "type": str(column.dtype),
                "missing": int(column.isna().sum()),
                "missing_pct": round(float(column.isna().mean() * 100), 2) if len(frame) else 0.0,
                "unique": int(column.nunique(dropna=True)),
                "minimum": numeric.min() if len(numeric) else None,
                "maximum": numeric.max() if len(numeric) else None,
                "mean": numeric.mean() if len(numeric) else None,
                "median": numeric.median() if len(numeric) else None,
            }
        )
    column_profile = pd.DataFrame(
        rows,
        columns=[
            "column",
            "type",
            "missing",
            "missing_pct",
            "unique",
            "minimum",
            "maximum",
            "mean",
            "median",
        ],
    )
    missing = frame.isna().sum().astype(int).rename("missing").to_frame()
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_cells": int(frame.isna().sum().sum()),
        "missing_by_column": missing,
        "types": frame.dtypes.astype(str).rename("type").to_frame(),
        "column_profile": column_profile,
    }


def descriptive_stats(frame: pd.DataFrame, value_column: str) -> pd.Series:
    """Summarize finite numeric observations; invalid and infinite values are excluded."""
    if value_column not in frame:
        raise ValueError(f"Unknown measure: {value_column}")
    values = _numeric(frame[value_column]).dropna()
    if values.empty:
        return pd.Series(
            {
                "count": 0,
                "sum": 0.0,
                "mean": np.nan,
                "median": np.nan,
                "std": np.nan,
                "min": np.nan,
                "max": np.nan,
            }
        )
    return pd.Series(
        {
            "count": int(values.count()),
            "sum": float(values.sum()),
            "mean": float(values.mean()),
            "median": float(values.median()),
            "std": float(values.std()),
            "min": float(values.min()),
            "max": float(values.max()),
        }
    )


def group_summary(frame: pd.DataFrame, group_column: str, value_column: str) -> pd.DataFrame:
    """Return count, sum, mean and median for a selected category."""
    if group_column not in frame or value_column not in frame:
        raise ValueError("Choose existing group and measure columns.")
    data = frame[[group_column]].copy()
    data[value_column] = _numeric(frame[value_column])
    return (
        data.groupby(group_column, dropna=False)[value_column]
        .agg(count="count", total=lambda s: s.sum(min_count=1), mean="mean", median="median")
        .reset_index()
    )


def variance_table(
    frame: pd.DataFrame,
    value_column: str,
    date_column: str | None = None,
    group_column: str | None = None,
    frequency: str = "M",
) -> pd.DataFrame:
    """Compare latest and prior observed periods; percent variance needs a nonzero baseline."""
    for column in [value_column, date_column, group_column]:
        if column is not None and column not in frame:
            raise ValueError(f"Unknown column: {column}")
    keys = [group_column] if group_column else []
    columns = keys + ["actual", "baseline", "variance", "variance_pct", "period", "baseline_period"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    data = frame.copy()
    data[value_column] = _numeric(data[value_column])
    if date_column:
        data[date_column] = pd.to_datetime(data[date_column], errors="coerce", utc=True)
        data = data.dropna(subset=[date_column])
        data["_period"] = (
            data[date_column].dt.tz_convert(None).dt.to_period(frequency).dt.start_time
        )
    else:
        data["_period"] = pd.Timestamp("1970-01-01")
    if data.empty:
        return pd.DataFrame(columns=columns)
    grouped = (
        data.groupby(keys + ["_period"], dropna=False)[value_column].sum(min_count=1).reset_index()
    )
    periods = sorted(grouped["_period"].dropna().unique())
    if not periods:
        return pd.DataFrame(columns=columns)
    latest = periods[-1]
    previous = periods[-2] if len(periods) > 1 else None
    current_rows = grouped[grouped["_period"] == latest]
    baseline_rows = (
        grouped[grouped["_period"] == previous] if previous is not None else grouped.iloc[0:0]
    )
    if keys:
        current = current_rows.set_index(keys)[value_column]
        baseline = baseline_rows.set_index(keys)[value_column]
    else:
        current = pd.Series(
            current_rows[value_column].to_numpy(), index=pd.Index(["All"], name="scope")
        )
        baseline = pd.Series(
            baseline_rows[value_column].to_numpy(),
            index=pd.Index(["All"] if len(baseline_rows) else [], name="scope"),
        )
    result = pd.concat([current.rename("actual"), baseline.rename("baseline")], axis=1)
    result["variance"] = result["actual"] - result["baseline"]
    valid = result["baseline"].notna() & result["baseline"].ne(0)
    result["variance_pct"] = np.where(
        valid, result["variance"] / result["baseline"].abs() * 100, np.nan
    )
    result = result.reset_index()
    result["period"] = pd.Timestamp(latest).strftime("%Y-%m") if date_column else "All data"
    result["baseline_period"] = (
        pd.Timestamp(previous).strftime("%Y-%m")
        if date_column and previous is not None
        else "Unavailable"
    )
    return result


def trend_table(
    frame: pd.DataFrame, value_column: str, date_column: str, group_column: str | None = None
) -> pd.DataFrame:
    """Aggregate the selected measure by month and optional category."""
    data = frame.copy()
    data[date_column] = pd.to_datetime(data[date_column], errors="coerce", utc=True)
    data[value_column] = _numeric(data[value_column])
    data = data.dropna(subset=[date_column])
    data["period"] = data[date_column].dt.tz_convert(None).dt.to_period("M").dt.start_time
    by = ([group_column] if group_column else []) + ["period"]
    return (
        data.groupby(by, dropna=False)[value_column]
        .sum(min_count=1)
        .reset_index()
        .sort_values("period")
    )


def correlation_matrix(frame: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Return pairwise Pearson correlations; correlation does not establish causation."""
    numeric = frame.select_dtypes(include="number")
    if columns is not None:
        missing = [name for name in columns if name not in numeric]
        if missing:
            raise ValueError(f"Not numeric columns: {', '.join(missing)}")
        numeric = numeric[columns]
    return numeric.replace([np.inf, -np.inf], np.nan).corr(min_periods=2)


def anomaly_table(
    frame: pd.DataFrame, value_column: str, date_column: str | None = None
) -> pd.DataFrame:
    """Flag observations at |robust z| >= 3; flags are review signals only."""
    result = frame.copy()
    values = _numeric(result[value_column])
    median = values.median()
    mad = (values - median).abs().median()
    if pd.isna(mad) or mad == 0 or pd.isna(median):
        result["robust_z"] = np.nan
        result["is_anomaly"] = False
    else:
        result["robust_z"] = 0.6745 * (values - median) / mad
        result["is_anomaly"] = result["robust_z"].abs() >= 3
        result["is_anomaly"] = result["is_anomaly"].fillna(False)
    if date_column:
        result[date_column] = pd.to_datetime(result[date_column], errors="coerce")
    return result


def forecast_baseline(
    series: pd.Series, horizon: int = 3, seasonal_period: int = 12
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    """Create a last-value baseline forecast and a time-ordered holdout MAE."""
    if not 1 <= horizon <= 24:
        raise ValueError("Forecast horizon must be between 1 and 24 periods.")
    values = _numeric(series).dropna().reset_index(drop=True)
    if values.empty:
        raise ValueError("At least one finite observation is required to forecast.")
    if len(values) >= seasonal_period + 1:
        holdout = min(horizon, max(1, len(values) // 4), len(values) - seasonal_period)
        test = values.iloc[-holdout:]
        seasonal_predictions = values.iloc[-holdout - seasonal_period : -seasonal_period]
        mae = float((test.to_numpy() - seasonal_predictions.to_numpy()).__abs__().mean())
        forecast_values = values.iloc[-seasonal_period : -seasonal_period + horizon].tolist()
        forecast_values = [float(forecast_values[i % len(forecast_values)]) for i in range(horizon)]
        model = f"Seasonal naive ({seasonal_period})"
    else:
        holdout = min(horizon, max(1, len(values) // 4), len(values) - 1) if len(values) >= 4 else 0
        if holdout:
            train = values.iloc[:-holdout]
            test = values.iloc[-holdout:]
            baseline_value = float(train.iloc[-1])
            mae = float((test - baseline_value).abs().mean())
        else:
            mae = float("nan")
        forecast_values = [float(values.iloc[-1])] * horizon
        model = "Last observation (naive)"
    forecast = pd.DataFrame(
        {
            "step": range(1, horizon + 1),
            "estimate": forecast_values,
            "lower": np.nan,
            "upper": np.nan,
        }
    )
    return forecast, {
        "model": model,
        "holdout_periods": holdout,
        "holdout_mae": mae,
        "observations": int(len(values)),
    }


def scenario_analysis(baseline: float, change_pct: float) -> dict[str, float | str]:
    """Apply a visible analyst assumption to a finite baseline; result is not a prediction."""
    if not np.isfinite(baseline) or not np.isfinite(change_pct):
        raise ValueError("Baseline and assumption must be finite numbers.")
    if not -100 <= change_pct <= 500:
        raise ValueError("Scenario change must be between -100% and +500%.")
    estimate = float(round(baseline * (1 + change_pct / 100), 12))
    return {
        "baseline": float(baseline),
        "assumption_pct": float(change_pct),
        "estimate": float(estimate),
        "change": float(estimate - baseline),
        "label": "Analyst-defined scenario; not a forecast",
    }


def clean_dataset(
    frame: pd.DataFrame, *, drop_duplicates: bool = False, missing_strategy: str = "keep"
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Return a cleaned copy and change counts; supported missing strategies are explicit."""
    if missing_strategy not in {"keep", "drop_rows", "fill_numeric_median", "fill_most_frequent"}:
        raise ValueError("Unsupported missing-value strategy.")
    result = frame.copy()
    before = len(result)
    if drop_duplicates:
        result = result.drop_duplicates()
    duplicate_rows_removed = before - len(result)
    missing_before = int(result.isna().sum().sum())
    if missing_strategy == "drop_rows":
        result = result.dropna()
    elif missing_strategy == "fill_numeric_median":
        for column in result.select_dtypes(include="number").columns:
            median = result[column].replace([np.inf, -np.inf], np.nan).median()
            if pd.notna(median):
                result[column] = result[column].fillna(median)
    elif missing_strategy == "fill_most_frequent":
        for column in result.columns:
            modes = result[column].mode(dropna=True)
            if not modes.empty:
                result[column] = result[column].fillna(modes.iloc[0])
    return result, {
        "rows_removed_as_duplicates": int(duplicate_rows_removed),
        "rows_removed_as_incomplete": int(before - duplicate_rows_removed - len(result)),
        "missing_cells_filled_or_removed": max(0, missing_before - int(result.isna().sum().sum())),
    }
