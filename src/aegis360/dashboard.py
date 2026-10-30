"""Local-first AEGIS 360 analyst dashboard."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import sqlite3
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from aegis360.analytics import (
    anomaly_table,
    clean_dataset,
    correlation_matrix,
    descriptive_stats,
    forecast_baseline,
    group_summary,
    profile_dataset,
    scenario_analysis,
    trend_table,
    variance_table,
)
from aegis360.auth import email_is_allowed
from aegis360.exports import build_workbook
from aegis360.ingestion import load_table, safe_upload_name
from aegis360.logging_config import configure_logging
from aegis360.metadata import recent_runs, record_run
from aegis360.settings import load_settings
from aegis360.sources.world_bank import fetch_indicator

LOGGER = logging.getLogger("aegis360.dashboard")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = PROJECT_ROOT / "data" / "samples" / "monthly_business_performance.csv"


def _save_run_metadata(**values: object) -> str | None:
    try:
        return record_run(SETTINGS.database_path, **values)
    except sqlite3.Error as exc:
        LOGGER.error("ingestion_metadata_unavailable", extra={"error_type": type(exc).__name__})
        return None


st.set_page_config(page_title="AEGIS 360 | Decision Intelligence", page_icon="🛡️", layout="wide")
try:
    SETTINGS = load_settings()
except ValueError as exc:
    st.error(f"Application configuration is invalid: {exc}")
    st.stop()
configure_logging(SETTINGS.log_level)


def _authenticate() -> None:
    """Enforce the selected local password or OIDC identity and allowlist gate."""
    if SETTINGS.auth_mode == "oidc":
        required = {
            "redirect_uri",
            "cookie_secret",
            "client_id",
            "client_secret",
            "server_metadata_url",
        }
        try:
            auth_config = st.secrets.get("auth", {})
        except StreamlitSecretNotFoundError:
            auth_config = {}
        if not isinstance(auth_config, Mapping):
            auth_config = {}
        missing = sorted(key for key in required if not auth_config.get(key))
        if missing:
            st.error(
                "OIDC sign-in is selected, but Streamlit authentication settings are missing: "
                + ", ".join(missing)
            )
            st.stop()
        if not st.user.is_logged_in:
            st.title("AEGIS 360 sign in")
            st.button("Continue with your identity provider", on_click=st.login, type="primary")
            st.stop()
        if not st.user.get("email_verified", False):
            st.error("The identity provider did not assert a verified email address.")
            st.button("Sign out", on_click=st.logout)
            st.stop()
        if not email_is_allowed(
            st.user.get("email", ""),
            SETTINGS.oidc_allowed_domains,
            SETTINGS.oidc_allowed_emails,
        ):
            st.error("This identity is not on the AEGIS 360 access allowlist.")
            st.button("Sign out", on_click=st.logout)
            st.stop()
        if st.sidebar.button("Sign out"):
            st.logout()
        st.sidebar.caption("Signed in through the configured identity provider.")
        return

    if not SETTINGS.access_password:
        return
    if st.session_state.get("authenticated"):
        if st.sidebar.button("Sign out"):
            st.session_state["authenticated"] = False
            st.rerun()
        return
    st.title("AEGIS 360 sign in")
    password = st.text_input("Access password", type="password")
    if st.button("Continue", type="primary"):
        if hmac.compare_digest(password.encode("utf-8"), SETTINGS.access_password.encode("utf-8")):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Access denied.")
    st.stop()


_authenticate()

st.markdown(
    """
