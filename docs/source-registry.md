# Source registry

`config/sources.toml` is the machine-readable registry for the sources that are currently implemented.

| Source | Status | Data handling | Terms / provenance |
|---|---|---|---|
| `synthetic_demo` | Implemented | Bundled sample CSV | Generated deterministically by `scripts/generate_demo_data.py`; no real company data |
| `user_upload` | Implemented | In-memory per session; only job metadata and SHA-256 are retained | Uploader is responsible for rights and appropriate handling |
| `world_bank_indicators_v2` | Implemented, user-triggered | One country/indicator response is held in session memory; job metadata and hash only are stored | API is keyless. World Bank datasets default to CC BY 4.0 unless indicator metadata says otherwise; verify the selected indicator and preserve required attribution |

World Bank indicator requests are implemented through the official V2 Indicators API. The adapter limits timeout, retries, response bytes, pages, observations, and date range. It fetches one country and one indicator so it creates no cross-source join. Automated tests use mocked HTTP responses; a bounded live fetch for U.S. population, 2021–2022, returned two observations on 2026-10-30. Future candidates include official SEC EDGAR filings, FRED, and CFPB complaints. Before adding another adapter, document terms, fetch limits, keys, grain, freshness, retry behavior, and a deterministic mocked-response test. These sources must not be joined without a defensible key and a stated analytical method.

Source URLs for evaluation:

- [SEC EDGAR](https://www.sec.gov/edgar/search/)
- [World Bank Open Data](https://data.worldbank.org/)
- [FRED](https://fred.stlouisfed.org/)
- [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/)

The adapter uses the World Bank [V2 Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392). The World Bank says API keys are not required, and JSON responses are available with `format=json` ([V2 API details](https://datahelpdesk.worldbank.org/knowledgebase/articles/1886674-new-features-and-enhancements-to-the-v2-api)). World Bank catalog datasets default to CC BY 4.0 unless specific metadata says otherwise ([summary terms](https://data.worldbank.org/summary-terms-of-use)).
