"""The typed answers of the CheckAnySite API.

What: the shapes generated from the API's OpenAPI document (`SiteResult`, `Scan`, `Usage` and the
sections inside them), the batch shapes written by hand, and `ResponseMeta`, the headers of an
answer. Attributes are snake_case; the API's camelCase JSON names are their aliases.
Extending: regenerate after the API changes (`pnpm sdk:python:models`); never edit _generated.py.
"""

from . import _generated
from ._base import Model, ResponseModel
from ._generated import *  # noqa: F403  (its __all__ names every generated class)
from .batch import (
    BatchItemError,
    ScanBatch,
    ScanBatchFailure,
    ScanBatchItem,
    SiteBatch,
    SiteBatchItem,
)
from .meta import ResponseMeta

__all__ = [
    "BatchItemError",
    "Model",
    "ResponseMeta",
    "ResponseModel",
    "ScanBatch",
    "ScanBatchFailure",
    "ScanBatchItem",
    "SiteBatch",
    "SiteBatchItem",
]
__all__ += _generated.__all__
