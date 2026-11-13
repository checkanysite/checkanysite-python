"""The answers of the two batch endpoints, written by hand from the API v1 contract (ADR 0102).

What: POST /v1/sites/batch answers `SiteBatch` (one `SiteBatchItem` per unique domain, holding a
result or an error); POST /v1/scans/batch answers `ScanBatch` (a `Scan`, or a `ScanBatchFailure`
for a domain that couldn't be scanned).
Why by hand: the OpenAPI document doesn't describe the batch endpoints yet. Once it does, these
shapes move into the generated models (scripts/generate_models.py) under the same names.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional, Union

from pydantic import Discriminator, Tag

from ._base import Model, ResponseModel
from ._generated import Scan, SiteResult


class BatchItemError(Model):
    """Why one domain of a batch has no answer: a stable code and a sentence."""

    code: str
    """The error's stable code, such as `no_result` or `invalid_domain`."""
    message: str
    """What happened, in plain words."""


class SiteBatchItem(Model):
    """One domain of a lookup batch: its stored result, or why there is none.

    Exactly one of `result` and `error` is set. A found result costs its stored price; a miss
    is free.
    """

    input: str
    """The domain or URL as it was sent."""
    domain: Optional[str]
    """The domain as the API read it; None when the input isn't a domain."""
    result: Optional[SiteResult] = None
    """The stored result, when one answers."""
    error: Optional[BatchItemError] = None
    """Why there is no result (`no_result`, `invalid_domain`, …)."""


class SiteBatch(ResponseModel):
    """The answer of `sites.batch`: one item per unique domain, in the order first sent."""

    data: list[SiteBatchItem]


class ScanBatchFailure(Model):
    """A domain of a scan batch that couldn't be scanned, and why."""

    input: str
    """The domain or URL as it was sent."""
    domain: Optional[str]
    """The domain as the API read it; None when the input isn't a domain."""
    error: BatchItemError
    """Why it wasn't scanned (`invalid_domain`, `site_refused`, …)."""


def _scan_batch_item_kind(value: Any) -> str:
    """Tells a failure (it has `error`) from a scan, for the discriminated union below."""
    has_error = "error" in value if isinstance(value, dict) else hasattr(value, "error")
    return "failure" if has_error else "scan"


ScanBatchItem = Annotated[
    Union[Annotated[Scan, Tag("scan")], Annotated[ScanBatchFailure, Tag("failure")]],
    Discriminator(_scan_batch_item_kind),
]
"""One item of a scan batch: a `Scan`, or a `ScanBatchFailure`; tell them apart with isinstance."""


class ScanBatch(ResponseModel):
    """The answer of `scans.batch`: one item per unique domain, in the order first sent.

    `meta.status_code` is 200 when every scan was already complete, else 202.
    """

    data: list[ScanBatchItem]
