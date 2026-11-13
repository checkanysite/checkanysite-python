"""`client.usage`: the credits the key's account used and has left this month (GET /v1/usage)."""

from __future__ import annotations

from .._base_client import AsyncAPIClient, SyncAPIClient
from ..models import Usage


class UsageResource:
    """This month's credits, the key's own limit, and what each check costs."""

    def __init__(self, client: SyncAPIClient) -> None:
        self._client = client

    def retrieve(self) -> Usage:
        """Read this month's credits (UTC) for the key's account. Free."""
        return self._client._request("GET", "/usage", cast_to=Usage)


class AsyncUsageResource:
    """This month's credits, the key's own limit, and what each check costs (async)."""

    def __init__(self, client: AsyncAPIClient) -> None:
        self._client = client

    async def retrieve(self) -> Usage:
        """Read this month's credits (UTC) for the key's account. Free."""
        return await self._client._request("GET", "/usage", cast_to=Usage)
