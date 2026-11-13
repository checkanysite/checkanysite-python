"""The models: every field of the OpenAPI document reads, unknown fields are kept, headers parse."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from support import scan_json, site_result_json

from checkanysite import models
from checkanysite.models import ResponseMeta, Scan, ScanBatch, SiteResult
from checkanysite.models.meta import parse_retry_after

OPENAPI = json.loads((Path(__file__).parent.parent / "openapi.json").read_text(encoding="utf-8"))
SCHEMAS: dict[str, Any] = OPENAPI["components"]["schemas"]
# Requests are built by the resources; batch answers are written by hand (models/batch.py), as
# scripts/generate_models.py skips them.
REQUEST_SCHEMAS = {"Error", "ScanRequest", "SiteBatchRequest", "ScanBatchRequest"}
HAND_WRITTEN_SCHEMAS = {"SiteBatch", "ScanBatch", "BatchError"}
ANSWER_SCHEMAS = sorted(set(SCHEMAS) - REQUEST_SCHEMAS - HAND_WRITTEN_SCHEMAS)


def sample(schema: dict[str, Any]) -> Any:
    """A value for the schema with every property filled, to read every field of a model."""
    if "$ref" in schema:
        return sample(SCHEMAS[schema["$ref"].rsplit("/", 1)[-1]])
    if "anyOf" in schema:
        return sample(next(option for option in schema["anyOf"] if option.get("type") != "null"))
    if "enum" in schema:
        return schema["enum"][0]
    kind: str = schema.get("type", "")
    if isinstance(kind, list):  # a nullable scalar: ["string", "null"]
        kind = next(option for option in kind if option != "null")
    if kind == "object":
        if "properties" in schema:
            return {name: sample(inner) for name, inner in schema["properties"].items()}
        key = schema.get("propertyNames", {}).get("enum", ["key"])[0]
        return {key: sample(schema["additionalProperties"])}
    if kind == "array":
        return [sample(schema["items"])]
    if kind == "string":
        return {"date-time": "2026-11-10T09:30:00Z", "uri": "https://example.com/"}.get(
            schema.get("format", ""), "text"
        )
    scalars: dict[str, Any] = {"integer": 7, "number": 1.5, "boolean": True}
    return scalars[kind]


@pytest.mark.parametrize("name", ANSWER_SCHEMAS)
def test_every_field_of_every_answer_schema_reads_and_writes_back(name: str) -> None:
    value = sample(SCHEMAS[name])
    model = getattr(models, name).model_validate(value)
    assert model.model_dump(by_alias=True, mode="json") == value
    # Nothing landed in the extra fields: every documented field has its attribute.
    assert not model.model_extra


@pytest.mark.parametrize("name", sorted(HAND_WRITTEN_SCHEMAS - {"BatchError"}))
def test_the_hand_written_batches_read_the_documented_shape(name: str) -> None:
    # Each documented item shape reads: a found item first, then an error item in its place.
    schema = SCHEMAS[name]
    options = schema["properties"]["data"]["items"]["anyOf"]
    value = {"data": [sample(option) for option in options]}
    batch = getattr(models, name).model_validate(value)
    assert len(batch.data) == len(options)
    assert batch.data[-1].error is not None


def test_attributes_are_snake_case_with_the_apis_names_as_aliases() -> None:
    site = SiteResult.model_validate(site_result_json())
    assert site.scan_id == "0b5a7a6e-1f7e-4d7c-9a4e-2f0d8b1c6a11"
    assert site.final_url == "https://stripe.com/"
    assert "scanId" in site.model_dump(by_alias=True)
    assert "scan_id" in site.model_dump()


def test_unknown_fields_and_values_are_kept_not_refused() -> None:
    payload = site_result_json()
    payload["brandNewSection"] = {"answer": 42}
    payload["checks"] = ["ai", "a-check-added-later"]
    payload["ai"]["level"] = "a-level-added-later"
    payload["ai"]["confidence"] = 0.9
    site = SiteResult.model_validate(payload)
    assert site.model_extra == {"brandNewSection": {"answer": 42}}
    assert site.checks == ["ai", "a-check-added-later"]
    assert site.ai is not None
    assert site.ai.level == "a-level-added-later"
    assert site.ai.model_extra == {"confidence": 0.9}
    assert site.model_dump(by_alias=True)["brandNewSection"] == {"answer": 42}


def test_a_model_made_by_hand_has_an_empty_meta() -> None:
    scan = Scan.model_validate(scan_json("completed"))
    assert scan.meta == ResponseMeta()
    assert scan.result is not None
    assert scan.result.meta.request_id is None


def test_a_scan_batch_tells_scans_from_failures_built_either_way() -> None:
    scan = Scan.model_validate(scan_json("queued"))
    failure = models.ScanBatchFailure(
        input="x", domain=None, error=models.BatchItemError(code="invalid_domain", message="m")
    )
    batch = ScanBatch(data=[scan, failure])
    assert batch.data == [scan, failure]


def test_every_schema_has_a_class_and_no_generated_name_is_numbered() -> None:
    generated = set(models._generated.__all__)
    assert set(ANSWER_SCHEMAS) <= generated
    numbered = [name for name in generated if re.search(r"\d$", name)]
    # A numbered name means two inline shapes clashed: name them in scripts/generate_models.py.
    assert numbered == []


def test_the_answers_a_method_returns_carry_meta() -> None:
    for model in (models.SiteResult, models.Scan, models.Usage, models.SiteBatch, ScanBatch):
        assert issubclass(model, models.ResponseModel)
    assert not issubclass(models.AiTraces, models.ResponseModel)


class TestResponseMeta:
    def test_unreadable_or_missing_headers_are_none(self) -> None:
        meta = ResponseMeta.from_headers(
            200,
            {
                "X-Credits-Cost": "two",
                "X-Credits-Reset": "next month",
                "X-RateLimit-Reset": "soon",
                "Retry-After": "later",
            },
        )
        assert meta.credits_cost is None
        assert meta.credits_reset is None
        assert meta.rate_limit_reset is None
        assert meta.retry_after_seconds is None
        assert meta.request_id is None
        assert meta.idempotent_replayed is False

    def test_header_names_are_read_in_any_case(self) -> None:
        meta = ResponseMeta.from_headers(202, {"x-request-id": "a", "IDEMPOTENT-REPLAYED": "True"})
        assert meta.request_id == "a"
        assert meta.idempotent_replayed is True
        assert meta.status_code == 202


class TestRetryAfter:
    def test_seconds(self) -> None:
        assert parse_retry_after("3") == 3.0
        assert parse_retry_after(" 1.5 ") == 1.5
        assert parse_retry_after("-4") == 0.0
        assert parse_retry_after(None) is None
        assert parse_retry_after("nan") is None
        assert parse_retry_after("inf") is None

    def test_an_http_date(self) -> None:
        now = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)
        assert parse_retry_after("Wed, 11 Nov 2026 12:00:30 GMT", now=now) == 30.0
        assert parse_retry_after("Wed, 11 Nov 2026 11:59:00 GMT", now=now) == 0.0
        # A date without a zone is read as UTC.
        assert parse_retry_after("Wed, 11 Nov 2026 12:00:10 -0000", now=now) == 10.0

    def test_an_http_date_against_the_clock(self) -> None:
        assert parse_retry_after("Thu, 01 Jan 1970 00:00:00 GMT") == 0.0

    def test_garbage(self) -> None:
        assert parse_retry_after("") is None
        assert parse_retry_after("Someday, maybe") is None
