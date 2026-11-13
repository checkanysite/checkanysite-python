"""Sending a request to the API: authentication, idempotency keys, retries and typed answers.

What: `SyncAPIClient` and `AsyncAPIClient`, the transport the clients in _client.py build on.
Each call is one `httpx.Request` (with one Idempotency-Key for a POST), sent until it succeeds,
fails in a way that won't pass (_retries.py), or runs out of retries; a success is parsed into
its model with the answer's headers as `.meta`, an error answer into the class for its status.
Why one request object for every try: a retried POST must carry the same Idempotency-Key, so the
API replays the first answer instead of doing (and charging for) the work twice.
Not here: the endpoints (resources/) or the retry rules (_retries.py).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
import uuid
from collections.abc import Awaitable, Mapping
from typing import Callable, Optional, TypeVar, Union

import httpx

from ._constants import API_KEY_ENV, BASE_URL_ENV, DEFAULT_BASE_URL, USER_AGENT
from ._retries import is_retryable_status, retry_delay_seconds
from .errors import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    error_from_response,
)
from .models import ResponseMeta, ResponseModel

ResponseT = TypeVar("ResponseT", bound=ResponseModel)

Timeout = Union[float, httpx.Timeout]
"""Seconds for each of connecting, sending and reading, or an `httpx.Timeout` for each apart."""

RequestFailure = Union[APIStatusError, APIConnectionError]
"""How one try can fail: an error answer, or no answer."""

QueryParams = Mapping[str, Union[str, int]]
JsonBody = Mapping[str, object]


class _BaseClient:
    """What the sync and async clients share: their settings, how a request is built and read."""

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: Timeout,
        max_retries: int,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        if not key:
            raise APIError(
                f"No API key: pass api_key=... or set {API_KEY_ENV}. "
                "Get one free at https://checkanysite.com/account/keys."
            )
        if max_retries < 0:
            raise ValueError("max_retries must be 0 or more.")
        self.api_key = key
        self.base_url = (base_url or os.environ.get(BASE_URL_ENV) or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _build_request(
        self,
        http: Union[httpx.Client, httpx.AsyncClient],
        method: str,
        path: str,
        params: Optional[QueryParams],
        body: Optional[JsonBody],
        idempotency_key: Optional[str],
    ) -> httpx.Request:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if method == "POST":
            # One key per call, reused by its retries, so a retried POST is never done twice.
            headers["Idempotency-Key"] = idempotency_key or str(uuid.uuid4())
        return http.build_request(
            method,
            f"{self.base_url}{path}",
            params=dict(params) if params else None,
            json=dict(body) if body is not None else None,
            headers=headers,
            timeout=self.timeout,
        )

    def _retry_delay(self, retries_done: int, error: RequestFailure) -> Optional[float]:
        """The wait before trying again after this error, or None to raise it now."""
        if retries_done >= self.max_retries:
            return None
        if isinstance(error, APIStatusError):
            if not is_retryable_status(error.status_code, error.code):
                return None
            return retry_delay_seconds(retries_done, error.retry_after_seconds)
        # No answer at all (a connection error or a timeout): always worth another try.
        return retry_delay_seconds(retries_done, None)


class _OwnedClient(httpx.Client):
    """The `httpx.Client` a client makes for itself, closed when it is garbage collected.

    Why: a client used without `with` or `close()`, as a script's one client often is, would keep
    its pooled connections open until the interpreter exits, and Python warns about each one
    (ResourceWarning: unclosed socket).
    """

    def __del__(self) -> None:
        if self.is_closed:
            return
        # Nothing can be reported from a finalizer, so a failure to close is let pass.
        with contextlib.suppress(Exception):
            self.close()


class _OwnedAsyncClient(httpx.AsyncClient):
    """The `httpx.AsyncClient` an async client makes for itself, closed when it is collected
    while its event loop still runs (`async with` closes it for sure)."""

    def __del__(self) -> None:
        if self.is_closed:
            return
        # Without a running loop (RuntimeError) there is nothing to close it on.
        with contextlib.suppress(Exception):
            asyncio.get_running_loop().create_task(self.aclose())


def _connection_error(exception: httpx.RequestError) -> APIConnectionError:
    error = (
        APITimeoutError()
        if isinstance(exception, httpx.TimeoutException)
        else APIConnectionError(f"Could not reach the CheckAnySite API: {exception}")
    )
    error.__cause__ = exception
    return error


def _parse(response: httpx.Response, cast_to: type[ResponseT]) -> ResponseT:
    """The successful answer as its model, carrying the answer's headers as `.meta`."""
    try:
        data = response.json()
    except ValueError as exception:
        raise APIError(
            f"The API answered {response.status_code} without a JSON body.",
            status_code=response.status_code,
            request_id=response.headers.get("x-request-id"),
        ) from exception
    model = cast_to.model_validate(data)
    model._meta = ResponseMeta.from_headers(response.status_code, response.headers)
    return model


