"""What an answer's headers say about the call: its request id, credits and rate limit.

What: `ResponseMeta`, read from the headers the API sends (X-Request-Id, X-Credits-*,
X-RateLimit-*, Retry-After, Idempotent-Replayed, ETag), and the Retry-After parser the retries
share. Every value is None when its header is missing or can't be read: a missing header never
fails a call.
Not here: deciding whether to retry (that is _base_client.py).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional


@dataclass(frozen=True)
class ResponseMeta:
    """The headers of the answer an object came from, as typed values.

    Read it from the object a method returns, such as `site.meta.credits_remaining`. Objects
    nested inside an answer (a scan's result, a batch's items) carry an empty one.
    """

    status_code: Optional[int] = None
    """The HTTP status, such as 200, or 202 for a scan still on its way."""
    request_id: Optional[str] = None
    """The request's id (X-Request-Id); quote it when you write to us."""
    credits_cost: Optional[int] = None
    """Credits this call cost (X-Credits-Cost), on calls that cost credits."""
    credits_remaining: Optional[int] = None
    """Credits the account has left this month (X-Credits-Remaining)."""
    credits_reset: Optional[datetime] = None
    """When the month's credits start again, in UTC (X-Credits-Reset)."""
    rate_limit_limit: Optional[int] = None
    """Calls the key may make in the rate limit's window (X-RateLimit-Limit)."""
    rate_limit_remaining: Optional[int] = None
    """Calls left in the current window (X-RateLimit-Remaining)."""
    rate_limit_reset: Optional[datetime] = None
    """When the window starts again, in UTC (X-RateLimit-Reset, sent as Unix seconds)."""
    retry_after_seconds: Optional[float] = None
    """How long to wait before asking again (Retry-After): sent while a scan isn't complete."""
    idempotent_replayed: bool = False
    """True when this is the stored answer to an earlier call with the same Idempotency-Key."""
    etag: Optional[str] = None
    """The answer's ETag, for a conditional request later."""
    headers: Mapping[str, str] = field(default_factory=dict)
    """Every header of the answer, by lower-case name, for anything not read above."""

    @classmethod
    def from_headers(cls, status_code: int, headers: Mapping[str, str]) -> ResponseMeta:
        """Read the meta from an answer's status and headers (any case of header names)."""
        lower = {name.lower(): value for name, value in headers.items()}
        return cls(
            status_code=status_code,
            request_id=lower.get("x-request-id"),
            credits_cost=_int(lower.get("x-credits-cost")),
            credits_remaining=_int(lower.get("x-credits-remaining")),
            credits_reset=_iso_datetime(lower.get("x-credits-reset")),
            rate_limit_limit=_int(lower.get("x-ratelimit-limit")),
            rate_limit_remaining=_int(lower.get("x-ratelimit-remaining")),
            rate_limit_reset=_unix_datetime(lower.get("x-ratelimit-reset")),
            retry_after_seconds=parse_retry_after(lower.get("retry-after")),
            idempotent_replayed=lower.get("idempotent-replayed", "").strip().lower() == "true",
            etag=lower.get("etag"),
            headers=lower,
        )


def parse_retry_after(value: Optional[str], now: Optional[datetime] = None) -> Optional[float]:
    """Seconds to wait from a Retry-After value: a number of seconds, or an HTTP date.

    Args:
        value: the header's value, or None when it is missing.
        now: the current time, for an HTTP date; defaults to the clock (passed in by tests).

    Returns:
        The seconds to wait (never negative), or None when the value is missing or unreadable.
    """
    if value is None:
        return None
    text = value.strip()
    try:
        seconds = float(text)
    except ValueError:
        try:
            when = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        seconds = (when - (now or datetime.now(timezone.utc))).total_seconds()
    if seconds != seconds or seconds in (float("inf"), float("-inf")):  # NaN or infinite
        return None
    return max(seconds, 0.0)


def _int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        # Python before 3.11 doesn't read a trailing "Z" as UTC.
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _unix_datetime(value: Optional[str]) -> Optional[datetime]:
    seconds = _int(value)
    return datetime.fromtimestamp(seconds, tz=timezone.utc) if seconds is not None else None
