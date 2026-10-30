# Architecture

The application is a single-process Streamlit analyst workbench. The interface reads a bundled synthetic sample, an uploaded in-memory table, or an explicitly requested World Bank observation set. Pure analysis helpers calculate profiles, period variance, trends, correlations, robust review signals, and simple forecast/scenario outputs. Excel generation is an isolated export helper. SQLite stores operational job metadata only.

```text
CSV / XLSX / JSON / Parquet ──> guarded parser ──> in-memory DataFrame
                                                    ├─> quality profile
                                                    ├─> variance, trends, correlations, outliers
                                                    ├─> Plotly dashboard and forecast baseline
                                                    └─> Excel workbook
World Bank API (explicit request) ──────────────────────┘
                                  ingestion metadata ──> SQLite
```

The World Bank adapter is the only application data source that makes an outbound request, and it runs only after an explicit form submission. There is no external AI, scheduled ingestion, multi-user dataset storage, or AEGIS public REST API. Password mode is a basic shared gate; optional OIDC mode delegates identity to a configured provider and applies an email/domain allowlist. OIDC does not implement roles. Upload data is not written to disk, and the included sample is synthetic. These controls do not constitute production security certification.
