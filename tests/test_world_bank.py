import json
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from aegis360.sources.world_bank import fetch_indicator


def response(records, pages=1):
    return json.dumps([{"page": 1, "pages": pages}, records]).encode("utf-8")


def observation(year, value):
    return {
        "countryiso3code": "IND",
        "date": str(year),
        "value": value,
        "unit": "",
        "obs_status": "",
        "decimal": 0,
        "country": {"id": "IN", "value": "India"},
        "indicator": {"id": "SP.POP.TOTL", "value": "Population, total"},
    }


def test_world_bank_adapter_normalizes_response_and_records_provenance():
    calls = []

    def transport(url, timeout):
        calls.append((url, timeout))
        return response([observation(2022, 1_400), observation(2023, None)])

    result = fetch_indicator("in", "SP.POP.TOTL", 2022, 2023, transport=transport)
    assert result["year"].tolist() == [2022, 2023]
    assert result.loc[0, "value"] == 1400
    assert result.loc[1, "value"] is None or result.loc[1, "value"] != result.loc[1, "value"]
    assert result.attrs["source_id"] == "world_bank_indicators_v2"
    assert result.attrs["request"]["country"] == "IN"
    query = parse_qs(urlparse(calls[0][0]).query)
    assert query["date"] == ["2022:2023"]
    assert calls[0][1] == 10


def test_world_bank_adapter_paginates_and_retries_transient_errors():
    attempts = []
    sleeps = []

    def transport(url, timeout):
        query = parse_qs(urlparse(url).query)
        page = int(query["page"][0])
        attempts.append(page)
        if len(attempts) == 1:
            raise URLError("temporary")
        if page == 1:
            return response([observation(2022, 1)], pages=2)
        return json.dumps([{"page": 2, "pages": 2}, [observation(2023, 2)]]).encode()

    result = fetch_indicator(
        "IND", "SP.POP.TOTL", 2022, 2023, transport=transport, sleeper=sleeps.append
    )
    assert result["value"].tolist() == [1, 2]
    assert attempts == [1, 1, 2]
    assert sleeps == [0.25]


@pytest.mark.parametrize(
    "country,indicator,start,end",
    [
        ("all", "SP.POP.TOTL", 2020, 2024),
        ("IN", "../bad", 2020, 2024),
        ("IN", "SP.POP.TOTL", 2025, 2020),
        ("IN", "SP.POP.TOTL", 1800, 2020),
    ],
)
def test_world_bank_adapter_rejects_unbounded_or_invalid_requests(country, indicator, start, end):
    with pytest.raises(ValueError):
        fetch_indicator(country, indicator, start, end, transport=lambda *_: b"[]")


def test_world_bank_adapter_rejects_bad_response_and_page_overflow():
    with pytest.raises(ValueError, match="invalid JSON"):
        fetch_indicator("IN", "SP.POP.TOTL", 2020, 2021, transport=lambda *_: b"{")
    with pytest.raises(ValueError, match="page limit"):
        fetch_indicator("IN", "SP.POP.TOTL", 2020, 2021, transport=lambda *_: response([], pages=9))
