"""The async client mirrors the sync one: the same methods, retries, meta and waiting."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from support import SCAN_ID, FakeClock, error_json, scan_json, site_result_json, usage_json

from checkanysite import (
    APIConnectionError,
    AsyncCheckAnySite,
    NotFoundError,
    RateLimitError,
    ScanTimeoutError,
)
from checkanysite.models import Scan, ScanBatchFailure

POLL_HEADERS = {"Retry-After": "3"}


async def test_sites_retrieve_and_batch(
    async_client: AsyncCheckAnySite, api: respx.MockRouter
) -> None:
    one = api.get("/sites/stripe.com").respond(
        200, json=site_result_json(), headers={"X-Credits-Remaining": "41"}
    )
    many = api.post("/sites/batch").respond(
        200,
        json={
            "data": [{"input": "stripe.com", "domain": "stripe.com", "result": site_result_json()}]
        },
    )
    site = await async_client.sites.retrieve("stripe.com", checks=["ai"], max_age_days=30)
    batch = await async_client.sites.batch(["stripe.com"], checks=["ai"], max_age_days=30)

    assert one.calls.last.request.url.params["maxAgeDays"] == "30"
    assert site.meta.credits_remaining == 41
    assert json.loads(many.calls.last.request.content) == {
        "domains": ["stripe.com"],
        "checks": ["ai"],
        "maxAgeDays": 30,
    }
    assert batch.data[0].result is not None


async def test_scans_create_retrieve_and_batch(
    async_client: AsyncCheckAnySite, api: respx.MockRouter
) -> None:
    created = api.post("/scans").respond(202, json=scan_json("queued"), headers=POLL_HEADERS)
    api.get(f"/scans/{SCAN_ID}").respond(200, json=scan_json("running"))
    api.post("/scans/batch").respond(
        202,
        json={
            "data": [
                scan_json("queued"),
                {"input": "x", "domain": None, "error": {"code": "invalid_domain", "message": "m"}},
            ]
        },
    )
    scan = await async_client.scans.create("example.com", checks=["readiness"], again=True)
    polled = await async_client.scans.retrieve(scan.id, checks=["readiness"])
    batch = await async_client.scans.batch(["example.com", "x"])

    assert json.loads(created.calls.last.request.content) == {
        "domain": "example.com",
        "checks": ["readiness"],
        "again": True,
    }
    assert "idempotency-key" in created.calls.last.request.headers
    assert scan.meta.status_code == 202
    assert polled.status == "running"
    assert isinstance(batch.data[0], Scan)
    assert isinstance(batch.data[1], ScanBatchFailure)


async def test_usage_retrieve(async_client: AsyncCheckAnySite, api: respx.MockRouter) -> None:
    api.get("/usage").respond(200, json=usage_json())
    usage = await async_client.usage.retrieve()
    assert usage.allowance == 50


async def test_errors_and_retries_honouring_retry_after(
    async_client: AsyncCheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    route = api.post("/scans").mock(
        side_effect=[
            httpx.Response(429, json=error_json("rate_limited"), headers={"Retry-After": "4"}),
            httpx.ConnectError("refused"),
            httpx.Response(202, json=scan_json("queued")),
        ]
    )
    await async_client.scans.create("example.com")
    assert route.call_count == 3
    assert clock.sleeps[0] == 4.0
    assert len({call.request.headers["idempotency-key"] for call in route.calls}) == 1


async def test_spent_credits_are_not_retried(
    async_client: AsyncCheckAnySite, api: respx.MockRouter
) -> None:
    route = api.get("/sites/stripe.com").respond(429, json=error_json("key_limit_reached"))
    with pytest.raises(RateLimitError):
        await async_client.sites.retrieve("stripe.com")
    assert route.call_count == 1


async def test_not_found_and_connection_errors(
    async_client: AsyncCheckAnySite, api: respx.MockRouter
) -> None:
    api.get(f"/scans/{SCAN_ID}").respond(404, json=error_json("scan_not_found"))
    api.get("/usage").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(NotFoundError):
        await async_client.scans.retrieve(SCAN_ID)
    with pytest.raises(APIConnectionError):
        await async_client.usage.retrieve()


async def test_create_and_wait_polls_until_complete(
    async_client: AsyncCheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.post("/scans").respond(202, json=scan_json("queued"), headers=POLL_HEADERS)
    api.get(f"/scans/{SCAN_ID}").mock(
        side_effect=[
            httpx.Response(200, json=scan_json("running"), headers={"Retry-After": "2"}),
            httpx.Response(200, json=scan_json("completed")),
        ]
    )
    scan = await async_client.scans.create_and_wait("example.com", checks=["ai"])
    assert scan.complete is True
    assert clock.sleeps == [3.0, 2.0]


async def test_create_and_wait_times_out_naming_the_scan(
    async_client: AsyncCheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.post("/scans").respond(202, json=scan_json("queued"), headers=POLL_HEADERS)
    api.get(f"/scans/{SCAN_ID}").respond(200, json=scan_json("running"), headers=POLL_HEADERS)
    with pytest.raises(ScanTimeoutError) as caught:
        await async_client.scans.create_and_wait("example.com", timeout=5)
    assert caught.value.scan_id == SCAN_ID
    assert clock.sleeps == [3.0, 2.0]


async def test_wait_and_batch_and_wait(
    async_client: AsyncCheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.get(f"/scans/{SCAN_ID}").mock(
        side_effect=[
            httpx.Response(200, json=scan_json("running"), headers=POLL_HEADERS),
            httpx.Response(200, json=scan_json("completed")),
            httpx.Response(200, json=scan_json("completed", domain="example.org")),
        ]
    )
    scan = await async_client.scans.wait(SCAN_ID)
    assert scan.complete is True

    api.post("/scans/batch").respond(
        202,
        json={
            "data": [
                scan_json("queued", domain="example.org"),
                {
                    "input": "localhost",
                    "domain": None,
                    "error": {"code": "invalid_domain", "message": "No."},
                },
            ]
        },
    )
    batch = await async_client.scans.batch_and_wait(["example.org", "localhost"])
    first, failure = batch.data
    assert isinstance(first, Scan) and first.complete
    assert isinstance(failure, ScanBatchFailure)

    api.get(f"/scans/{SCAN_ID}").respond(200, json=scan_json("running"), headers=POLL_HEADERS)
    with pytest.raises(ScanTimeoutError):
        await async_client.scans.wait(SCAN_ID, timeout=1)
