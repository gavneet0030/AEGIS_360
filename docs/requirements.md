# Product requirements and evidence

| Requirement | Implementation | Evidence / status |
|---|---|---|
| Local analyst workflow | Streamlit dashboard with overview, quality, performance, review, forecast/scenario, export, and pipeline tabs | Dashboard smoke test |
| Tabular uploads | CSV, XLSX, JSON arrays/column objects/JSON Lines, Parquet | Parser unit tests; optional PyArrow dependency |
| Upload bounds | 25 MB default, 250,000 rows, 200 columns, 5,000,000 cells; XLSX expansion 150 MB; Parquet expansion 256 MB | Parser checks and tests |
| Data quality | Types, nulls, unique values, numeric range/mean/median, exact duplicate rows | Profiling tests |
| Cleaning | Preview duplicate removal and explicit missing-value choices | Cleaning function tests and dashboard control |
| Deterministic analytics | Descriptive statistics, grouping, monthly trends, variance, correlation, MAD flags, baseline forecast, scenario | Unit tests |
| Excel | Eight report sections plus imported data, bounded rows, formatting and string escaping | Reopen workbook tests |
| Metadata | SQLite job history, hash, status, dimensions, time, error class | Metadata store test |
| Public data | Explicit, bounded World Bank Indicators API v2 adapter for one country/indicator request | Mocked pagination, retry, provenance, and error tests; no live fetch verification |
| Configuration | Validated environment settings and production secret requirement | Configuration tests |
| Security baseline | In-memory source files, allowlisted parsers, zip/row/cell caps, formula escaping, non-root container, read-only container root, XSRF/CORS, secret-free Git patterns | Unit tests, static configuration review |
| Public data | No live adapter | Not implemented; no claims of public-source ingestion |
| Authentication | Optional shared-password app gate | Partial; add managed identity proxy before confidential/public production use |
| Deployment | Docker, Compose, Render Blueprint and CI container smoke workflow | Configuration written; local Docker daemon inaccessible, hosted deployment not created |
