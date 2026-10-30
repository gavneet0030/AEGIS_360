import warnings

import numpy as np
import pandas as pd
import pytest

from aegis360.analytics import (
    anomaly_table,
    clean_dataset,
    correlation_matrix,
    descriptive_stats,
    forecast_baseline,
    group_summary,
    profile_dataset,
    scenario_analysis,
    trend_table,
    variance_table,
)


def test_variance_uses_previous_observed_month_and_zero_baseline_is_undefined():
    frame = pd.DataFrame(
        {
            "month": ["2025-01-01", "2025-02-01", "2025-01-01", "2025-02-01"],
            "region": ["A", "A", "B", "B"],
            "value": [0, 5, 10, 12],
        }
    )
    result = variance_table(frame, "value", "month", "region").set_index("region")
    assert result.loc["A", "variance"] == 5
    assert pd.isna(result.loc["A", "variance_pct"])
    assert result.loc["B", "variance_pct"] == 20


def test_profile_counts_nulls_exact_duplicates_and_column_statistics():
    result = profile_dataset(pd.DataFrame({"x": [1, 1], "y": [None, None]}))
    assert result["missing_cells"] == 2
    assert result["duplicate_rows"] == 1
    assert result["column_profile"].set_index("column").loc["x", "unique"] == 1


def test_descriptive_stats_excludes_infinite_and_invalid_values():
    result = descriptive_stats(pd.DataFrame({"value": [1.0, 3.0, np.inf, "bad", None]}), "value")
    assert result["count"] == 2
    assert result["mean"] == 2
    empty = descriptive_stats(pd.DataFrame({"value": [np.inf, "bad"]}), "value")
    assert empty["count"] == 0
    assert pd.isna(empty["mean"])


def test_group_summary_and_trend_are_deterministic():
    frame = pd.DataFrame(
        {
            "month": ["2025-01-02", "2025-01-20", "2025-02-01"],
            "region": ["N", "N", "S"],
            "value": [3, 7, 10],
        }
    )
    assert group_summary(frame, "region", "value").set_index("region").loc["N", "total"] == 10
    trend = trend_table(frame, "value", "month")
    assert len(trend) == 2
    assert trend.iloc[-1]["value"] == 10


def test_correlation_is_pairwise_and_does_not_claim_causation():
    frame = pd.DataFrame({"a": [1, 2, 3], "b": [2, 4, 6]})
    assert correlation_matrix(frame).loc["a", "b"] == pytest.approx(1)


def test_anomaly_flags_extreme_value_and_handles_constant_or_null_series():
    result = anomaly_table(pd.DataFrame({"value": [10, 11, 9, 10, 100]}), "value")
    assert result.iloc[-1]["is_anomaly"]
    constant = anomaly_table(pd.DataFrame({"value": [2, 2, 2]}), "value")
    assert not constant["is_anomaly"].any()
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        missing = anomaly_table(pd.DataFrame({"value": [None, np.inf]}), "value")
    assert not missing["is_anomaly"].any()


def test_forecast_baseline_is_time_ordered_and_checks_horizon():
    forecast, evaluation = forecast_baseline(pd.Series([1, 2, 3, 4, 5, 7]), horizon=2)
    assert forecast["estimate"].tolist() == [7.0, 7.0]
    assert evaluation["model"] == "Last observation (naive)"
    assert evaluation["holdout_mae"] == 2.0
    with pytest.raises(ValueError, match="horizon"):
        forecast_baseline(pd.Series([1]), horizon=25)
    with pytest.raises(ValueError, match="observation"):
        forecast_baseline(pd.Series([np.nan]))


def test_seasonal_naive_uses_same_season_observations():
    forecast, evaluation = forecast_baseline(pd.Series(range(1, 15)), horizon=2, seasonal_period=12)
    assert evaluation["model"].startswith("Seasonal naive")
    assert forecast["estimate"].tolist() == [3.0, 4.0]
    assert evaluation["holdout_mae"] == 12


def test_scenario_validates_assumptions_and_labels_estimate():
    result = scenario_analysis(100, 10)
    assert result["estimate"] == 110
    assert "not a forecast" in result["label"]
    with pytest.raises(ValueError, match="finite"):
        scenario_analysis(float("inf"), 10)
    with pytest.raises(ValueError, match="between"):
        scenario_analysis(100, 600)


def test_cleaning_returns_copy_and_change_counts():
    original = pd.DataFrame({"value": [1.0, 1.0, None], "label": ["a", "a", "b"]})
    cleaned, changes = clean_dataset(
        original, drop_duplicates=True, missing_strategy="fill_numeric_median"
    )
    assert len(original) == 3
    assert len(cleaned) == 2
    assert cleaned["value"].isna().sum() == 0
    assert changes["rows_removed_as_duplicates"] == 1
    assert changes["missing_cells_filled_or_removed"] == 1
    with pytest.raises(ValueError, match="Unsupported"):
        clean_dataset(original, missing_strategy="invent")
