# Metrics catalog

| Metric | Definition | Source | Invalid-data behavior | Limitation |
|---|---|---|---|---|
| Count | Number of finite numeric observations | Selected field | Invalid, null, and infinite values excluded | Dtype/meaning depends on source |
| Total | Sum of finite numeric observations | Selected measure | Invalid, null, and infinite values excluded | Unit and currency are not inferred |
| Period variance | Latest observed monthly sum minus prior observed monthly sum | Selected measure and date field | Null when no comparison period exists | Months need not be consecutive |
| Percentage variance | Variance / absolute prior sum × 100 | Same | Undefined for missing or zero baseline | Descriptive only |
| Missing cells | Null cell count | Entire loaded dataset | Blank strings are not treated as null | Source-specific missing markers may need mapping |
| Exact duplicate rows | Full-row exact duplicates | Entire loaded dataset | Does not assume a business key | Key uniqueness requires source-specific rules |
| Correlation | Pairwise Pearson coefficient on finite numeric fields | Selected dataset | Pairwise calculations require at least two observations | Correlation does not establish causality |
| Outlier review | Robust z = 0.6745 × (x − median) / MAD; flag if absolute score ≥ 3 | Selected measure | No flags for unavailable or zero MAD | Not a fraud/risk diagnosis |
| Forecast baseline | Seasonal naive when at least one seasonal cycle exists; otherwise last observation | Monthly aggregate | Requires finite observations; horizon 1–24 | Point estimate only; no prediction interval |
| Holdout MAE | Mean absolute error on the latest time-ordered holdout | Forecast baseline | Not calculated with fewer than four observations | Evaluation sample can be too small |
| Scenario estimate | Baseline × (1 + analyst change % / 100) | User-provided assumption | Assumption limited to −100% to +500% | Not a forecast or guaranteed outcome |

All calculations run locally. Financial business definitions such as revenue, margin, and exposure must be validated against the source and are not inferred from field labels.