class SyncAPIClient(_BaseClient):
    """Sends requests with `httpx.Client`, waiting between retries with `time.sleep`."""

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: Timeout,
        max_retries: int,
        http_client: Optional[httpx.Client],
    ) -> None:
        super().__init__(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries
        )
        self._owns_http_client = http_client is None
        self._http = http_client if http_client is not None else _OwnedClient()
        # The clock and the wait, as attributes so tests can stand in for them.
        self._sleep: Callable[[float], None] = time.sleep
        self._clock: Callable[[], float] = time.monotonic

    def _request(
        self,
        method: str,
        path: str,
        *,
        cast_to: type[ResponseT],
        params: Optional[QueryParams] = None,
        body: Optional[JsonBody] = None,
        idempotency_key: Optional[str] = None,
    ) -> ResponseT:
        request = self._build_request(self._http, method, path, params, body, idempotency_key)
        retries_done = 0
        while True:
            error: RequestFailure
            try:
                response = self._http.send(request)
            except httpx.RequestError as exception:
                error = _connection_error(exception)
            else:
                if response.is_success:
                    return _parse(response, cast_to)
                error = error_from_response(response)
            delay = self._retry_delay(retries_done, error)
            if delay is None:
                raise error
            self._sleep(delay)
            retries_done += 1

    def close(self) -> None:
        """Close the connections, unless the `http_client` was passed in (its owner closes it)."""
        if self._owns_http_client:
            self._http.close()


class AsyncAPIClient(_BaseClient):
    """Sends requests with `httpx.AsyncClient`, waiting between retries with `asyncio.sleep`."""

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: Timeout,
        max_retries: int,
        http_client: Optional[httpx.AsyncClient],
    ) -> None:
        super().__init__(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries
        )
        self._owns_http_client = http_client is None
        self._http = http_client if http_client is not None else _OwnedAsyncClient()
        self._sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
        self._clock: Callable[[], float] = time.monotonic

    async def _request(
        self,
        method: str,
        path: str,
        *,
        cast_to: type[ResponseT],
        params: Optional[QueryParams] = None,
        body: Optional[JsonBody] = None,
        idempotency_key: Optional[str] = None,
    ) -> ResponseT:
        request = self._build_request(self._http, method, path, params, body, idempotency_key)
        retries_done = 0
        while True:
            error: RequestFailure
            try:
                response = await self._http.send(request)
            except httpx.RequestError as exception:
                error = _connection_error(exception)
            else:
                if response.is_success:
                    return _parse(response, cast_to)
                error = error_from_response(response)
            delay = self._retry_delay(retries_done, error)
            if delay is None:
                raise error
            await self._sleep(delay)
            retries_done += 1

    async def close(self) -> None:
        """Close the connections, unless the `http_client` was passed in (its owner closes it)."""
        if self._owns_http_client:
            await self._http.aclose()
