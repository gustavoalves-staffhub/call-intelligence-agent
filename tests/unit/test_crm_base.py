"""Tests for shared Twenty CRM GraphQL behavior."""

from __future__ import annotations

from typing import Any

import pytest

from app.adapters.crm import base
from app.adapters.crm.base import TwentyGraphQLClient


class _FakeResponse:
    """Minimal httpx response stand-in for GraphQL retry tests."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.is_success = True
        self.status_code = 200
        self.text = ""

    def json(self) -> dict[str, Any]:
        """Return the configured JSON payload."""

        return self._payload


async def test_gql_request_retries_twenty_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Twenty token/rate limit errors should be retried up to three times."""

    responses = [
        _FakeResponse(
            {
                "errors": [
                    {
                        "message": "Limit reached: token rate exceeded",
                        "extensions": {"code": "BAD_USER_INPUT"},
                    }
                ]
            }
        ),
        _FakeResponse(
            {
                "errors": [
                    {
                        "message": "Limit reached: token rate exceeded",
                        "extensions": {"code": "BAD_USER_INPUT"},
                    }
                ]
            }
        ),
        _FakeResponse(
            {
                "errors": [
                    {
                        "message": "Limit reached: token rate exceeded",
                        "extensions": {"code": "BAD_USER_INPUT"},
                    }
                ]
            }
        ),
        _FakeResponse({"data": {"ok": True}}),
    ]
    sleep_calls: list[int] = []

    class FakeAsyncClient:
        """AsyncClient test double that returns queued responses."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, *args: Any, **kwargs: Any) -> _FakeResponse:
            return responses.pop(0)

    async def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(base.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(base.asyncio, "sleep", fake_sleep)

    client = TwentyGraphQLClient("https://crm.example", "token")
    data = await client.gql_request("query Test { ok }")

    assert data == {"ok": True}
    assert sleep_calls == [60, 60, 60]
