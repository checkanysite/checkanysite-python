"""Shared test setup: a mocked API (respx) and clients that never really sleep.

No test reaches the network: respx answers every request, and an unmatched one fails the test.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import respx
from support import API_KEY, BASE_URL, FakeClock

from checkanysite import AsyncCheckAnySite, CheckAnySite


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never read a key or base URL from the machine they run on."""
    monkeypatch.delenv("CHECKANYSITE_API_KEY", raising=False)
    monkeypatch.delenv("CHECKANYSITE_BASE_URL", raising=False)


@pytest.fixture
def api() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(clock: FakeClock) -> Iterator[CheckAnySite]:
    client = CheckAnySite(api_key=API_KEY, base_url=BASE_URL)
    client._sleep = clock.sleep
    client._clock = clock.now
    yield client
    client.close()


@pytest.fixture
async def async_client(clock: FakeClock) -> AsyncIterator[AsyncCheckAnySite]:
    client = AsyncCheckAnySite(api_key=API_KEY, base_url=BASE_URL)
    client._sleep = clock.async_sleep
    client._clock = clock.now
    yield client
    await client.close()
