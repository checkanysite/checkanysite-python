"""What the tests share: the fake base URL and key, a fake clock, and answers in the API's shape."""

from __future__ import annotations

from typing import Any, Optional

BASE_URL = "https://api.test/v1"
API_KEY = "cas_live_test_0000"
SCAN_ID = "0b5a7a6e-1f7e-4d7c-9a4e-2f0d8b1c6a11"


class FakeClock:
    """Stands in for time.monotonic and the sleeps: sleeping moves the clock, without waiting."""

    def __init__(self) -> None:
        self.now_seconds = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.now_seconds

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now_seconds += seconds

    async def async_sleep(self, seconds: float) -> None:
        self.sleep(seconds)


def site_result_json(
    domain: str = "stripe.com", checks: tuple[str, ...] = ("ai",)
) -> dict[str, Any]:
    """A stored result holding the `ai` check, as the API answers it (src/app/api/examples.ts)."""
    return {
        "domain": domain,
        "checks": list(checks),
        "scanId": SCAN_ID,
        "scannedAt": "2026-11-10T09:30:06.000Z",
        "complete": True,
        "pending": [],
        "limited": None,
        "finalUrl": f"https://{domain}/",
        "resultUrl": f"https://checkanysite.com/site/{domain}?focus=ai",
        "versions": {"signatures": "2026.11.1", "score": "3"},
        "ai": {"level": "none", "builders": [], "patterns": []},
        "readiness": None,
        "popularity": None,
        "tech": None,
        "dns": None,
        "trust": None,
        "score": None,
        "summary": None,
        "history": None,
        "notes": [],
    }


def scan_json(
    status: str = "queued",
    *,
    scan_id: str = SCAN_ID,
    domain: str = "example.com",
    complete: Optional[bool] = None,
    failure: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """A scan as the API answers it; `complete` follows the status unless given."""
    finished = status in ("completed", "failed")
    return {
        "id": scan_id,
        "domain": domain,
        "checks": ["ai"],
        "status": status,
        "createdAt": "2026-11-10T09:30:00.000Z",
        "finishedAt": "2026-11-10T09:30:06.000Z" if finished else None,
        "complete": finished if complete is None else complete,
        "failure": failure,
        "result": site_result_json(domain) if status == "completed" else None,
        "links": {
            "self": f"https://checkanysite.com/api/v1/scans/{scan_id}?checks=ai",
            "result": f"https://checkanysite.com/site/{domain}?focus=ai",
        },
    }


def usage_json() -> dict[str, Any]:
    """A month's usage, part spent, for a key with a limit of its own."""
    price = {"stored": 1, "scan": 5}
    return {
        "period": {"start": "2026-11-01T00:00:00.000Z", "end": "2026-12-01T00:00:00.000Z"},
        "allowance": 50,
        "used": 18,
        "remaining": 32,
        "key": {
            "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "name": "Production",
            "monthlyCreditLimit": 20,
            "used": 6,
            "remaining": 14,
        },
        "prices": {
            "checks": {check: price for check in ("ai", "readiness", "dns")},
            "allChecks": {"stored": 4, "scan": 20},
        },
        "rateLimit": {"requests": 60, "periodSeconds": 60},
    }


def error_json(code: str, message: str = "Something happened.", **extra: str) -> dict[str, Any]:
    """An error answer in the API's shape."""
    return {
        "error": {
            "code": code,
            "message": message,
            "docs": f"https://checkanysite.com/developers/docs/errors#{code}",
            "requestId": "req_from_body",
            **extra,
        }
    }
