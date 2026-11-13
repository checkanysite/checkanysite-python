"""The two clients: `CheckAnySite` (sync) and `AsyncCheckAnySite` (async), one surface for both.

What: settings (key, base URL, timeout, retries) and the resources `sites`, `scans` and `usage`.
Not here: sending and retrying requests (_base_client.py) or the endpoints (resources/).
"""

from __future__ import annotations

from types import TracebackType
from typing import Optional

import httpx

from ._base_client import AsyncAPIClient, SyncAPIClient, Timeout
from ._constants import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT_SECONDS
from .resources import (
    AsyncScansResource,
    AsyncSitesResource,
    AsyncUsageResource,
    ScansResource,
    SitesResource,
    UsageResource,
)


class CheckAnySite(SyncAPIClient):
    """The CheckAnySite API client.

    Example:
        >>> from checkanysite import CheckAnySite
        >>> client = CheckAnySite()  # reads CHECKANYSITE_API_KEY
        >>> site = client.sites.retrieve("stripe.com", checks=["ai", "tech"])
        >>> site.meta.credits_remaining

    Args:
        api_key: your key (`cas_live_…`); read from CHECKANYSITE_API_KEY when left out.
        base_url: the API's address; CHECKANYSITE_BASE_URL, else https://api.checkanysite.com/v1.
        timeout: seconds each request may take to connect, send and read (30 by default), or an
            `httpx.Timeout`.
        max_retries: retries after the first try for failures that may pass (2 by default; 0
            turns retrying off).
        http_client: an `httpx.Client` of your own (proxies, transports); you close it yourself.

    Raises:
        APIError: no API key was passed or found in the environment.
    """

    sites: SitesResource
    """The Lookup API: stored results, at once, never a scan."""
    scans: ScansResource
    """The Scan API: live scans, answered asynchronously."""
    usage: UsageResource
    """This month's credits."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            http_client=http_client,
        )
        self.sites = SitesResource(self)
        self.scans = ScansResource(self)
        self.usage = UsageResource(self)

    def __enter__(self) -> CheckAnySite:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()


class AsyncCheckAnySite(AsyncAPIClient):
    """The CheckAnySite API client for asyncio, with the same methods as `CheckAnySite`.

    Example:
        >>> async with AsyncCheckAnySite() as client:
        ...     site = await client.sites.retrieve("stripe.com", checks=["ai"])

    Args: as for `CheckAnySite`, with an `httpx.AsyncClient` as `http_client`.
    """

    sites: AsyncSitesResource
    scans: AsyncScansResource
    usage: AsyncUsageResource

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Timeout = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            http_client=http_client,
        )
        self.sites = AsyncSitesResource(self)
        self.scans = AsyncScansResource(self)
        self.usage = AsyncUsageResource(self)

    async def __aenter__(self) -> AsyncCheckAnySite:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.close()
