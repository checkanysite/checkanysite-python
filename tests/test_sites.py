"""`client.sites`: reading stored results, one site or a batch."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import respx
from support import site_result_json

from checkanysite import CheckAnySite, NotFoundError
from checkanysite.models import SiteBatch, SiteResult

CHARGED_HEADERS = {
    "X-Request-Id": "req_123",
    "X-Credits-Cost": "2",
    "X-Credits-Remaining": "48",
    "X-Credits-Reset": "2026-12-01T00:00:00.000Z",
    "X-RateLimit-Limit": "60",
    "X-RateLimit-Remaining": "59",
    "X-RateLimit-Reset": "1794398460",
    "ETag": '"abc"',
}


def test_retrieve_asks_for_the_checks_and_age_and_reads_the_result(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.get("/sites/stripe.com").respond(
        200, json=site_result_json("stripe.com", ("ai", "tech")), headers=CHARGED_HEADERS
    )
    site = client.sites.retrieve("stripe.com", checks=["ai", "tech"], max_age_days=30)

    request = route.calls.last.request
    assert request.url.params["checks"] == "ai,tech"
    assert request.url.params["maxAgeDays"] == "30"
    assert isinstance(site, SiteResult)
    assert site.domain == "stripe.com"
    assert site.checks == ["ai", "tech"]
    assert site.scanned_at == datetime(2026, 11, 10, 9, 30, 6, tzinfo=timezone.utc)
    assert site.ai is not None
    assert site.ai.level == "none"
    assert site.tech is None


def test_retrieve_carries_the_answers_headers_as_meta(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    api.get("/sites/stripe.com").respond(200, json=site_result_json(), headers=CHARGED_HEADERS)
    meta = client.sites.retrieve("stripe.com").meta
    assert meta.status_code == 200
    assert meta.request_id == "req_123"
    assert meta.credits_cost == 2
    assert meta.credits_remaining == 48
    assert meta.credits_reset == datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert meta.rate_limit_limit == 60
    assert meta.rate_limit_remaining == 59
    assert meta.rate_limit_reset == datetime(2026, 11, 11, 12, 1, tzinfo=timezone.utc)
    assert meta.etag == '"abc"'
    assert meta.idempotent_replayed is False
    assert meta.headers["x-credits-cost"] == "2"


def test_retrieve_without_options_asks_every_check(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.get("/sites/stripe.com").respond(200, json=site_result_json())
    client.sites.retrieve("stripe.com")
    assert dict(route.calls.last.request.url.params) == {}


def test_retrieve_takes_one_check_as_a_string(client: CheckAnySite, api: respx.MockRouter) -> None:
    route = api.get("/sites/stripe.com").respond(200, json=site_result_json())
    client.sites.retrieve("stripe.com", checks="dns")
    assert route.calls.last.request.url.params["checks"] == "dns"


def test_retrieve_escapes_the_domain_as_one_path_segment(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.get(url__regex=r".*/sites/[^/]+$").respond(200, json=site_result_json())
    client.sites.retrieve("https://stripe.com/pricing?x=1")
    assert route.calls.last.request.url.raw_path == (
        b"/v1/sites/https%3A%2F%2Fstripe.com%2Fpricing%3Fx%3D1"
    )


def test_retrieve_refuses_an_empty_domain(client: CheckAnySite) -> None:
    with pytest.raises(ValueError, match="domain"):
        client.sites.retrieve("")


def test_a_missing_result_raises_not_found_with_its_code(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    api.get("/sites/unknown.example").respond(
        404,
        json={
            "error": {
                "code": "no_result",
                "message": "We have no result for this site.",
                "docs": "https://checkanysite.com/developers/docs/errors#no_result",
                "requestId": "req_404",
            }
        },
    )
    with pytest.raises(NotFoundError) as caught:
        client.sites.retrieve("unknown.example")
    assert caught.value.code == "no_result"
    assert caught.value.status_code == 404
    assert caught.value.request_id == "req_404"


def test_batch_sends_the_domains_and_reads_results_and_errors(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.post("/sites/batch").respond(
        200,
        json={
            "data": [
                {"input": "stripe.com", "domain": "stripe.com", "result": site_result_json()},
                {
                    "input": "https://lovable.dev/",
                    "domain": "lovable.dev",
                    "error": {"code": "no_result", "message": "No stored result."},
                },
                {
                    "input": "not a domain",
                    "domain": None,
                    "error": {"code": "invalid_domain", "message": "Not a public domain."},
                },
            ]
        },
        headers={"X-Credits-Cost": "1"},
    )
    batch = client.sites.batch(
        ["stripe.com", "https://lovable.dev/", "not a domain"], checks=["ai"], max_age_days=7
    )

    request = route.calls.last.request
    assert json.loads(request.content) == {
        "domains": ["stripe.com", "https://lovable.dev/", "not a domain"],
        "checks": ["ai"],
        "maxAgeDays": 7,
    }
    assert request.headers["content-type"] == "application/json"
    assert isinstance(batch, SiteBatch)
    assert batch.meta.credits_cost == 1
    found, missing, invalid = batch.data
    assert found.result is not None
    assert found.result.domain == "stripe.com"
    assert found.error is None
    assert missing.result is None
    assert missing.error is not None
    assert missing.error.code == "no_result"
    assert invalid.domain is None
    assert invalid.input == "not a domain"


def test_batch_sends_only_the_domains_when_nothing_else_is_asked(
    client: CheckAnySite, api: respx.MockRouter
) -> None:
    route = api.post("/sites/batch").respond(200, json={"data": []})
    client.sites.batch(("a.example", "b.example"))
    assert json.loads(route.calls.last.request.content) == {"domains": ["a.example", "b.example"]}
