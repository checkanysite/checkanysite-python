"""Every error this library raises, all under `APIError`.

What: one class per kind of failure, and `error_from_response`, which turns an API error answer
(`{"error": {"code", "message", "param"?, "docs", "requestId"}}`) into the class for its status.
Why by status: the API may add error codes within v1 (ADR 0102), so the class comes from the
HTTP status and the code is read as a string; a code this version doesn't know still lands in
the right class.

    APIError
    ├── APIStatusError            the API answered with an error status
    │   ├── BadRequestError           400
    │   ├── AuthenticationError       401
    │   ├── PermissionDeniedError     403
    │   ├── NotFoundError             404
    │   ├── ConflictError             409
    │   ├── UnprocessableEntityError  422
    │   ├── RateLimitError            429
    │   └── InternalServerError       500 and above
    ├── APIConnectionError        no answer: the network or the connection failed
    │   └── APITimeoutError           no answer in time
    └── ScanTimeoutError          scans.create_and_wait gave up waiting
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import httpx

from .models.meta import parse_retry_after

if TYPE_CHECKING:
    from .models import Scan


class APIError(Exception):
    """The base of every error this library raises.

    Attributes:
        message: what happened, in a sentence.
        code: the API's stable error code (`rate_limited`, `no_result`, …), when it gave one.
        param: the parameter at fault, for `invalid_parameter`.
        request_id: the request's id; quote it when you write to us.
        status_code: the HTTP status, when the API answered.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        param: Optional[str] = None,
        request_id: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.param = param
        self.request_id = request_id
        self.status_code = status_code

    def __str__(self) -> str:
        parts = [str(self.status_code)] if self.status_code is not None else []
        if self.code:
            parts.append(self.code)
        prefix = f"{' '.join(parts)}: " if parts else ""
        suffix = f" (request {self.request_id})" if self.request_id else ""
        return f"{prefix}{self.message}{suffix}"


class APIStatusError(APIError):
    """The API answered with an error status (4xx or 5xx).

    Attributes, besides those of `APIError`:
        status_code: the HTTP status.
        docs: the code's entry on the errors page.
        retry_after_seconds: the wait the Retry-After header asked for, if any.
        response: the raw `httpx.Response`.
        body: the answer's JSON (or text, when it isn't JSON).
    """

    status_code: int

    def __init__(
        self,
        message: str,
        *,
        response: httpx.Response,
        body: object,
        code: Optional[str] = None,
        param: Optional[str] = None,
        request_id: Optional[str] = None,
        docs: Optional[str] = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            param=param,
            request_id=request_id,
            status_code=response.status_code,
        )
        self.response = response
        self.body = body
        self.docs = docs
        self.retry_after_seconds = parse_retry_after(response.headers.get("retry-after"))


class BadRequestError(APIStatusError):
    """400: invalid JSON, an invalid or unknown parameter, or not a public domain."""


class AuthenticationError(APIStatusError):
    """401: the API key is missing, unknown, revoked or expired."""


class PermissionDeniedError(APIStatusError):
    """403: the key may not do this (`read_only_key`), or the call came from a browser."""


class NotFoundError(APIStatusError):
    """404: no stored result (`no_result`), no such scan, or no such endpoint."""


class ConflictError(APIStatusError):
    """409: a request with the same Idempotency-Key is still running (retried automatically)."""


class UnprocessableEntityError(APIStatusError):
    """422: a site we don't check, or an Idempotency-Key reused with a different body."""


class RateLimitError(APIStatusError):
    """429: too many requests (`rate_limited`, retried automatically), or a limit used up.

    `quota_exceeded` and `key_limit_reached` mean the month's credits are spent, and
    `scan_limit_reached` that the account started its new scans for the day: they are never
    retried, since asking again can't succeed before the reset.
    """


class InternalServerError(APIStatusError):
    """500 and above: an error on our side, or no capacity for new scans (retried automatically)."""


class APIConnectionError(APIError):
    """No answer: the connection failed, was refused or broke off."""

    def __init__(self, message: str = "Could not reach the CheckAnySite API.") -> None:
        super().__init__(message)


class APITimeoutError(APIConnectionError):
    """No answer within the request timeout (30 seconds unless set on the client)."""

    def __init__(self, message: str = "The CheckAnySite API didn't answer in time.") -> None:
        super().__init__(message)


class ScanTimeoutError(APIError, TimeoutError):
    """`scans.create_and_wait` reached its timeout before the scan was complete.

    The scan goes on: read it later with `scans.retrieve(error.scan_id)`.

    Attributes:
        scan_id: the scan's id.
        scan: the scan as last read, with whatever result it had by then.
        timeout_seconds: the timeout that was reached.
    """

    def __init__(self, scan: Scan, timeout_seconds: float) -> None:
        super().__init__(
            f"Scan {scan.id} of {scan.domain} wasn't complete after {timeout_seconds:g} seconds "
            f"(status {scan.status}); it goes on, so read it later with "
            f"scans.retrieve({scan.id!r}).",
            request_id=scan.meta.request_id,
        )
        self.scan_id = scan.id
        self.scan = scan
        self.timeout_seconds = timeout_seconds


_ERROR_CLASS_BY_STATUS: dict[int, type[APIStatusError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def error_class_for_status(status_code: int) -> type[APIStatusError]:
    """The error class for an HTTP status: its own, InternalServerError for 5xx, else the base."""
    if status_code >= 500:
        return InternalServerError
    return _ERROR_CLASS_BY_STATUS.get(status_code, APIStatusError)


def error_from_response(response: httpx.Response) -> APIStatusError:
    """The error an error answer stands for, read from its body (when it is the API's JSON).

    An answer that isn't the API's error shape (a proxy's HTML page, an empty body) still gives
    the class for its status, with a message naming the status.
    """
    body: object
    try:
        body = response.json()
    except ValueError:
        body = response.text or None
    details = body.get("error") if isinstance(body, dict) else None
    error = details if isinstance(details, dict) else {}

    def text(name: str) -> Optional[str]:
        value = error.get(name)
        return value if isinstance(value, str) and value else None

    message = text("message") or f"HTTP {response.status_code} {response.reason_phrase}".strip()
    return error_class_for_status(response.status_code)(
        message,
        response=response,
        body=body,
        code=text("code"),
        param=text("param"),
        request_id=text("requestId") or response.headers.get("x-request-id"),
        docs=text("docs"),
    )
