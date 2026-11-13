"""Error answers become the class for their status, carrying the code, message and request id."""

from __future__ import annotations

import httpx
import pytest
import respx
from support import API_KEY, BASE_URL, error_json

import checkanysite
from checkanysite import (
    APIError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    CheckAnySite,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from checkanysite.errors import error_class_for_status, error_from_response

# Every code of the API v1 contract, with its status and the class it becomes.
CONTRACT_CODES = [
    (400, "invalid_json", BadRequestError),
    (400, "invalid_parameter", BadRequestError),
    (400, "invalid_domain", BadRequestError),
    (401, "missing_api_key", AuthenticationError),
    (401, "invalid_api_key", AuthenticationError),
    (401, "revoked_api_key", AuthenticationError),
    (401, "expired_api_key", AuthenticationError),
    (403, "read_only_key", PermissionDeniedError),
    (403, "browser_request", PermissionDeniedError),
    (404, "not_found", NotFoundError),
    (404, "no_result", NotFoundError),
    (404, "scan_not_found", NotFoundError),
    (405, "method_not_allowed", APIStatusError),
    (409, "idempotency_key_in_use", ConflictError),
    (413, "request_too_large", APIStatusError),
    (415, "unsupported_media_type", APIStatusError),
    (422, "site_refused", UnprocessableEntityError),
    (422, "idempotency_key_reused", UnprocessableEntityError),
    (429, "rate_limited", RateLimitError),
    (429, "quota_exceeded", RateLimitError),
    (429, "key_limit_reached", RateLimitError),
    (429, "scan_limit_reached", RateLimitError),
    (500, "internal_error", InternalServerError),
    (503, "capacity", InternalServerError),
]


@pytest.mark.parametrize(("status", "code", "error_class"), CONTRACT_CODES)
def test_each_contract_code_becomes_the_class_for_its_status(
    api: respx.MockRouter, status: int, code: str, error_class: type[APIStatusError]
) -> None:
    api.get("/usage").respond(status, json=error_json(code, "What happened."))
    client = CheckAnySite(api_key=API_KEY, base_url=BASE_URL, max_retries=0)
    with pytest.raises(error_class) as caught:
        client.usage.retrieve()
    error = caught.value
    assert type(error) is error_class
    assert error.status_code == status
    assert error.code == code
    assert error.message == "What happened."
    assert error.request_id == "req_from_body"
    assert error.docs == f"https://checkanysite.com/developers/docs/errors#{code}"
    assert error.response.status_code == status
    assert isinstance(error, APIError)


@pytest.mark.parametrize(
    ("status", "error_class"),
    [
        (400, BadRequestError),
        (403, PermissionDeniedError),
        (418, APIStatusError),
        (429, RateLimitError),
        (501, InternalServerError),
        (599, InternalServerError),
    ],
)
def test_a_code_this_version_doesnt_know_goes_by_its_status(
    status: int, error_class: type[APIStatusError]
) -> None:
    error = error_from_response(httpx.Response(status, json=error_json("brand_new_code")))
    assert type(error) is error_class
    assert error.code == "brand_new_code"


def test_an_answer_that_isnt_the_apis_json_still_gives_its_class() -> None:
    response = httpx.Response(
        502, text="<html>Bad gateway</html>", headers={"X-Request-Id": "req_edge"}
    )
    error = error_from_response(response)
    assert isinstance(error, InternalServerError)
    assert error.code is None
    assert error.message == "HTTP 502 Bad Gateway"
    assert error.request_id == "req_edge"
    assert error.body == "<html>Bad gateway</html>"


@pytest.mark.parametrize("body", [{"message": "not our shape"}, ["a list"], {"error": "text"}])
def test_json_in_another_shape_reads_as_no_details(body: object) -> None:
    error = error_from_response(httpx.Response(400, json=body))
    assert isinstance(error, BadRequestError)
    assert error.code is None
    assert error.message == "HTTP 400 Bad Request"
    assert error.body == body


def test_an_empty_answer_has_no_body() -> None:
    error = error_from_response(httpx.Response(500))
    assert error.body is None
    assert error.message == "HTTP 500 Internal Server Error"


def test_the_message_names_the_status_code_and_request() -> None:
    error = error_from_response(
        httpx.Response(429, json=error_json("rate_limited", "Too many requests."))
    )
    assert str(error) == "429 rate_limited: Too many requests. (request req_from_body)"
    assert str(APIError("Plain.")) == "Plain."


def test_retry_after_is_read_onto_the_error() -> None:
    error = error_from_response(
        httpx.Response(429, json=error_json("rate_limited"), headers={"Retry-After": "12"})
    )
    assert error.retry_after_seconds == 12.0


def test_error_classes_by_status() -> None:
    assert error_class_for_status(401) is AuthenticationError
    assert error_class_for_status(409) is ConflictError
    assert error_class_for_status(500) is InternalServerError
    assert error_class_for_status(302) is APIStatusError


def test_a_success_without_json_is_an_api_error(api: respx.MockRouter) -> None:
    api.get("/usage").respond(200, text="ok", headers={"X-Request-Id": "req_text"})
    client = CheckAnySite(api_key=API_KEY, base_url=BASE_URL)
    with pytest.raises(APIError) as caught:
        client.usage.retrieve()
    assert caught.value.status_code == 200
    assert caught.value.request_id == "req_text"
    assert not isinstance(caught.value, APIStatusError)


def test_every_error_class_is_exported_from_the_package() -> None:
    for name in (
        "APIError",
        "APIStatusError",
        "BadRequestError",
        "AuthenticationError",
        "PermissionDeniedError",
        "NotFoundError",
        "ConflictError",
        "UnprocessableEntityError",
        "RateLimitError",
        "InternalServerError",
        "APIConnectionError",
        "APITimeoutError",
        "ScanTimeoutError",
    ):
        assert issubclass(getattr(checkanysite, name), APIError)
    assert issubclass(checkanysite.APITimeoutError, checkanysite.APIConnectionError)
