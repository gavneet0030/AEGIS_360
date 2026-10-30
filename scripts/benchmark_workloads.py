"""Benchmark deterministic, synthetic processing workloads at supported row counts."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aegis360.analytics import (  # noqa: E402
    anomaly_table,
    forecast_baseline,
    profile_dataset,
    trend_table,
    variance_table,
)
from aegis360.exports import build_workbook  # noqa: E402
from aegis360.ingestion import load_table  # noqa: E402


def synthetic_csv(rows: int) -> bytes:
    dates = pd.date_range("2019-01-01", periods=84, freq="MS")
    frame = pd.DataFrame(
        {
            "month": dates.take([index % len(dates) for index in range(rows)]).strftime("%Y-%m-%d"),
            "segment": [f"Segment-{index % 4}" for index in range(rows)],
            "revenue": [
                100_000 + (index % 84) * 210 + (index % 4) * 1_000 for index in range(rows)
            ],
            "cost": [60_000 + (index % 84) * 130 + (index % 4) * 750 for index in range(rows)],
            "customers": [50 + (index % 84) * 3 + (index % 4) * 10 for index in range(rows)],
            "score": [(index % 1000) / 10 for index in range(rows)],
        }
    )
    return frame.to_csv(index=False).encode("utf-8")


def timed(operation):
    started = time.perf_counter()
    result = operation()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return result, elapsed_ms


def benchmark(rows: int) -> dict[str, object]:
    payload = synthetic_csv(rows)
    data, ingest_ms = timed(lambda: load_table("bench.csv", payload))
    quality, analytics_ms = timed(lambda: profile_dataset(data))
    trend, trend_ms = timed(lambda: trend_table(data, "revenue", "month", "segment"))
    variance, variance_ms = timed(lambda: variance_table(data, "revenue", "month", "segment"))
    anomalies, anomaly_ms = timed(lambda: anomaly_table(data, "revenue", "month"))
    values = trend.groupby("period")["revenue"].sum(min_count=1).sort_index()
    _, forecast_ms = timed(lambda: forecast_baseline(values))
    workbook, export_ms = timed(
        lambda: build_workbook(data, quality, variance, trend, source="Synthetic benchmark")
    )
    return {
        "rows": rows,
        "columns": len(data.columns),
        "input_csv_mb": round(len(payload) / (1024 * 1024), 2),
        "ingestion_ms": ingest_ms,
        "profile_ms": analytics_ms,
        "trend_ms": trend_ms,
        "variance_ms": variance_ms,
        "anomaly_ms": anomaly_ms,
        "forecast_ms": forecast_ms,
        "xlsx_export_ms": export_ms,
        "xlsx_output_mb": round(len(workbook) / (1024 * 1024), 2),
        "anomaly_flags": int(anomalies["is_anomaly"].sum()),
    }


if __name__ == "__main__":
    for size in (1_000, 10_000, 100_000):
        print(json.dumps(benchmark(size)), flush=True)
