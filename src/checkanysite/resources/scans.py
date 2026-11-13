"""`client.scans`: the Scan API, which scans a site live and answers asynchronously.

What: `create` (POST /v1/scans), `retrieve` (GET /v1/scans/{id}, free), `batch`
(POST /v1/scans/batch), and the helpers that poll until a scan is complete, waiting as long as
each answer's Retry-After asks: `wait` for a scan already started, `create_and_wait` and
`batch_and_wait`. Sync and async.
Why poll with the checks asked: the scan's result then holds those checks, as the scan's own
`links.self` does, and the credits paid cover exactly them.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Union

from .._base_client import AsyncAPIClient, SyncAPIClient
from .._constants import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_WAIT_TIMEOUT_SECONDS,
    MIN_POLL_INTERVAL_SECONDS,
)
from ..errors import ScanTimeoutError
from ..models import Scan, ScanBatch, ScanBatchFailure
from ._params import as_list, checks_query, json_body, path_segment, query_params


def _scan_options(checks: Optional[Sequence[str]], again: bool) -> dict[str, object]:
    """The body fields every scan request shares; those left out take the API's defaults."""
    return json_body(
        checks=as_list(checks) if checks is not None else None,
        # Sent only when asked: the API's default is false.
        again=True if again else None,
    )


def _poll_delay_seconds(scan: Scan, remaining_seconds: float) -> float:
    """How long to wait before polling again: the scan's Retry-After, within the time left."""
    asked = scan.meta.retry_after_seconds
    delay = DEFAULT_POLL_INTERVAL_SECONDS if asked is None else asked
    return min(max(delay, MIN_POLL_INTERVAL_SECONDS), remaining_seconds)


def _checks_of(scan: Union[Scan, str], checks: Optional[Sequence[str]]) -> Optional[Sequence[str]]:
    """The checks to poll with: those given, else the scan's own, so its result keeps its shape."""
    if checks is not None or isinstance(scan, str):
        return checks
    return scan.checks or None


def _with_items(batch: ScanBatch, items: Sequence[Union[Scan, ScanBatchFailure]]) -> ScanBatch:
    """The batch with its items replaced (each scan as last read), its `meta` kept."""
    updated = batch.model_copy(update={"data": list(items)})
    updated._meta = batch._meta
    return updated


