"""When a failed request is tried again, and after how long (ADR 0102).

What: two pure functions the sync and async clients share. A request is retried when the
failure may pass by itself:
- no answer (a connection error or a timeout);
- 409 `idempotency_key_in_use`: the first request with this key is still running;
- 429 only for `rate_limited`, never `quota_exceeded` or `key_limit_reached` (credits spent) or
  `scan_limit_reached` (the day's new scans started);
- 500, 502, 503 and 504.
Retrying a POST is safe because it carries the same Idempotency-Key on every try.
Not here: the loop itself, which sleeps in the sync or async way (_base_client.py).
"""

from __future__ import annotations

import random
from typing import Callable, Optional

from ._constants import (
    INITIAL_RETRY_DELAY_SECONDS,
    MAX_RETRY_AFTER_SECONDS,
    MAX_RETRY_DELAY_SECONDS,
    RETRY_JITTER_FRACTION,
)

RETRYABLE_STATUSES = frozenset({500, 502, 503, 504})
"""Statuses retried whatever their code."""

RETRYABLE_CODES = {409: frozenset({"idempotency_key_in_use"}), 429: frozenset({"rate_limited"})}
"""Statuses retried only for these codes."""


def is_retryable_status(status_code: int, code: Optional[str]) -> bool:
    """True when an error answer with this status and code may succeed if asked again."""
    if status_code in RETRYABLE_STATUSES:
        return True
    return code is not None and code in RETRYABLE_CODES.get(status_code, frozenset())


def retry_delay_seconds(
    retries_done: int,
    retry_after_seconds: Optional[float],
    random_fraction: Callable[[], float] = random.random,
) -> Optional[float]:
    """How long to wait before the next try, or None when the wait is the caller's to decide.

    Args:
        retries_done: how many retries came before this one (0 for the first).
        retry_after_seconds: the answer's Retry-After, if it sent one.
        random_fraction: a source of numbers in [0, 1), for the jitter (passed in by tests).

    Returns:
        The Retry-After when the API sent one it is reasonable to wait out (up to 60 seconds);
        else an exponential backoff (0.5, 1, 2 … up to 8 seconds) with up to a quarter taken off
        at random. None when the Retry-After is longer than the library waits by itself.
    """
    if retry_after_seconds is not None:
        return retry_after_seconds if retry_after_seconds <= MAX_RETRY_AFTER_SECONDS else None
    backoff: float = min(INITIAL_RETRY_DELAY_SECONDS * 2.0**retries_done, MAX_RETRY_DELAY_SECONDS)
    return backoff * (1 - RETRY_JITTER_FRACTION * random_fraction())
