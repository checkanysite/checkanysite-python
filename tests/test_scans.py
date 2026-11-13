"""`client.scans`: starting scans, reading them, batches, and waiting for one to be complete."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from support import SCAN_ID, FakeClock, scan_json, usage_json

from checkanysite import CheckAnySite, ScanTimeoutError
from checkanysite.models import Scan, ScanBatch, ScanBatchFailure, Usage

POLL_HEADERS = {"Retry-After": "3", "X-Request-Id": "req_poll"}


def test_create_sends_the_domain_and_checks_and_reads_a_queued_scan(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.post("/scans").respond(
        202,
        json=scan_json("queued"),
        headers={"Location": f"https://checkanysite.com/api/v1/scans/{SCAN_ID}", **POLL_HEADERS},
    )
    scan = client.scans.create("example.com", checks=["readiness"])

    assert json.loads(route.calls.last.request.content) == {
        "domain": "example.com",
        "checks": ["readiness"],
    }
    assert isinstance(scan, Scan)
    assert scan.id == SCAN_ID
    assert scan.status == "queued"
    assert scan.complete is False
    assert scan.result is None
    assert scan.links.self == f"https://checkanysite.com/api/v1/scans/{SCAN_ID}?checks=ai"
    assert scan.meta.status_code == 202
    assert scan.meta.retry_after_seconds == 3.0


def test_create_asks_again_only_when_told(client: CheckAnySite, api: respx.MockRouter) -> None:
    route = api.post("/scans").respond(200, json=scan_json("completed"))
    scan = client.scans.create("example.com", checks=["readiness"], again=True)
    assert json.loads(route.calls.last.request.content)["again"] is True
    # A result from the last day answers at once: 200, complete, with its result.
    assert scan.meta.status_code == 200
    assert scan.complete is True
    assert scan.result is not None
    assert scan.result.domain == "example.com"


def test_retrieve_reads_a_scan_with_the_checks_asked(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.get(f"/scans/{SCAN_ID}").respond(200, json=scan_json("running"))
    scan = client.scans.retrieve(SCAN_ID, checks=["ai"])
    assert route.calls.last.request.url.params["checks"] == "ai"
    assert scan.status == "running"


def test_retrieve_without_checks_sends_no_query(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.get(f"/scans/{SCAN_ID}").respond(200, json=scan_json("running"))
    client.scans.retrieve(SCAN_ID)
    assert route.calls.last.request.url.query == b""


def test_batch_reads_scans_and_failures_apart(client: CheckAnySite, api: respx.MockRouter) -> None:
    route = api.post("/scans/batch").respond(
        202,
        json={
            "data": [
                scan_json("queued", domain="a.example"),
                {
                    "input": "localhost",
                    "domain": None,
                    "error": {"code": "invalid_domain", "message": "Not a public domain."},
                },
            ]
        },
    )
    batch = client.scans.batch(["a.example", "localhost"], checks=["ai"])

    assert json.loads(route.calls.last.request.content) == {
        "domains": ["a.example", "localhost"],
        "checks": ["ai"],
    }
    assert isinstance(batch, ScanBatch)
    assert batch.meta.status_code == 202
    scan, failure = batch.data
    assert isinstance(scan, Scan)
    assert scan.domain == "a.example"
    assert isinstance(failure, ScanBatchFailure)
    assert failure.error.code == "invalid_domain"
    assert failure.domain is None


def test_create_and_wait_polls_as_often_as_retry_after_asks(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.post("/scans").respond(202, json=scan_json("queued"), headers=POLL_HEADERS)
    poll = api.get(f"/scans/{SCAN_ID}").mock(
        side_effect=[
            httpx.Response(200, json=scan_json("running"), headers={"Retry-After": "5"}),
            # Completed, but a slow source is still being read: not complete yet.
            httpx.Response(200, json=scan_json("completed", complete=False), headers=POLL_HEADERS),
            httpx.Response(200, json=scan_json("completed"), headers={"X-Request-Id": "req_done"}),
        ]
    )
    scan = client.scans.create_and_wait("example.com", checks=["ai"], timeout=120)

    assert scan.complete is True
    assert scan.result is not None
    assert scan.meta.request_id == "req_done"
    assert clock.sleeps == [3.0, 5.0, 3.0]
    assert poll.call_count == 3
    # Every poll names the checks asked, so the result holds just those.
    assert all(call.request.url.params["checks"] == "ai" for call in poll.calls)


def test_create_and_wait_returns_at_once_when_a_recent_result_answers(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.post("/scans").respond(200, json=scan_json("completed"))
    scan = client.scans.create_and_wait("example.com")
    assert scan.complete is True
    assert clock.sleeps == []


def test_create_and_wait_returns_a_failed_scan(client: CheckAnySite, api: respx.MockRouter) -> None:
    api.post("/scans").respond(202, json=scan_json("queued"), headers=POLL_HEADERS)
    api.get(f"/scans/{SCAN_ID}").respond(
        200,
        json=scan_json("failed", failure={"code": "unreachable", "message": "No answer."}),
    )
    scan = client.scans.create_and_wait("example.com")
    assert scan.status == "failed"
    assert scan.failure is not None
    assert scan.failure.code == "unreachable"


def test_create_and_wait_polls_every_3_seconds_without_retry_after_and_never_faster_than_1(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.post("/scans").respond(202, json=scan_json("queued"))
    api.get(f"/scans/{SCAN_ID}").mock(
        side_effect=[
            httpx.Response(200, json=scan_json("running"), headers={"Retry-After": "0"}),
            httpx.Response(200, json=scan_json("completed")),
        ]
    )
    client.scans.create_and_wait("example.com")
    assert clock.sleeps == [3.0, 1.0]


def test_create_and_wait_gives_up_at_its_timeout_naming_the_scan(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.post("/scans").respond(202, json=scan_json("queued"), headers=POLL_HEADERS)
    api.get(f"/scans/{SCAN_ID}").respond(200, json=scan_json("running"), headers=POLL_HEADERS)

    with pytest.raises(ScanTimeoutError) as caught:
        client.scans.create_and_wait("example.com", timeout=10)

    # Polls at 3, 6 and 9 seconds, a last one at the timeout, then the error.
    assert clock.sleeps == [3.0, 3.0, 3.0, 1.0]
    error = caught.value
    assert error.scan_id == SCAN_ID
    assert SCAN_ID in str(error)
    assert error.scan.status == "running"
    assert error.timeout_seconds == 10
    assert error.request_id == "req_poll"
    assert isinstance(error, TimeoutError)


def test_usage_retrieve_reads_the_months_credits(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    api.get("/usage").respond(200, json=usage_json(), headers={"X-Request-Id": "req_usage"})
    usage = client.usage.retrieve()
    assert isinstance(usage, Usage)
    assert usage.remaining == 32
    assert usage.key.monthly_credit_limit == 20
    assert usage.prices.checks["ai"].scan == 5
    assert usage.prices.all_checks.stored == 4
    assert usage.rate_limit.period_seconds == 60
    assert usage.meta.request_id == "req_usage"


def test_wait_polls_a_scan_already_started_until_it_is_complete(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.post("/scans").respond(202, json=scan_json("queued"), headers=POLL_HEADERS)
    api.get(f"/scans/{SCAN_ID}").mock(
        side_effect=[
            httpx.Response(200, json=scan_json("running"), headers=POLL_HEADERS),
            httpx.Response(200, json=scan_json("completed")),
        ]
    )
    started = client.scans.create("example.com", checks=["ai"])
    scan = client.scans.wait(started)  # polls with the scan's own checks

    assert scan.complete is True
    assert clock.sleeps == [3.0, 3.0]
    assert api.calls.last.request.url.params["checks"] == "ai"


def test_wait_takes_a_scan_id_and_reads_the_scan_first(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    poll = api.get(f"/scans/{SCAN_ID}").mock(
        side_effect=[
            httpx.Response(200, json=scan_json("running"), headers=POLL_HEADERS),
            httpx.Response(200, json=scan_json("completed")),
        ]
    )
    scan = client.scans.wait(SCAN_ID, timeout=30)

    assert scan.complete is True
    assert poll.call_count == 2
    assert clock.sleeps == [3.0]


def test_wait_gives_up_at_its_timeout(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.get(f"/scans/{SCAN_ID}").respond(200, json=scan_json("running"), headers=POLL_HEADERS)
    with pytest.raises(ScanTimeoutError) as caught:
        client.scans.wait(SCAN_ID, timeout=5)
    assert caught.value.scan_id == SCAN_ID


def test_batch_and_wait_waits_for_every_scan_and_keeps_failures_in_place(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    second = "1c6b8b8f-2f8f-4e8d-8b5f-3f1e9c2d7a22"
    api.post("/scans/batch").respond(
        202,
        json={
            "data": [
                scan_json("queued", domain="example.org"),
                {
                    "input": "localhost",
                    "domain": None,
                    "error": {"code": "invalid_domain", "message": "Not a public domain."},
                },
                scan_json("completed", scan_id=second, domain="example.net"),
            ]
        },
        headers={"X-Request-Id": "req_batch", "X-Credits-Cost": "6", "Retry-After": "3"},
    )
    api.get(f"/scans/{SCAN_ID}").mock(
        side_effect=[
            httpx.Response(
                200, json=scan_json("running", domain="example.org"), headers=POLL_HEADERS
            ),
            httpx.Response(200, json=scan_json("completed", domain="example.org")),
        ]
    )
    batch = client.scans.batch_and_wait(["example.org", "localhost", "example.net"], checks=["ai"])

    first, failure, third = batch.data
    assert isinstance(first, Scan) and first.complete and first.domain == "example.org"
    assert isinstance(failure, ScanBatchFailure) and failure.error.code == "invalid_domain"
    assert isinstance(third, Scan) and third.complete and third.domain == "example.net"
    # What the batch cost stays with it.
    assert batch.meta.request_id == "req_batch"
    assert batch.meta.credits_cost == 6
    assert clock.sleeps == [3.0, 3.0]
