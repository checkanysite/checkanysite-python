"""The library's defaults in one place: where the API is, how long to wait, how often to retry.

Each can be changed per client (`CheckAnySite(timeout=..., max_retries=...)`); the base URL and
the key can also come from the environment.
"""

from ._version import __version__

DEFAULT_BASE_URL = "https://api.checkanysite.com/v1"
"""The API v1 (https://checkanysite.com/api/v1 answers the same)."""

API_KEY_ENV = "CHECKANYSITE_API_KEY"
"""The environment variable read when no `api_key` is passed."""

BASE_URL_ENV = "CHECKANYSITE_BASE_URL"
"""The environment variable read when no `base_url` is passed."""

USER_AGENT = f"checkanysite-python/{__version__}"

DEFAULT_TIMEOUT_SECONDS = 30.0
"""How long one request may wait for each of connecting, sending and reading."""

DEFAULT_MAX_RETRIES = 2
"""Retries after the first try, for failures that may pass (see _retries.py)."""

INITIAL_RETRY_DELAY_SECONDS = 0.5
"""The first retry's wait without a Retry-After header; it doubles with each retry."""

MAX_RETRY_DELAY_SECONDS = 8.0
"""The longest wait between retries without a Retry-After header."""

RETRY_JITTER_FRACTION = 0.25
"""Up to this share of a backoff wait is taken off at random, so clients don't retry in step."""

MAX_RETRY_AFTER_SECONDS = 60.0
"""The longest Retry-After the library waits out by itself; a longer one is raised to the caller.

The API's rate limit window is 60 seconds; a longer wait (no capacity for new scans until later)
is the caller's to decide.
"""

DEFAULT_WAIT_TIMEOUT_SECONDS = 120.0
"""How long `scans.create_and_wait` waits for a scan to be complete before raising."""

DEFAULT_POLL_INTERVAL_SECONDS = 3.0
"""The wait between polls of a scan when the API sends no Retry-After (it sends 3 seconds)."""

MIN_POLL_INTERVAL_SECONDS = 1.0
"""Never poll a scan more than once a second, whatever Retry-After says (a polite client)."""