class ScansResource:
    """Live scans of a site."""

    def __init__(self, client: SyncAPIClient) -> None:
        self._client = client

    def create(
        self,
        domain: str,
        *,
        checks: Optional[Sequence[str]] = None,
        again: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Scan:
        """Scan a site, or join a scan of it already running.

        Args:
            domain: the site, as a domain or a URL.
            checks: the checks to answer, such as `["readiness"]`; every check when left out. A
                scan runs only what they need, so fewer checks are faster and cost less.
            again: with the `readiness` check, ask it again once its answer is a few minutes old,
                to check a fix.
            idempotency_key: a key of your own (1 to 255 characters); one is made otherwise.

        Returns:
            The scan: complete at once when a result from the last 24 hours answers
            (`meta.status_code` 200), else queued or running (202); poll it with `retrieve`, or
            use `create_and_wait`.
        """
        return self._client._request(
            "POST",
            "/scans",
            body={"domain": domain, **_scan_options(checks, again)},
            idempotency_key=idempotency_key,
            cast_to=Scan,
        )

    def retrieve(self, scan_id: str, *, checks: Optional[Sequence[str]] = None) -> Scan:
        """Read a scan as it is now, with its result once completed. Free.

        Args:
            scan_id: the scan's `id`.
            checks: the checks the scan was asked for, so its result holds those.
        """
        return self._client._request(
            "GET",
            f"/scans/{path_segment('scan_id', scan_id)}",
            params=query_params(checks=checks_query(checks)),
            cast_to=Scan,
        )

    def create_and_wait(
        self,
        domain: str,
        *,
        checks: Optional[Sequence[str]] = None,
        again: bool = False,
        timeout: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        idempotency_key: Optional[str] = None,
    ) -> Scan:
        """Scan a site and wait until the scan is complete (completed with every slow source in,
        or failed), polling as often as the API's Retry-After asks.

        Args:
            domain, checks, again, idempotency_key: as for `create`.
            timeout: how long to wait in all, in seconds (120 by default).

        Returns:
            The complete scan. A failed scan is returned too: read `status` and `failure`.

        Raises:
            ScanTimeoutError: the scan wasn't complete in time; it names the scan's id and holds
                the scan as last read. The scan goes on, so read it later with `retrieve`.
        """
        started = self._client._clock()
        scan = self.create(domain, checks=checks, again=again, idempotency_key=idempotency_key)
        return self._wait_until(scan, checks, started + timeout, timeout)

    def wait(
        self,
        scan: Union[Scan, str],
        *,
        checks: Optional[Sequence[str]] = None,
        timeout: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    ) -> Scan:
        """Wait until a scan already started is complete, polling as often as Retry-After asks.

        Args:
            scan: the scan, as `create` or `batch` returned it, or its id.
            checks: the checks the scan was asked for, so its result holds those; for a scan
                passed in, its own `checks` when left out.
            timeout: how long to wait in all, in seconds (120 by default).

        Returns:
            The complete scan; a failed one too (read `status` and `failure`).

        Raises:
            ScanTimeoutError: it wasn't complete in time; the scan goes on.
        """
        started = self._client._clock()
        checks = _checks_of(scan, checks)
        current = self.retrieve(scan, checks=checks) if isinstance(scan, str) else scan
        return self._wait_until(current, checks, started + timeout, timeout)

    def _wait_until(
        self, scan: Scan, checks: Optional[Sequence[str]], deadline: float, timeout: float
    ) -> Scan:
        while not scan.complete:
            remaining = deadline - self._client._clock()
            if remaining <= 0:
                raise ScanTimeoutError(scan, timeout)
            self._client._sleep(_poll_delay_seconds(scan, remaining))
            scan = self.retrieve(scan.id, checks=checks)
        return scan

    def batch_and_wait(
        self,
        domains: Union[str, Sequence[str]],
        *,
        checks: Optional[Sequence[str]] = None,
        again: bool = False,
        timeout: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        idempotency_key: Optional[str] = None,
    ) -> ScanBatch:
        """Scan several sites (1 to 10) and wait until every scan is complete.

        Args:
            domains, checks, again, idempotency_key: as for `batch`.
            timeout: how long to wait for all of them, in seconds (120 by default).

        Returns:
            The batch with each scan complete, a domain that couldn't be scanned still a
            `ScanBatchFailure` in its place; `meta` is the batch request's (what it cost).

        Raises:
            ScanTimeoutError: a scan wasn't complete in time; the scans go on.
        """
        deadline = self._client._clock() + timeout
        batch = self.batch(domains, checks=checks, again=again, idempotency_key=idempotency_key)
        done = [
            item
            if isinstance(item, ScanBatchFailure)
            else self._wait_until(item, checks, deadline, timeout)
            for item in batch.data
        ]
        return _with_items(batch, done)

    def batch(
        self,
        domains: Union[str, Sequence[str]],
        *,
        checks: Optional[Sequence[str]] = None,
        again: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ScanBatch:
        """Scan several sites (1 to 10) in one call.

        Returns:
            One item per unique domain, in the order first sent: a `Scan`, or a
            `ScanBatchFailure` for a domain that couldn't be scanned. `meta.status_code` is 200
            when every scan was already complete, else 202.
        """
        return self._client._request(
            "POST",
            "/scans/batch",
            body={"domains": as_list(domains), **_scan_options(checks, again)},
            idempotency_key=idempotency_key,
            cast_to=ScanBatch,
        )


class AsyncScansResource:
    """Live scans of a site (async)."""

    def __init__(self, client: AsyncAPIClient) -> None:
        self._client = client

    async def create(
        self,
        domain: str,
        *,
        checks: Optional[Sequence[str]] = None,
        again: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Scan:
        """Scan a site, or join a scan of it already running; see `ScansResource.create`."""
        return await self._client._request(
            "POST",
            "/scans",
            body={"domain": domain, **_scan_options(checks, again)},
            idempotency_key=idempotency_key,
            cast_to=Scan,
        )

    async def retrieve(self, scan_id: str, *, checks: Optional[Sequence[str]] = None) -> Scan:
        """Read a scan as it is now; see `ScansResource.retrieve`."""
        return await self._client._request(
            "GET",
            f"/scans/{path_segment('scan_id', scan_id)}",
            params=query_params(checks=checks_query(checks)),
            cast_to=Scan,
        )

    async def create_and_wait(
        self,
        domain: str,
        *,
        checks: Optional[Sequence[str]] = None,
        again: bool = False,
        timeout: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        idempotency_key: Optional[str] = None,
    ) -> Scan:
        """Scan a site and wait until it is complete; see `ScansResource.create_and_wait`."""
        started = self._client._clock()
        scan = await self.create(
            domain, checks=checks, again=again, idempotency_key=idempotency_key
        )
        return await self._wait_until(scan, checks, started + timeout, timeout)

    async def wait(
        self,
        scan: Union[Scan, str],
        *,
        checks: Optional[Sequence[str]] = None,
        timeout: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    ) -> Scan:
        """Wait until a scan already started is complete; see `ScansResource.wait`."""
        started = self._client._clock()
        checks = _checks_of(scan, checks)
        current = await self.retrieve(scan, checks=checks) if isinstance(scan, str) else scan
        return await self._wait_until(current, checks, started + timeout, timeout)

    async def _wait_until(
        self, scan: Scan, checks: Optional[Sequence[str]], deadline: float, timeout: float
    ) -> Scan:
        while not scan.complete:
            remaining = deadline - self._client._clock()
            if remaining <= 0:
                raise ScanTimeoutError(scan, timeout)
            await self._client._sleep(_poll_delay_seconds(scan, remaining))
            scan = await self.retrieve(scan.id, checks=checks)
        return scan

    async def batch_and_wait(
        self,
        domains: Union[str, Sequence[str]],
        *,
        checks: Optional[Sequence[str]] = None,
        again: bool = False,
        timeout: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        idempotency_key: Optional[str] = None,
    ) -> ScanBatch:
        """Scan several sites and wait for each; see `ScansResource.batch_and_wait`."""
        deadline = self._client._clock() + timeout
        batch = await self.batch(
            domains, checks=checks, again=again, idempotency_key=idempotency_key
        )
        done: list[Union[Scan, ScanBatchFailure]] = []
        for item in batch.data:
            done.append(
                item
                if isinstance(item, ScanBatchFailure)
                else await self._wait_until(item, checks, deadline, timeout)
            )
        return _with_items(batch, done)

    async def batch(
        self,
        domains: Union[str, Sequence[str]],
        *,
        checks: Optional[Sequence[str]] = None,
        again: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ScanBatch:
        """Scan several sites in one call; see `ScansResource.batch`."""
        return await self._client._request(
            "POST",
            "/scans/batch",
            body={"domains": as_list(domains), **_scan_options(checks, again)},
            idempotency_key=idempotency_key,
            cast_to=ScanBatch,
        )
