# Data dictionary

The source determines the uploaded dataset's schema. AEGIS 360 does not rename fields or infer currency, company ownership, margins, or exposure.

## Synthetic sample: `monthly_business_performance.csv`

| Field | Type | Grain | Meaning |
|---|---|---|---|
| `month` | ISO date | Monthly | Synthetic observation period, first day of month |
| `region` | Text category | Region-month-segment | Synthetic region label (`North`, `South`) |
| `segment` | Text category | Region-month-segment | Synthetic customer segment (`Enterprise`, `SMB`) |
| `revenue` | Integer | Region-month-segment | Illustrative synthetic revenue units; no currency is specified |
| `operating_cost` | Integer | Region-month-segment | Illustrative synthetic operating cost units |
| `customers` | Integer | Region-month-segment | Illustrative synthetic customer count |

The sample has 72 observations across 18 months, two regions, and two segments. A deliberate June 2025 North/Enterprise movement exercises the outlier review. This is synthetic testing material, not a real company result.

## Upload profile fields

The profile reports inferred pandas dtype, missing-cell count and percentage, distinct non-null values, and finite numeric minimum, maximum, mean, and median. These are descriptive profiling results; inferred dtypes may require analyst correction.
