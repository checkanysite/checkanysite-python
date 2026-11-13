"""Retries: what is tried again, after how long, and with one idempotency key across the tries."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest
import respx
from support import API_KEY, BASE_URL, FakeClock, error_json, scan_json, usage_json

from checkanysite import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    BadRequestError,
    CheckAnySite,
    ConflictError,
    InternalServerError,
    RateLimitError,
    UnprocessableEntityError,
)
from checkanysite._retries import is_retryable_status, retry_delay_seconds


def failing(status: int, code: str, retry_after: str = "0") -> httpx.Response:
    return httpx.Response(status, json=error_json(code), headers={"Retry-After": retry_after})


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (409, "idempotency_key_in_use"),
        (429, "rate_limited"),
        (500, "internal_error"),
        (502, "bad_gateway"),
        (503, "capacity"),
        (504, "gateway_timeout"),
    ],
)
def test_retries_failures_that_may_pass(
    client: CheckAnySite, api: respx.MockRouter, status: int, code: str
) -> None:
    route = api.get("/usage").mock(
        side_effect=[failing(status, code), httpx.Response(200, json=usage_json())]
    )
    usage = client.usage.retrieve()
    assert usage.remaining == 32
    assert route.call_count == 2


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (429, "quota_exceeded"),
        (429, "key_limit_reached"),
        (429, "scan_limit_reached"),
        (409, "some_other_conflict"),
        (400, "invalid_parameter"),
        (401, "invalid_api_key"),
        (404, "no_result"),
        (422, "idempotency_key_reused"),
    ],
)
def test_never_retries_failures_that_wont_pass(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock, status: int, code: str
) -> None:
    route = api.get("/usage").mock(return_value=failing(status, code))
    with pytest.raises(APIStatusError) as caught:
        client.usage.retrieve()
    assert caught.value.code == code
    assert route.call_count == 1
    assert clock.sleeps == []


def test_spent_credits_raise_a_rate_limit_error_at_once(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.post("/scans").mock(return_value=failing(429, "quota_exceeded", "3600"))
    with pytest.raises(RateLimitError) as caught:
        client.scans.create("example.com")
    assert caught.value.code == "quota_exceeded"
    assert route.call_count == 1


def test_waits_as_long_as_retry_after_asks(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    api.get("/usage").mock(
        side_effect=[
            failing(429, "rate_limited", "7"),
            failing(503, "capacity", "2.5"),
            httpx.Response(200, json=usage_json()),
        ]
    )
    client.usage.retrieve()
    assert clock.sleeps == [7.0, 2.5]


def test_a_retry_after_longer_than_a_minute_goes_back_to_the_caller(
    client: CheckAnySite, api: respx.MockRouter, clock: FakeClock
) -> None:
    route = api.post("/scans").mock(return_value=failing(503, "capacity", "3600"))
    with pytest.raises(InternalServerError) as caught:
        client.scans.create("example.com")
    assert caught.value.retry_after_seconds == 3600
    assert route.call_count == 1
    assert clock.sleeps == []


def test_backs_off_exponentially_with_jitter_without_retry_after(
    api: respx.MockRouter, clock: FakeClock
) -> None:
    api.get("/usage").mock(return_value=httpx.Response(500, json=error_json("internal_error")))
    client = CheckAnySite(api_key=API_KEY, base_url=BASE_URL, max_retries=3)
    client._sleep = clock.sleep
    with pytest.raises(InternalServerError):
        client.usage.retrieve()
    first, second, third = clock.sleeps
    assert 0.375 <= first <= 0.5
    assert 0.75 <= second <= 1.0
    assert 1.5 <= third <= 2.0


def test_gives_up_after_max_retries(client: CheckAnySite, api: respx.MockRouter) -> None:
    route = api.get("/usage").mock(return_value=failing(500, "internal_error"))
    with pytest.raises(InternalServerError) as caught:
        client.usage.retrieve()
    assert route.call_count == 3  # the first try and two retries
    assert caught.value.request_id == "req_from_body"


def test_max_retries_zero_tries_once(api: respx.MockRouter) -> None:
    route = api.get("/usage").mock(return_value=failing(500, "internal_error"))
    client = CheckAnySite(api_key=API_KEY, base_url=BASE_URL, max_retries=0)
    with pytest.raises(InternalServerError):
        client.usage.retrieve()
    assert route.call_count == 1


def test_retries_connection_errors_then_raises_one(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.get("/usage").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(APIConnectionError) as caught:
        client.usage.retrieve()
    assert route.call_count == 3
    assert not isinstance(caught.value, APITimeoutError)
    assert isinstance(caught.value.__cause__, httpx.ConnectError)
    assert caught.value.status_code is None


def test_retries_timeouts_then_raises_a_timeout_error(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.get("/usage").mock(
        side_effect=[
            httpx.ReadTimeout("slow"),
            httpx.ConnectTimeout("slow"),
            httpx.ReadTimeout("x"),
        ]
    )
    with pytest.raises(APITimeoutError):
        client.usage.retrieve()
    assert route.call_count == 3


def test_recovers_from_a_connection_error(client: CheckAnySite, api: respx.MockRouter) -> None:
    api.get("/usage").mock(
        side_effect=[httpx.RemoteProtocolError("dropped"), httpx.Response(200, json=usage_json())]
    )
    assert client.usage.retrieve().used == 18


def test_a_post_keeps_one_idempotency_key_across_its_retries(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.post("/scans").mock(
        side_effect=[
            httpx.ConnectError("refused"),
            failing(409, "idempotency_key_in_use"),
            httpx.Response(202, json=scan_json("queued")),
        ]
    )
    client.scans.create("example.com")
    keys = {call.request.headers["idempotency-key"] for call in route.calls}
    assert len(keys) == 1
    assert uuid.UUID(keys.pop()).version == 4
    bodies = {call.request.content for call in route.calls}
    assert len(bodies) == 1  # the same body each time, so the API replays the first answer


def test_each_post_gets_a_new_idempotency_key(client: CheckAnySite, api: respx.MockRouter) -> None:
    route = api.post("/scans").respond(202, json=scan_json("queued"))
    client.scans.create("example.com")
    client.scans.create("example.com")
    first, second = (call.request.headers["idempotency-key"] for call in route.calls)
    assert first != second


def test_the_caller_may_give_the_idempotency_key(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    scans = api.post("/scans").respond(202, json=scan_json("queued"))
    scan_batch = api.post("/scans/batch").respond(202, json={"data": []})
    site_batch = api.post("/sites/batch").respond(200, json={"data": []})
    client.scans.create("example.com", idempotency_key="order-42")
    client.scans.batch(["example.com"], idempotency_key="order-43", again=True)
    client.sites.batch(["example.com"], idempotency_key="order-44")
    assert scans.calls.last.request.headers["idempotency-key"] == "order-42"
    assert scan_batch.calls.last.request.headers["idempotency-key"] == "order-43"
    assert json.loads(scan_batch.calls.last.request.content)["again"] is True
    assert site_batch.calls.last.request.headers["idempotency-key"] == "order-44"


def test_a_replayed_answer_says_so(client: CheckAnySite, api: respx.MockRouter) -> None:
    api.post("/scans").respond(
        202, json=scan_json("queued"), headers={"Idempotent-Replayed": "true"}
    )
    assert client.scans.create("example.com", idempotency_key="order-42").meta.idempotent_replayed


def test_a_reused_key_with_another_body_is_not_retried(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    api.post("/scans").mock(return_value=failing(422, "idempotency_key_reused"))
    with pytest.raises(UnprocessableEntityError) as caught:
        client.scans.create("other.example", idempotency_key="order-42")
    assert caught.value.code == "idempotency_key_reused"


def test_a_conflict_still_running_after_the_retries_raises_conflict(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    api.post("/scans").mock(return_value=failing(409, "idempotency_key_in_use"))
    with pytest.raises(ConflictError):
        client.scans.create("example.com")


def test_an_invalid_parameter_names_it(client: CheckAnySite, api: respx.MockRouter) -> None:
    api.get("/sites/stripe.com").respond(
        400, json=error_json("invalid_parameter", "Unknown parameter.", param="checks")
    )
    with pytest.raises(BadRequestError) as caught:
        client.sites.retrieve("stripe.com", checks=["nope"])
    assert caught.value.param == "checks"


class TestRetryRules:
    """The pure rules in _retries.py."""

    def test_retryable_statuses_and_codes(self) -> None:
        assert is_retryable_status(500, None)
        assert is_retryable_status(503, "something_new")
        assert is_retryable_status(429, "rate_limited")
        assert not is_retryable_status(429, None)
        assert not is_retryable_status(429, "quota_exceeded")
        assert is_retryable_status(409, "idempotency_key_in_use")
        assert not is_retryable_status(409, None)
        assert not is_retryable_status(501, None)
        assert not is_retryable_status(404, "no_result")

    def test_delay_takes_retry_after_up_to_a_minute(self) -> None:
        assert retry_delay_seconds(0, 0.0) == 0.0
        assert retry_delay_seconds(5, 60.0) == 60.0
        assert retry_delay_seconds(0, 60.5) is None

    def test_backoff_doubles_up_to_8_seconds_and_jitter_takes_up_to_a_quarter(self) -> None:
        no_jitter = [retry_delay_seconds(n, None, lambda: 0.0) for n in range(6)]
        assert no_jitter == [0.5, 1.0, 2.0, 4.0, 8.0, 8.0]
        assert retry_delay_seconds(0, None, lambda: 0.999) == pytest.approx(0.375, abs=0.001)