<style>
  .stApp {background: #f4f7fb;}
  [data-testid="stSidebar"] {background: #10263d;}
  [data-testid="stSidebar"] * {color: #eff6ff !important;}
  .hero {padding: 1.25rem 1.5rem; border-radius: 16px; color: white;
    background: linear-gradient(115deg,#10263d,#1b5274); margin-bottom: .8rem;}
  .hero small {color:#c8dfed; letter-spacing:.12em; text-transform:uppercase;}
  .hero h1 {margin:.25rem 0; color:white;}
  .hero p {margin:0; color:#d7e8f2;}
</style>
<div class="hero"><small>AEGIS 360 · ANALYST WORKBENCH</small>
<h1>Business performance, with evidence.</h1>
<p>Validate a dataset, investigate change, and export the calculations and their limitations.</p></div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 🛡️ AEGIS 360")
    st.caption(f"{SETTINGS.environment.upper()} · LOCAL ANALYTICS")
    data_source = st.radio("Data source", ["Demo sample", "Upload a file", "World Bank indicator"])
    uploaded = None
    wb_country = None
    wb_indicator = None
    wb_start = None
    wb_end = None
    wb_submitted = False
    if data_source == "Upload a file":
        uploaded = st.file_uploader(
            "Load a dataset",
            type=["csv", "xlsx", "json", "parquet"],
            help=f"Maximum {SETTINGS.max_upload_mb} MB, 250,000 rows, 200 columns, 5,000,000 cells.",
        )
    elif data_source == "World Bank indicator":
        st.caption(
            "Fetch one country and indicator on demand. No API key; only the selected public query is sent."
        )
        with st.form("world_bank_request"):
            wb_country = st.selectbox("Country", ["IND", "USA", "GBR", "CAN", "AUS"])
            indicators = {
                "GDP (current US$)": "NY.GDP.MKTP.CD",
                "Population, total": "SP.POP.TOTL",
                "Inflation, annual %": "FP.CPI.TOTL.ZG",
                "Unemployment, total %": "SL.UEM.TOTL.ZS",
            }
            indicator_label = st.selectbox("Indicator", list(indicators))
            wb_indicator = indicators[indicator_label]
            wb_start = st.number_input("From year", min_value=1960, max_value=2100, value=2015)
            wb_end = st.number_input(
                "Through year",
                min_value=1960,
                max_value=2100,
                value=max(1960, datetime.now(timezone.utc).year - 2),
            )
            wb_submitted = st.form_submit_button("Fetch public data")
        if wb_submitted:
            started = time.perf_counter()
            st.session_state.pop("world_bank_request_key", None)
            st.session_state.pop("world_bank_data", None)
            try:
                result = fetch_indicator(wb_country, wb_indicator, int(wb_start), int(wb_end))
                st.session_state["world_bank_data"] = result
                st.session_state["world_bank_duration_ms"] = round(
                    (time.perf_counter() - started) * 1000
                )
                st.session_state["world_bank_request_key"] = (
                    wb_country,
                    wb_indicator,
                    int(wb_start),
                    int(wb_end),
                )
                st.success(f"Fetched {len(result):,} observations from World Bank API v2.")
            except ValueError as exc:
                query_hash = hashlib.sha256(
                    f"{wb_country}|{wb_indicator}|{int(wb_start)}|{int(wb_end)}".encode()
                ).hexdigest()
                if st.session_state.get("last_failed_hash") != query_hash:
                    duration_ms = round((time.perf_counter() - started) * 1000)
                    job_id = _save_run_metadata(
                        status="failed",
                        sha256=query_hash,
                        duration_ms=duration_ms,
                        error_type=type(exc).__name__,
                    )
                    LOGGER.warning(
                        "public_source_fetch_failed",
                        extra={
                            "job_id": job_id,
                            "status": "failed",
                            "duration_ms": duration_ms,
                            "error_type": type(exc).__name__,
                        },
                    )
                    st.session_state["last_failed_hash"] = query_hash
                st.error(f"World Bank request failed: {exc}")
    st.divider()
    st.caption(
        "Uploads are analyzed in memory and are not saved. Only job metadata and a SHA-256 fingerprint are retained locally."
    )

if data_source == "Demo sample":
    raw_data = pd.read_csv(SAMPLE)
    source_label = "Synthetic sample · illustrative values"
    upload_hash = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
elif data_source == "Upload a file" and uploaded is None:
    st.info("Choose a CSV, XLSX, JSON, or Parquet file in the sidebar.")
    st.stop()
elif data_source == "Upload a file":
    upload_bytes = uploaded.getvalue()
    upload_hash = hashlib.sha256(upload_bytes).hexdigest()
    try:
        started = time.perf_counter()
        raw_data = load_table(uploaded.name, upload_bytes, SETTINGS.max_upload_mb * 1024 * 1024)
        duration_ms = round((time.perf_counter() - started) * 1000)
        source_label = f"{safe_upload_name(uploaded.name)} · session only"
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000)
        if st.session_state.get("last_failed_hash") != upload_hash:
            job_id = _save_run_metadata(
                status="failed",
                sha256=upload_hash,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
            )
            LOGGER.warning(
                "ingestion_failed",
                extra={"job_id": job_id, "status": "failed", "error_type": type(exc).__name__},
            )
            st.session_state["last_failed_hash"] = upload_hash
        detail = (
            str(exc)
            if isinstance(exc, ValueError)
            else "The format is malformed or could not be processed safely."
        )
        st.error(f"This dataset could not be loaded: {detail}")
        st.stop()
    if st.session_state.get("last_recorded_hash") != upload_hash:
        job_id = _save_run_metadata(
            status="succeeded",
            sha256=upload_hash,
            rows=len(raw_data),
            columns=len(raw_data.columns),
            duration_ms=duration_ms,
        )
        if job_id:
            LOGGER.info(
                "ingestion_completed",
                extra={
                    "job_id": job_id,
                    "status": "succeeded",
                    "rows": len(raw_data),
                    "columns": len(raw_data.columns),
                    "duration_ms": duration_ms,
                },
            )
        else:
            st.warning("Dataset loaded, but the local job history could not be written.")
        st.session_state["last_recorded_hash"] = upload_hash
else:
    requested_key = (wb_country, wb_indicator, int(wb_start), int(wb_end))
    if st.session_state.get("world_bank_request_key") != requested_key:
        st.info("Submit the World Bank request in the sidebar to load public indicator data.")
        st.stop()
    raw_data = st.session_state["world_bank_data"].copy()
    upload_hash = hashlib.sha256(
        raw_data.to_json(orient="split", date_format="iso", double_precision=15).encode("utf-8")
    ).hexdigest()
    retrieved = raw_data.attrs.get("retrieved_at_utc", "retrieval time unavailable")
    source_label = (
        f"World Bank Indicators API v2 · {wb_country} · {wb_indicator} · retrieved {retrieved} · "
        "CC BY 4.0 default; verify the selected indicator metadata"
    )
    if st.session_state.get("last_recorded_hash") != upload_hash:
        job_id = _save_run_metadata(
            status="succeeded",
            sha256=upload_hash,
            rows=len(raw_data),
            columns=len(raw_data.columns),
            duration_ms=st.session_state.get("world_bank_duration_ms", 0),
        )
        if job_id:
            LOGGER.info(
                "public_source_loaded",
                extra={
                    "job_id": job_id,
                    "status": "succeeded",
                    "rows": len(raw_data),
                    "columns": len(raw_data.columns),
                    "duration_ms": st.session_state.get("world_bank_duration_ms", 0),
                },
            )
        st.session_state["last_recorded_hash"] = upload_hash

if st.session_state.get("cleaned_hash") != upload_hash:
    st.session_state.pop("cleaned_data", None)
    st.session_state.pop("cleaning_changes", None)
    st.session_state.pop("cleaning_parameters", None)
    st.session_state.pop("report_bytes", None)
    st.session_state["cleaned_hash"] = upload_hash

use_cleaned = False
if "cleaned_data" in st.session_state:
    use_cleaned = st.sidebar.toggle(
        "Use previewed cleaned data",
        value=False,
        help="Only available after you preview a cleaning operation.",
    )
data = st.session_state["cleaned_data"] if use_cleaned else raw_data
quality = profile_dataset(data)

date_candidates = [
    column
    for column in data.columns
    if any(token in str(column).lower() for token in ("date", "month", "period", "time"))
]
number_candidates = [
    column
    for column in data.columns
    if pd.api.types.is_numeric_dtype(data[column])
    or pd.to_numeric(data[column], errors="coerce").notna().any()
]
date_column = None
dimension = None
active_date_range = None
selected_dimension_values: list[str] = []

with st.sidebar:
    st.success(f"{len(data):,} rows · {len(data.columns)} columns")
    st.caption(f"Source: {source_label}\n\nFingerprint: `{upload_hash[:12]}`")
    if use_cleaned:
        st.info("Analysis uses the previewed cleaning changes.")

if not number_candidates:
    st.warning(
        "No numeric measures were found. You can still inspect the dataset and its quality report."
    )
    measure = None
else:
    selector_a, selector_b, selector_c = st.columns([1.2, 1, 1])
    with selector_a:
        default_measure = (
            number_candidates.index("value")
            if "value" in number_candidates
            else number_candidates.index("revenue")
            if "revenue" in number_candidates
            else 0
        )
        measure = st.selectbox(
            "Measure",
            number_candidates,
            index=default_measure,
        )
    with selector_b:
        date_column = st.selectbox(
            "Time column",
            ["— none —"] + list(data.columns),
            index=list(data.columns).index(date_candidates[0]) + 1 if date_candidates else 0,
        )
    date_column = None if date_column == "— none —" else date_column
    dimensions = [
        column
        for column in data.columns
        if column not in {measure, date_column} and data[column].nunique(dropna=True) <= 100
    ]
    with selector_c:
        dimension = st.selectbox("Break down by", ["— none —"] + dimensions)
    dimension = None if dimension == "— none —" else dimension

analysis_data = data.copy()
if date_column:
    parsed_dates = pd.to_datetime(analysis_data[date_column], errors="coerce", utc=True)
    valid_dates = parsed_dates.dropna()
    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()
        date_range = (
            st.slider(
                "Date range",
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date),
            )
            if min_date < max_date
            else (min_date, max_date)
        )
        active_date_range = (str(date_range[0]), str(date_range[1]))
        keep = parsed_dates.dt.date.between(date_range[0], date_range[1])
        analysis_data = analysis_data.loc[keep].copy()
    else:
        st.warning(
            "The selected time column contains no valid dates; time-series views are unavailable."
        )
if dimension:
    options = sorted(analysis_data[dimension].dropna().astype(str).unique().tolist())
    selected_dimension_values = st.multiselect(f"Filter {dimension}", options, default=options)
    analysis_data = analysis_data[
        analysis_data[dimension].astype(str).isin(selected_dimension_values)
    ]

tabs = st.tabs(
    [
        "Executive Overview",
        "Dataset & Quality",
        "Performance",
        "Risk Review",
        "Forecast & Scenario",
        "Exports",
        "Health & Pipeline",
    ]
)

variance = pd.DataFrame()
trend = pd.DataFrame()
scenario = None
scenario_change_pct = None
if measure is not None:
    variance = variance_table(analysis_data, measure, date_column, dimension)
    if date_column:
        trend = trend_table(analysis_data, measure, date_column, dimension)

with tabs[0]:
    st.subheader("Executive overview")
    if measure is None:
        st.info(
            "Select a dataset with at least one numeric column to calculate performance measures."
        )
    else:
        stats = descriptive_stats(analysis_data, measure)
        current = float(stats["sum"])
        variance_value = (
            variance["variance"].sum(min_count=1) if not variance.empty else float("nan")
        )
        variance_pct = variance["variance_pct"].mean() if not variance.empty else float("nan")
        cards = st.columns(4)
        cards[0].metric("Records in view", f"{len(analysis_data):,}")
        cards[1].metric(
            f"Total · {measure}",
            f"{current:,.2f}",
            help="Sum of finite numeric values. Unit and currency are source-defined.",
        )
        cards[2].metric(
            "Latest period change",
            f"{variance_value:,.2f}" if pd.notna(variance_value) else "Unavailable",
        )
        cards[3].metric(
            "Mean group variance",
            f"{variance_pct:,.1f}%" if pd.notna(variance_pct) else "Unavailable",
        )
        st.caption(
            f"Source: {source_label}. Figures recalculate from the selected filters. Sample values are synthetic."
        )
        if date_column and not trend.empty:
            chart = (
                px.line(
                    trend,
                    x="period",
                    y=measure,
                    color=dimension,
                    markers=True,
                    template="plotly_white",
                )
                if dimension
                else px.line(trend, x="period", y=measure, markers=True, template="plotly_white")
            )
            st.plotly_chart(chart, width="stretch")
        st.markdown("**Data-backed summary**")
        st.write(
            f"{int(stats['count']):,} finite observations · mean {stats['mean']:,.2f}"
            if pd.notna(stats["mean"])
            else "No finite numeric observations in the current view."
        )
        st.caption(
            "This view describes the loaded data. It does not infer causation, company-wide risk, or currency."
        )

with tabs[1]:
    st.subheader("Dataset explorer and data quality")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Rows", f"{quality['rows']:,}")
    col_b.metric("Columns", f"{quality['columns']:,}")
    col_c.metric("Exact duplicate rows", f"{quality['duplicate_rows']:,}")
    st.dataframe(quality["column_profile"], width="stretch", hide_index=True)
    st.markdown("**Preview source rows**")
    st.dataframe(data.head(500), width="stretch", hide_index=True)
    st.markdown("**Cleaning preview**")
    clean_a, clean_b = st.columns(2)
    with clean_a:
        drop_duplicates = st.checkbox("Remove exact duplicate rows", key="clean_dedup")
    with clean_b:
        missing_strategy = st.selectbox(
            "Missing value strategy",
            ["keep", "drop_rows", "fill_numeric_median", "fill_most_frequent"],
            format_func=lambda value: {
                "keep": "Keep missing values",
                "drop_rows": "Drop rows with missing values",
                "fill_numeric_median": "Fill numeric values with median",
                "fill_most_frequent": "Fill with most frequent value",
            }[value],
        )
    if st.button("Preview cleaning changes"):
        cleaned, changes = clean_dataset(
            raw_data, drop_duplicates=drop_duplicates, missing_strategy=missing_strategy
        )
        st.session_state["cleaned_data"] = cleaned
        st.session_state["cleaning_changes"] = changes
        st.session_state["cleaning_parameters"] = {
            "remove_exact_duplicates": bool(drop_duplicates),
            "missing_value_strategy": missing_strategy,
        }
        st.session_state["cleaned_hash"] = upload_hash
        st.rerun()
    if "cleaned_data" in st.session_state:
        st.write("Cleaning preview changes", st.session_state["cleaning_changes"])
        st.caption(
            "The original data is unchanged. Toggle ‘Use previewed cleaned data’ in the sidebar to analyze the preview."
        )
        st.dataframe(st.session_state["cleaned_data"].head(100), width="stretch", hide_index=True)

with tabs[2]:
    st.subheader("Business performance and variance")
    if measure is None:
        st.info("A numeric measure is required for performance analysis.")
    else:
        st.caption(
            "Variance compares the latest observed month with the previous observed month. Percentage is undefined when its baseline is missing or zero."
        )
        st.dataframe(variance, width="stretch", hide_index=True)
        if dimension:
            st.markdown(f"**Summary by {dimension}**")
            st.dataframe(
                group_summary(analysis_data, dimension, measure), width="stretch", hide_index=True
            )
        numeric_cols = analysis_data.select_dtypes(include="number").columns.tolist()
        if len(numeric_cols) >= 2:
            st.markdown(
                "**Correlation (descriptive only; correlation does not establish causation)**"
            )
            st.dataframe(correlation_matrix(analysis_data), width="stretch")

with tabs[3]:
    st.subheader("Risk and anomaly review")
    if measure is None:
        st.info("A numeric measure is required to calculate statistical review signals.")
    else:
        st.caption(
            "Flags use a robust median/MAD threshold on the selected measure. They are investigation cues, not fraud, misconduct, or causal findings."
        )
        signals = anomaly_table(analysis_data, measure, date_column)
        flagged = signals[signals["is_anomaly"]].sort_values(
            "robust_z", key=lambda series: series.abs(), ascending=False
        )
        st.metric("Observations flagged for review", f"{len(flagged):,}")
        if flagged.empty:
            st.info("No observations crossed the robust threshold in the current view.")
        else:
            st.dataframe(flagged, width="stretch", hide_index=True)

with tabs[4]:
    st.subheader("Baseline forecasts and analyst scenarios")
    if measure is None or date_column is None:
        st.info("Choose a numeric measure and a time column to see a baseline forecast.")
    elif trend.empty:
        st.info("No valid dated observations are available in the current view.")
    else:
        forecast_horizon = st.slider(
            "Forecast horizon (periods)", min_value=1, max_value=12, value=3
        )
        period_series = trend.groupby("period")[measure].sum(min_count=1).sort_index()
        finite_periods = (
            pd.to_numeric(period_series, errors="coerce")
            .replace([float("inf"), float("-inf")], float("nan"))
            .dropna()
        )
        if finite_periods.empty:
            st.info("No finite monthly values are available for forecasting or scenario analysis.")
        else:
            try:
                forecast, evaluation = forecast_baseline(finite_periods, horizon=forecast_horizon)
                st.caption(
                    f"Model: {evaluation['model']} · observations: {evaluation['observations']} · holdout MAE: {evaluation['holdout_mae']:,.2f}"
                    if pd.notna(evaluation["holdout_mae"])
                    else f"Model: {evaluation['model']} · not enough data for a holdout evaluation."
                )
                st.dataframe(forecast, width="stretch", hide_index=True)
            except ValueError as exc:
                st.info(str(exc))
            st.caption(
                "Forecast steps follow observed monthly records. Missing calendar months are not imputed."
            )
            baseline = float(finite_periods.iloc[-1])
            change_pct = st.slider(
                "Scenario assumption: change from latest period",
                min_value=-100,
                max_value=100,
                value=0,
                step=5,
            )
            scenario_change_pct = float(change_pct)
            scenario = scenario_analysis(baseline, float(change_pct))
            st.metric(
                "Scenario estimate",
                f"{scenario['estimate']:,.2f}",
                delta=f"{scenario['change']:,.2f}",
            )
            st.warning("Analyst-defined assumption. This is not a forecast or guaranteed outcome.")

report_context = {
    "source_sha256": upload_hash,
    "cleaned_data": bool(use_cleaned),
    "measure": measure,
    "date_column": date_column,
    "date_range": active_date_range,
    "dimension": dimension,
    "dimension_values": selected_dimension_values,
    "scenario_change_pct": scenario_change_pct,
}
report_context_hash = hashlib.sha256(
    json.dumps(report_context, sort_keys=True, default=str).encode("utf-8")
).hexdigest()
if st.session_state.get("report_context_hash") != report_context_hash:
    st.session_state.pop("report_bytes", None)
    st.session_state["report_context_hash"] = report_context_hash

with tabs[5]:
    st.subheader("Excel and report exports")
    st.write(
        "The analyst workbook includes summary, KPIs, profile, data quality, variance, trend, scenario, methodology, and imported records."
    )
    if st.button("Generate analyst workbook", type="primary"):
        try:
            cleaning_applied = use_cleaned and st.session_state.get("cleaned_hash") == upload_hash
            processing = {
                "source_sha256": upload_hash,
                "input_rows": len(raw_data),
                "exported_rows": len(data),
                "cleaning_applied": cleaning_applied,
                "cleaning_parameters": (
                    st.session_state.get("cleaning_parameters", {}) if cleaning_applied else "none"
                ),
                "cleaning_changes": (
                    st.session_state.get("cleaning_changes", {}) if cleaning_applied else {}
                ),
            }
            report = build_workbook(
                data, quality, variance, trend, scenario, source_label, processing=processing
            )
            st.session_state["report_bytes"] = report
            st.success(f"Workbook generated: {len(report) / 1024:,.0f} KB")
        except (ValueError, OSError) as exc:
            st.error(f"Workbook could not be generated: {exc}")
    if "report_bytes" in st.session_state:
        st.download_button(
            "Download AEGIS360_Analyst_Report.xlsx",
            data=st.session_state["report_bytes"],
            file_name="AEGIS360_Analyst_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    st.caption(
        "Strings beginning with spreadsheet formula markers are escaped. The workbook contains values and does not depend on formula recalculation."
    )

with tabs[6]:
    st.subheader("Application health and ingestion history")
    st.write(
        {
            "Environment": SETTINGS.environment,
            "Database": "SQLite metadata only",
            "Data directory": str(SETTINGS.data_dir),
            "Upload storage": "In-memory; source files not persisted",
        }
    )
    try:
        runs = recent_runs(SETTINGS.database_path)
        st.metric("Recorded ingestion jobs", f"{len(runs):,}")
        if runs:
            st.dataframe(
                pd.DataFrame(
                    runs,
                    columns=[
                        "Job ID",
                        "Created (UTC)",
                        "Status",
                        "SHA-256",
                        "Rows",
                        "Columns",
                        "Duration ms",
                        "Error type",
                    ],
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No upload jobs have been recorded in this data directory yet.")
        st.success("Metadata database is available.")
    except (OSError, RuntimeError) as exc:
        st.error(f"Metadata store is unavailable: {type(exc).__name__}")
    st.caption(
        "For public deployment, place the app behind a managed identity-aware access proxy. The optional shared password is a basic gate, not SSO, user roles, or a compliance control."
    )

st.divider()
st.caption(
    "AEGIS 360 · local-first analytics · no external AI; World Bank data is fetched only on explicit request."
)
