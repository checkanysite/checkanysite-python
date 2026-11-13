"""The client's settings: where the key and base URL come from, the headers every call sends."""

from __future__ import annotations

import asyncio
import threading

import httpx
import pytest
import respx
from support import API_KEY, BASE_URL, usage_json

from checkanysite import APIError, AsyncCheckAnySite, CheckAnySite, __version__
from checkanysite._base_client import _OwnedAsyncClient, _OwnedClient


def test_reads_the_key_and_base_url_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHECKANYSITE_API_KEY", "cas_live_from_env")
    monkeypatch.setenv("CHECKANYSITE_BASE_URL", "https://checkanysite.com/api/v1/")
    with CheckAnySite() as client:
        assert client.api_key == "cas_live_from_env"
        # A trailing slash is dropped, so paths join cleanly.
        assert client.base_url == "https://checkanysite.com/api/v1"


def test_arguments_win_over_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHECKANYSITE_API_KEY", "cas_live_from_env")
    monkeypatch.setenv("CHECKANYSITE_BASE_URL", "https://elsewhere.test/v1")
    with CheckAnySite(api_key="cas_live_passed", base_url=BASE_URL) as client:
        assert client.api_key == "cas_live_passed"
        assert client.base_url == BASE_URL


def test_defaults_to_the_public_api_with_a_30_second_timeout_and_two_retries() -> None:
    with CheckAnySite(api_key=API_KEY) as client:
        assert client.base_url == "https://api.checkanysite.com/v1"
        assert client.timeout == 30.0
        assert client.max_retries == 2


def test_refuses_to_start_without_a_key() -> None:
    with pytest.raises(APIError, match="CHECKANYSITE_API_KEY"):
        CheckAnySite()
    with pytest.raises(APIError, match="CHECKANYSITE_API_KEY"):
        AsyncCheckAnySite(api_key="")


def test_refuses_a_negative_retry_count() -> None:
    with pytest.raises(ValueError, match="max_retries"):
        CheckAnySite(api_key=API_KEY, max_retries=-1)


def test_sends_the_key_user_agent_and_timeout(client: CheckAnySite, api: respx.MockRouter) -> None:
    route = api.get("/usage").respond(200, json=usage_json())
    client.usage.retrieve()
    request = route.calls.last.request
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert request.headers["user-agent"] == f"checkanysite-python/{__version__}"
    assert request.headers["accept"] == "application/json"
    # A GET changes nothing, so it carries no idempotency key.
    assert "idempotency-key" not in request.headers
    assert request.extensions["timeout"] == httpx.Timeout(30.0).as_dict()


def test_a_timeout_of_its_own_applies_to_every_request(api: respx.MockRouter) -> None:
    route = api.get("/usage").respond(200, json=usage_json())
    with CheckAnySite(api_key=API_KEY, base_url=BASE_URL, timeout=httpx.Timeout(5.0)) as client:
        client.usage.retrieve()
    assert route.calls.last.request.extensions["timeout"] == httpx.Timeout(5.0).as_dict()


def test_an_http_client_passed_in_is_used_and_left_open(api: respx.MockRouter) -> None:
    api.get("/usage").respond(200, json=usage_json())
    http_client = httpx.Client()
    with CheckAnySite(api_key=API_KEY, base_url=BASE_URL, http_client=http_client) as client:
        client.usage.retrieve()
    assert not http_client.is_closed
    http_client.close()


def test_its_own_http_client_is_closed_with_it() -> None:
    client = CheckAnySite(api_key=API_KEY)
    client.close()
    assert client._http.is_closed


def test_its_own_http_client_closes_when_collected_unclosed() -> None:
    http = CheckAnySite(api_key=API_KEY)._http
    assert isinstance(http, _OwnedClient)
    http.__del__()  # what the garbage collector runs for a client never closed
    assert http.is_closed
    http.__del__()  # already closed: nothing more to do


def test_an_http_client_passed_in_is_never_closed_when_collected() -> None:
    http_client = httpx.Client()
    assert type(CheckAnySite(api_key=API_KEY, http_client=http_client)._http) is httpx.Client
    http_client.close()


async def test_the_async_client_closes_its_own_http_client_when_collected() -> None:
    http = AsyncCheckAnySite(api_key=API_KEY)._http
    assert isinstance(http, _OwnedAsyncClient)
    http.__del__()  # schedules the close on the running loop
    await asyncio.sleep(0)
    assert http.is_closed
    http.__del__()


async def test_the_async_client_collected_without_a_loop_leaves_it_be() -> None:
    http = AsyncCheckAnySite(api_key=API_KEY)._http
    assert isinstance(http, _OwnedAsyncClient)
    # Collected on a thread with no event loop: nothing to close it on, and no error.
    collector = threading.Thread(target=http.__del__)
    collector.start()
    collector.join()
    assert not http.is_closed
    await http.aclose()


async def test_the_async_client_closes_its_own_http_client() -> None:
    async with AsyncCheckAnySite(api_key=API_KEY) as client:
        assert not client._http.is_closed
    assert client._http.is_closed


async def test_the_async_client_leaves_an_http_client_passed_in_open() -> None:
    http_client = httpx.AsyncClient()
    async with AsyncCheckAnySite(api_key=API_KEY, http_client=http_client):
        pass
    assert not http_client.is_closed
    await http_client.aclose()
