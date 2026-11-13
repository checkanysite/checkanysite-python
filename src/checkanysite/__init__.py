"""The official Python library for the CheckAnySite API: what is this website, with evidence.

    from checkanysite import CheckAnySite

    client = CheckAnySite()  # reads CHECKANYSITE_API_KEY
    site = client.sites.retrieve("stripe.com", checks=["ai", "tech"])

Docs: https://docs.checkanysite.com. The answers' types are in `checkanysite.models`.
"""

from . import models
from ._client import AsyncCheckAnySite, CheckAnySite
from ._version import __version__
from .errors import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ScanTimeoutError,
    UnprocessableEntityError,
)

__all__ = [
    "APIConnectionError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncCheckAnySite",
    "AuthenticationError",
    "BadRequestError",
    "CheckAnySite",
    "ConflictError",
    "InternalServerError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "ScanTimeoutError",
    "UnprocessableEntityError",
    "__version__",
    "models",
]
