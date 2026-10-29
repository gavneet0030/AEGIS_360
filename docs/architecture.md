# Architecture

The MVP is a single-process Streamlit application. The interface reads either a bundled synthetic sample or an uploaded in-memory table, then calls pure analysis helpers for profiles, period variance, and robust outlier flags. Excel generation is an isolated export helper.

```text
CSV / XLSX / JSON / Parquet ──> guarded parser ──> in-memory DataFrame
                                                    ├─> quality profile
                                                    ├─> variance and outliers
                                                    ├─> Plotly dashboard
                                                    └─> Excel workbook
```

The application has no network calls, external AI, database, authentication, or scheduled jobs. Upload data is not written to disk. The included sample is synthetic. These choices keep the initial local analyst flow small and inspectable; they are not production deployment controls.
