"""Step 1: poll call sources and apply idempotency checks."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.config import get_settings
from app.models.call_event import CallEvent, CallSource
from app.storage.audit import is_processed

_PHONEBURNER_QUERY = """
SELECT *
FROM `phoneburner_logs.call_events`
WHERE connected = @connected
  AND duration >= @min_duration_seconds
  AND end_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @poll_interval_minutes MINUTE)
  AND recording_gcs_uri IS NOT NULL
"""

_RINGCENTRAL_QUERY = """
SELECT *
FROM `RingCentral.Call_Logs`
WHERE result = @connected_result
  AND duration >= CAST(@min_duration_seconds AS NUMERIC)
  AND finishTime >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @poll_interval_minutes MINUTE)
  AND record_uri IS NOT NULL
"""


async def poll_new_calls() -> list[CallEvent]:
    """Poll BigQuery for recent connected calls and return unprocessed events."""

    settings = get_settings()
    phoneburner_rows, ringcentral_rows = await asyncio.gather(
        _query_phoneburner_rows(
            bq_project=settings.gcp.bq_project,
            min_duration_seconds=settings.pipeline.min_call_duration_seconds,
            poll_interval_minutes=settings.pipeline.poll_interval_minutes,
        ),
        _query_ringcentral_rows(
            bq_project=settings.gcp.bq_project,
            min_duration_seconds=settings.pipeline.min_call_duration_seconds,
            poll_interval_minutes=settings.pipeline.poll_interval_minutes,
        ),
    )

    events = [
        *[_phoneburner_row_to_event(row) for row in phoneburner_rows],
        *[_ringcentral_row_to_event(row) for row in ringcentral_rows],
    ]
    return await _filter_unprocessed(events)


async def check_idempotency(call_id: str) -> bool:
    """Query call_audit_log and return True when call_id was already processed."""

    return await is_processed(call_id)


async def _query_phoneburner_rows(
    *,
    bq_project: str,
    min_duration_seconds: int,
    poll_interval_minutes: int,
) -> list[dict[str, Any]]:
    """Query recent PhoneBurner connected call rows."""

    return await _query_rows(
        bq_project=bq_project,
        query=_PHONEBURNER_QUERY,
        query_parameters=[
            _scalar_query_parameter("connected", "BOOL", True),
            _scalar_query_parameter("min_duration_seconds", "INT64", min_duration_seconds),
            _scalar_query_parameter("poll_interval_minutes", "INT64", poll_interval_minutes),
        ],
    )


async def _query_ringcentral_rows(
    *,
    bq_project: str,
    min_duration_seconds: int,
    poll_interval_minutes: int,
) -> list[dict[str, Any]]:
    """Query recent RingCentral connected call rows."""

    return await _query_rows(
        bq_project=bq_project,
        query=_RINGCENTRAL_QUERY,
        query_parameters=[
            _scalar_query_parameter("connected_result", "STRING", "Call connected"),
            _scalar_query_parameter("min_duration_seconds", "INT64", min_duration_seconds),
            _scalar_query_parameter("poll_interval_minutes", "INT64", poll_interval_minutes),
        ],
    )


async def _query_rows(
    *,
    bq_project: str,
    query: str,
    query_parameters: Sequence[Any],
) -> list[dict[str, Any]]:
    """Run a parameterized BigQuery query in a thread."""

    if not bq_project:
        raise RuntimeError("BQ_PROJECT must be configured for BigQuery polling.")

    return await asyncio.to_thread(
        _query_rows_sync,
        bq_project,
        query,
        query_parameters,
    )


def _query_rows_sync(
    bq_project: str,
    query: str,
    query_parameters: Sequence[Any],
) -> list[dict[str, Any]]:
    """Run a synchronous BigQuery query and return JSON-friendly rows."""

    from google.cloud import bigquery

    client = bigquery.Client(project=bq_project)
    job_config = bigquery.QueryJobConfig(query_parameters=list(query_parameters))
    rows = client.query(query, job_config=job_config).result()
    return [_row_to_dict(row) for row in rows]


def _scalar_query_parameter(name: str, type_: str, value: Any) -> Any:
    """Create a BigQuery scalar query parameter without importing BigQuery at module load."""

    from google.cloud import bigquery

    return bigquery.ScalarQueryParameter(name, type_, value)


async def _filter_unprocessed(events: list[CallEvent]) -> list[CallEvent]:
    """Remove calls that already have successful audit-log rows."""

    processed_flags = await asyncio.gather(*(is_processed(event.call_id) for event in events))
    return [
        event
        for event, already_processed in zip(events, processed_flags, strict=True)
        if not already_processed
    ]


def _phoneburner_row_to_event(row: dict[str, Any]) -> CallEvent:
    """Map a PhoneBurner BigQuery row to the normalized CallEvent model."""

    raw_payload = _with_matching_hints(row)
    agent_name = _join_name(
        _nested_str(raw_payload, "agent", "first_name"),
        _nested_str(raw_payload, "agent", "last_name"),
    )

    return CallEvent(
        call_id=str(_required_value(raw_payload, "call_id")),
        source=CallSource.PHONEBURNER,
        workspace="intake",
        phone_from=_nested_str(raw_payload, "contact", "phone"),
        phone_to=_str_value(raw_payload.get("endpoint")),
        duration_sec=_int_value(raw_payload.get("duration")),
        agent_id=agent_name or None,
        gcs_audio_uri=_str_value(raw_payload.get("recording_gcs_uri")) or None,
        raw_payload=raw_payload,
    )


def _ringcentral_row_to_event(row: dict[str, Any]) -> CallEvent:
    """Map a RingCentral BigQuery row to the normalized CallEvent model."""

    raw_payload = dict(row)

    return CallEvent(
        call_id=_str_value(_required_value(raw_payload, "id")),
        source=CallSource.RINGCENTRAL,
        workspace="medhub",
        phone_from=_str_value(raw_payload.get("from_phonenumber")),
        phone_to=_str_value(raw_payload.get("to_phonenumber")),
        duration_sec=_int_value(raw_payload.get("duration")),
        agent_id=None,
        gcs_audio_uri=None,
        raw_payload=raw_payload,
    )


def _with_matching_hints(row: dict[str, Any]) -> dict[str, Any]:
    """Add normalized fallback matching fields while preserving the full BigQuery row."""

    raw_payload = dict(row)
    contact_name = _join_name(
        _nested_str(raw_payload, "contact", "first_name"),
        _nested_str(raw_payload, "contact", "last_name"),
    )
    if contact_name and not raw_payload.get("name"):
        raw_payload["name"] = contact_name

    contact_email = _nested_str(raw_payload, "contact", "primary_email")
    if contact_email and not raw_payload.get("email"):
        raw_payload["email"] = contact_email

    return raw_payload


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a BigQuery Row into a JSON-friendly dictionary."""

    items = row.items() if hasattr(row, "items") else dict(row).items()
    return {str(key): _plain_value(value) for key, value in items}


def _plain_value(value: Any) -> Any:
    """Convert BigQuery values into JSON-friendly Python values."""

    if isinstance(value, Mapping):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if hasattr(value, "items"):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        if value.is_finite() and value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain_value(item) for item in value]
    return value


def _nested_str(payload: dict[str, Any], *keys: str) -> str:
    """Read a nested field as a string."""

    value: Any = payload
    for key in keys:
        if not isinstance(value, Mapping):
            return ""
        value = value.get(key)
    return _str_value(value)


def _required_value(payload: dict[str, Any], key: str) -> Any:
    """Read a required BigQuery field."""

    value = payload.get(key)
    if value is None or value == "":
        raise ValueError(f"BigQuery row is missing required field {key!r}.")
    return value


def _join_name(first_name: str, last_name: str) -> str:
    """Join nullable first and last name parts."""

    return " ".join(part for part in (first_name.strip(), last_name.strip()) if part)


def _str_value(value: Any) -> str:
    """Convert nullable BigQuery values into strings."""

    if value is None:
        return ""
    return str(value).strip()


def _int_value(value: Any) -> int:
    """Convert BigQuery numeric values into integers."""

    if isinstance(value, Decimal):
        return int(value)
    if value is None or value == "":
        return 0
    return int(value)
