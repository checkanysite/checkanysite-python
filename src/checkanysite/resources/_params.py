"""How the resources write their arguments into a request: paths, the checks list, optional fields.

The API checks every value itself (which checks exist, how many domains a batch takes), so these
helpers only shape the arguments and never repeat the API's limits.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional, Union
from urllib.parse import quote


def path_segment(name: str, value: str) -> str:
    """The value escaped as one path segment, so a URL or a slash can't change the path."""
    if not value:
        raise ValueError(f"{name} must not be empty.")
    return quote(value, safe="")


def as_list(values: Union[str, Sequence[str]]) -> list[str]:
    """A list of strings, from a list or a single string (`"ai"` is `["ai"]`, not its letters)."""
    return [values] if isinstance(values, str) else list(values)


def checks_query(checks: Optional[Sequence[str]]) -> Optional[str]:
    """The checks as the query takes them, separated by commas (`ai,dns`); None asks every check."""
    return ",".join(as_list(checks)) if checks is not None else None


def query_params(**fields: Union[str, int, None]) -> dict[str, Union[str, int]]:
    """The query parameters that are set: the API's defaults apply to those left out."""
    return {name: value for name, value in fields.items() if value is not None}


def json_body(**fields: object) -> dict[str, object]:
    """The body fields that are set: the API's defaults apply to those left out."""
    return {name: value for name, value in fields.items() if value is not None}
