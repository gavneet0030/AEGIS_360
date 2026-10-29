"""Write reproducible, explicitly synthetic monthly operating data."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "samples" / "monthly_business_performance.csv"


def demo_rows() -> list[dict[str, object]]:
    regions = {"North": 0, "South": -22_000}
    segments = {"Enterprise": (0, 42), "SMB": (-70_000, 116)}
    rows = []
    for month_index in range(18):
        year, month = 2024 + month_index // 12, month_index % 12 + 1
        period = date(year, month, 1).isoformat()
        for region, region_offset in regions.items():
            for segment, (segment_offset, customer_base) in segments.items():
                revenue = 128_000 + month_index * 2_400 + region_offset + segment_offset
                if period == "2025-06-01" and region == "North" and segment == "Enterprise":
                    revenue += 50_000  # Intentional demo movement for anomaly review.
                customers = customer_base + month_index + (0 if region == "North" else -11)
                operating_cost = round(revenue * (0.67 if segment == "Enterprise" else 0.72))
                rows.append(
                    {
                        "month": period,
                        "region": region,
                        "segment": segment,
                        "revenue": revenue,
                        "operating_cost": operating_cost,
                        "customers": customers,
                    }
                )
    return rows


def write_demo_data(output: Path = DEFAULT_OUTPUT) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = demo_rows()
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(f"Wrote {write_demo_data(args.output):,} synthetic records to {args.output}")
