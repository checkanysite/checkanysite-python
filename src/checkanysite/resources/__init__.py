"""The API's endpoints, grouped as the client exposes them: `sites`, `scans` and `usage`.

Extending: a new endpoint is a method on its resource (sync and async), calling
`self._client._request(...)` with the model it answers; a new group is a new module here and one
attribute on each client in _client.py.
"""

from .scans import AsyncScansResource, ScansResource
from .sites import AsyncSitesResource, SitesResource
from .usage import AsyncUsageResource, UsageResource

__all__ = [
    "AsyncScansResource",
    "AsyncSitesResource",
    "AsyncUsageResource",
    "ScansResource",
    "SitesResource",
    "UsageResource",
]
