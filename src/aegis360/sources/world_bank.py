"""Bounded World Bank Indicators API v2 adapter."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

BASE_URL = "https://api.worldbank.org/v2"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_ROWS = 500
MAX_PAGES = 3


def _request_bytes(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "AEGIS360/0.2"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("World Bank response exceeded the 2 MB limit.")
    return payload


def fetch_indicator(
    country: str,
    indicator: str,
    start_year: int,
    end_year: int,
    *,
    timeout: float = 10,
    transport=_request_bytes,
    sleeper=time.sleep,
) -> pd.DataFrame:
    """Fetch one country's one World Bank indicator over a bounded year range.

    Uses the public V2 Indicators API, which does not require an API key. Source rows are
    returned as observations and are not joined with other datasets.
    """
    country = country.strip().upper()
    indicator = indicator.strip()
    if not re.fullmatch(r"[A-Z]{2,3}", country):
        raise ValueError("Country must be a two- or three-letter World Bank country code.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{2,40}", indicator):
        raise ValueError("Indicator code contains unsupported characters.")
    if not isinstance(start_year, int) or not isinstance(end_year, int):
        raise ValueError("Start and end years must be integers.")
    if not (1900 <= start_year <= end_year <= 2100) or end_year - start_year > 100:
        raise ValueError("Choose an ordered year range from 1900–2100, no longer than 100 years.")
    if not 1 <= timeout <= 20:
        raise ValueError("Request timeout must be between 1 and 20 seconds.")

    endpoint = f"{BASE_URL}/country/{country}/indicator/{indicator}"
    parameters = {"format": "json", "per_page": 200, "date": f"{start_year}:{end_year}"}
    records: list[dict[str, object]] = []
    page_count = None
    for page in range(1, MAX_PAGES + 1):
        parameters["page"] = page
        url = f"{endpoint}?{urlencode(parameters)}"
        for attempt in range(3):
            try:
                raw = transport(url, timeout)
                break
            except HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise ValueError(f"World Bank API returned HTTP {exc.code}.") from exc
                sleeper(0.25 * (2**attempt))
            except (URLError, TimeoutError, OSError) as exc:
                if attempt == 2:
                    raise ValueError(
                        "World Bank API request failed after bounded retries."
                    ) from exc
                sleeper(0.25 * (2**attempt))
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("World Bank response exceeded the 2 MB limit.")
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
            raise ValueError("World Bank API returned invalid JSON.") from exc
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
            raise ValueError("World Bank API returned an unexpected response shape.")
        metadata = payload[0]
        if "message" in metadata:
            raise ValueError("World Bank API rejected the country, indicator, or date range.")
        try:
            page_count = int(metadata.get("pages", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("World Bank response has invalid pagination metadata.") from exc
        if not 1 <= page_count <= MAX_PAGES:
            raise ValueError("World Bank result exceeds the configured page limit.")
        observations = payload[1]
        if observations is None:
            observations = []
        if not isinstance(observations, list):
            raise ValueError("World Bank observation list has an invalid shape.")
        if len(records) + len(observations) > MAX_ROWS:
            raise ValueError("World Bank result exceeds the 500-observation limit.")
        records.extend(observations)
        if page >= page_count:
            break

    if not records:
        raise ValueError("World Bank returned no observations for the selected request.")

    normalized = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("World Bank observation has an invalid shape.")
        country_info = record.get("country") or {}
        indicator_info = record.get("indicator") or {}
        if not isinstance(country_info, dict) or not isinstance(indicator_info, dict):
            raise ValueError("World Bank observation has invalid country or indicator metadata.")
        try:
            year = int(record.get("date"))
        except (TypeError, ValueError) as exc:
            raise ValueError("World Bank observation has an invalid year.") from exc
        if not start_year <= year <= end_year:
            raise ValueError("World Bank observation year falls outside the requested range.")
        normalized.append(
            {
                "country_code": record.get("countryiso3code") or country,
                "country": country_info.get("value"),
                "indicator_code": indicator_info.get("id") or indicator,
                "indicator": indicator_info.get("value"),
                "year": year,
                "period": pd.to_datetime(f"{year}-01-01", errors="coerce"),
                "value": pd.to_numeric(record.get("value"), errors="coerce"),
                "unit": record.get("unit"),
                "observation_status": record.get("obs_status"),
                "decimal_places": record.get("decimal"),
            }
        )
    frame = pd.DataFrame(normalized)
    frame = frame.sort_values("year").reset_index(drop=True)
    frame["year"] = frame["year"].astype(int)
    frame.attrs["source_id"] = "world_bank_indicators_v2"
    frame.attrs["source_url"] = endpoint
    frame.attrs["source_license"] = (
        "World Bank datasets default to CC BY 4.0 unless specific metadata says otherwise."
    )
    frame.attrs["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    frame.attrs["request"] = {
        "country": country,
        "indicator": indicator,
        "start_year": start_year,
        "end_year": end_year,
    }
    return frame
