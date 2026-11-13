"""The base classes of every model: snake_case attributes, camelCase aliases, unknown fields kept.

What: `Model`, the base of every answer shape, and `ResponseModel`, the base of the shapes a method
returns (a site's result, a scan, usage, a batch), which carry the answer's headers as `.meta`.
Why unknown fields are kept: within v1 the API adds fields without notice (ADR 0102); a client
built today keeps them in `model_extra` instead of failing or dropping them.
"""

from __future__ import annotations

from typing import Optional

import pydantic
from pydantic import ConfigDict, PrivateAttr

from .meta import ResponseMeta


class Model(pydantic.BaseModel):
    """An answer shape. Attributes are snake_case; `model_dump(by_alias=True)` gives the API's JSON.

    Fields the API added after this version of the library are kept: read them in `model_extra`
    under their JSON names.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ResponseModel(Model):
    """A shape a method returns, with what the answer's headers said in `.meta`."""

    _meta: Optional[ResponseMeta] = PrivateAttr(default=None)

    @property
    def meta(self) -> ResponseMeta:
        """The answer's request id, credits and rate limit; empty on an object nested in another."""
        return self._meta if self._meta is not None else ResponseMeta()
