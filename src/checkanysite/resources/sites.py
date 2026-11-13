"""`client.sites`: the Lookup API, which answers from stored results at once and never scans.

What: `retrieve` (GET /v1/sites/{domain}) and `batch` (POST /v1/sites/batch), sync and async.
A found result costs each check asked at its stored price; a miss (`no_result`) is free.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Union

from .._base_client import AsyncAPIClient, SyncAPIClient
from ..models import SiteBatch, SiteResult
from ._params import as_list, checks_query, json_body, path_segment, query_params


class SitesResource:
    """Stored results, read without starting a scan."""

    def __init__(self, client: SyncAPIClient) -> None:
        self._client = client

    def retrieve(
        self,
        domain: str,
        *,
        checks: Optional[Sequence[str]] = None,
        max_age_days: Optional[int] = None,
    ) -> SiteResult:
        """Read our newest stored result for a site.

        Args:
            domain: the site, such as `"stripe.com"`.
            checks: the checks to answer, such as `["ai", "tech"]`; every check when left out.
                The result holds those; the other sections are None.
            max_age_days: answer only with a result at most this many days old.

        Returns:
            The stored result; `.meta` has the credits it cost.

        Raises:
            NotFoundError: with code `no_result` when we have none (as recent as asked); it is
                free, and `client.scans.create` starts a scan.
        """
        params = query_params(checks=checks_query(checks), maxAgeDays=max_age_days)
        return self._client._request(
            "GET",
            f"/sites/{path_segment('domain', domain)}",
            params=params,
            cast_to=SiteResult,
        )

    def batch(
        self,
        domains: Union[str, Sequence[str]],
        *,
        checks: Optional[Sequence[str]] = None,
        max_age_days: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> SiteBatch:
        """Read the stored results of several sites (1 to 50) in one call.

        Args:
            domains: the sites, as domains or URLs.
            checks: the checks to answer for each; every check when left out.
            max_age_days: answer only with results at most this many days old.
            idempotency_key: a key of your own (1 to 255 characters); one is made otherwise.

        Returns:
            One item per unique domain, in the order first sent, each with `.result` or `.error`.
        """
        body = json_body(
            domains=as_list(domains),
            checks=as_list(checks) if checks is not None else None,
            maxAgeDays=max_age_days,
        )
        return self._client._request(
            "POST", "/sites/batch", body=body, idempotency_key=idempotency_key, cast_to=SiteBatch
        )


class AsyncSitesResource:
    """Stored results, read without starting a scan (async)."""

    def __init__(self, client: AsyncAPIClient) -> None:
        self._client = client

    async def retrieve(
        self,
        domain: str,
        *,
        checks: Optional[Sequence[str]] = None,
        max_age_days: Optional[int] = None,
    ) -> SiteResult:
        """Read our newest stored result for a site; see `SitesResource.retrieve`."""
        params = query_params(checks=checks_query(checks), maxAgeDays=max_age_days)
        return await self._client._request(
            "GET",
            f"/sites/{path_segment('domain', domain)}",
            params=params,
            cast_to=SiteResult,
        )

    async def batch(
        self,
        domains: Union[str, Sequence[str]],
        *,
        checks: Optional[Sequence[str]] = None,
        max_age_days: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> SiteBatch:
        """Read the stored results of several sites in one call; see `SitesResource.batch`."""
        body = json_body(
            domains=as_list(domains),
            checks=as_list(checks) if checks is not None else None,
            maxAgeDays=max_age_days,
        )
        return await self._client._request(
            "POST", "/sites/batch", body=body, idempotency_key=idempotency_key, cast_to=SiteBatch
        )
