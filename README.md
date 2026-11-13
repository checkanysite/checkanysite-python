# CheckAnySite Python library

[![PyPI version](https://img.shields.io/pypi/v/checkanysite.svg)](https://pypi.org/project/checkanysite/)
[![Python versions](https://img.shields.io/pypi/pyversions/checkanysite.svg)](https://pypi.org/project/checkanysite/)

The CheckAnySite Python library provides convenient access to the [CheckAnySite API](https://docs.checkanysite.com) from Python 3.9+ applications. Ask what any public website is: whether it was built with an AI website builder, how ready it is for AI tools, how popular it is, what it runs on, and what its DNS records, trust signals and history show. Every answer comes with its evidence.

The library includes typed models for every response, synchronous and asynchronous clients powered by [httpx](https://www.python-httpx.org), and automatic retries.

## Documentation

The API reference and guides are at [docs.checkanysite.com](https://docs.checkanysite.com).

## Installation

```sh
pip install checkanysite
```

Or, with [uv](https://docs.astral.sh/uv/):

```sh
uv add checkanysite
```

## Usage

Create an API key on your [account page](https://checkanysite.com/account/keys); keys are free while the API launches. Keep the key out of your code by setting it in the `CHECKANYSITE_API_KEY` environment variable:

```sh
export CHECKANYSITE_API_KEY="cas_live_…"
```

The following example checks whether a site shows traces of an AI website builder:

```python
from checkanysite import CheckAnySite

client = CheckAnySite()  # Reads the key from CHECKANYSITE_API_KEY.

site = client.sites.retrieve("stripe.com", checks=["ai"])

if site.ai.level == "none":
    print(f"No AI builder traces found on {site.domain}.")
else:
    builders = ", ".join(builder.name for builder in site.ai.builders)
    print(f"{site.domain}: traces of {builders}, {site.ai.level} confidence")

print(f"Evidence: {site.result_url}")
```

`client.sites.retrieve` returns our stored result for a site straight away and never starts a scan. For a site we haven't checked yet, it raises `NotFoundError`, and you can scan the site instead.

### Scan a site

The following example scans a site and waits for the result:

```python
from checkanysite import CheckAnySite

client = CheckAnySite()

scan = client.scans.create_and_wait("example.com", checks=["readiness"])

if scan.status == "completed":
    print(f"AI readiness: {scan.result.readiness.score} out of 100")
else:
    print(f"The scan failed: {scan.failure.message}")
```

`create_and_wait` starts a scan and polls it until it is complete; most scans take a few seconds. If the scan takes longer than `timeout` (120 seconds by default), it raises `ScanTimeoutError`. The scan keeps running, so you can read it later with `client.scans.retrieve(error.scan_id)`. To start a scan without waiting for it, call `client.scans.create`.

### Use a stored result when there is one

A stored result costs fewer credits than a new scan. The following function uses the stored result when there is one and scans the site otherwise:

```python
from checkanysite import CheckAnySite, NotFoundError

client = CheckAnySite()


def ai_traces(domain):
    """Returns the AI builder traces of a site, or None if its scan failed."""
    try:
        return client.sites.retrieve(domain, checks=["ai"]).ai
    except NotFoundError:
        scan = client.scans.create_and_wait(domain, checks=["ai"])
        return scan.result.ai if scan.status == "completed" else None
```

## Checks

Each request asks for one or more checks and costs credits for each of them. Leave out `checks` to ask for all of them.

| Check        | What it answers                                                                        |
| ------------ | -------------------------------------------------------------------------------------- |
| `ai`         | Traces of Lovable, Bolt, v0 and other AI website builders, each with the exact line    |
| `readiness`  | A score out of 100 for how well AI tools find, read and use the site                   |
| `popularity` | A band from public ranked lists, and the site's rank in each                           |
| `tech`       | Frameworks, site builders, shop systems, analytics and the network, with evidence      |
| `dns`        | DNS records, whether DNSSEC validated them, and the network                            |
| `trust`      | Contact and company details, policies, HTTPS and domain age, and a score out of 100    |
| `summary`    | What the site says about itself, its kind, and who is behind it by independent sources |
| `history`    | Its registration, first certificate and first web archive capture, each dated          |

Every account gets free credits each month while the API launches. [Credits](https://docs.checkanysite.com/credits) lists what each check costs.

## Check many sites at once

The following example looks up several sites in one request:

```python
from checkanysite import CheckAnySite

client = CheckAnySite()

domains = ["stripe.com", "lovable.dev", "example.org"]
batch = client.sites.batch(domains, checks=["ai"])

for item in batch.data:
    if item.result:
        print(f"{item.domain}: {item.result.ai.level}")
    else:
        print(f"{item.input}: {item.error.message}")
```

`client.sites.batch` looks up to 50 sites. A site without a stored result comes back with an error in its place and costs nothing. `client.scans.batch_and_wait` scans up to 10 sites and waits until every scan is complete.

## Async usage

`AsyncCheckAnySite` has the same methods as `CheckAnySite`; await each call. The following example finds the framework of two sites at once:

```python
import asyncio

from checkanysite import AsyncCheckAnySite


async def main():
    async with AsyncCheckAnySite() as client:
        sites = await asyncio.gather(
            client.sites.retrieve("stripe.com", checks=["tech"]),
            client.sites.retrieve("vercel.com", checks=["tech"]),
        )
    for site in sites:
        frameworks = [item.name for item in site.tech.technologies if item.category == "Framework"]
        print(f"{site.domain}: {', '.join(frameworks) or 'no framework found'}")


asyncio.run(main())
```

## Handling errors

When the library can't reach the API, for example because of a network problem or a timeout, it raises `checkanysite.APIConnectionError`. When the API returns an error, it raises a subclass of `checkanysite.APIStatusError`, which carries the HTTP `status_code`, the error's `code` and `message`, and the `request_id`. All of them inherit from `checkanysite.APIError`.

```python
import logging

import checkanysite
from checkanysite import CheckAnySite

logger = logging.getLogger(__name__)
client = CheckAnySite()

try:
    site = client.sites.retrieve("stripe.com", checks=["ai"])
except checkanysite.AuthenticationError as error:
    logger.error("CheckAnySite rejected the API key: %s", error.message)
    raise
except checkanysite.RateLimitError as error:
    # Requests over the rate limit were already retried. A spent monthly or
    # daily limit lasts until its reset, which the message gives.
    logger.warning("CheckAnySite limit reached: %s", error.message)
    raise
except checkanysite.APIStatusError as error:
    logger.error(
        "CheckAnySite returned %s (%s): %s Request ID: %s",
        error.status_code,
        error.code,
        error.message,
        error.request_id,
    )
    raise
except checkanysite.APIConnectionError:
    logger.error("Could not reach the CheckAnySite API.")
    raise
```

Each status has its own class:

| Status         | Class                      | Codes                                                                       |
| -------------- | -------------------------- | --------------------------------------------------------------------------- |
| 400            | `BadRequestError`          | `invalid_json`, `invalid_parameter`, `invalid_domain`                       |
| 401            | `AuthenticationError`      | `missing_api_key`, `invalid_api_key`, `revoked_api_key`, `expired_api_key`  |
| 403            | `PermissionDeniedError`    | `read_only_key`, `browser_request`                                          |
| 404            | `NotFoundError`            | `not_found`, `no_result`, `scan_not_found`                                  |
| 409            | `ConflictError`            | `idempotency_key_in_use`                                                    |
| 422            | `UnprocessableEntityError` | `site_refused`, `idempotency_key_reused`                                    |
| 429            | `RateLimitError`           | `rate_limited`, `quota_exceeded`, `key_limit_reached`, `scan_limit_reached` |
| 500 and above  | `InternalServerError`      | `internal_error`, `capacity`                                                |
| Other statuses | `APIStatusError`           | `method_not_allowed` (405), `request_too_large` (413) and others            |
| No response    | `APIConnectionError`       | `APITimeoutError` when the request timed out                                |

New codes can appear within v1, each in the class of its status. The [errors](https://docs.checkanysite.com/errors) page explains every code.

## Request IDs

Every response object has `meta.request_id`, and every `APIStatusError` has `request_id`, both taken from the `X-Request-Id` header. Include it when you contact us about a request.

## Retries

The library retries a failed request twice by default, with exponential backoff, when it may succeed later: connection errors and timeouts, `409 idempotency_key_in_use`, `429 rate_limited`, and statuses of 500 and above. When the API sends a `Retry-After` header, the library waits that long, up to 60 seconds. It never retries a spent limit (`quota_exceeded`, `key_limit_reached` or `scan_limit_reached`).

You can change the number of retries:

```python
from checkanysite import CheckAnySite

client = CheckAnySite(max_retries=5)  # Use 0 to turn retries off.
```

Retried scans are never started twice. Every POST request carries an `Idempotency-Key` header, so when a response is lost and the request is retried, the API returns the first response instead of starting and charging for a second scan. To make a request safe to repeat across runs of your program, pass your own key; the API keeps it for 24 hours:

```python
from checkanysite import CheckAnySite

client = CheckAnySite()

scan = client.scans.create("stripe.com", checks=["ai"], idempotency_key="nightly-stripe-2026-11-12")
```

## Timeouts

Requests time out after 30 seconds by default. You can change it, in seconds or as an `httpx.Timeout`:

```python
from checkanysite import CheckAnySite

client = CheckAnySite(timeout=10.0)
```

## Configuration

| Argument      | Environment variable    | Default                                            |
| ------------- | ----------------------- | -------------------------------------------------- |
| `api_key`     | `CHECKANYSITE_API_KEY`  | None; a key is required                            |
| `base_url`    | `CHECKANYSITE_BASE_URL` | `https://api.checkanysite.com/v1`                  |
| `timeout`     |                         | 30 seconds                                         |
| `max_retries` |                         | 2                                                  |
| `http_client` |                         | A new `httpx.Client`; pass your own to use a proxy |

The client keeps its connections open between requests. Use it as a context manager (`with CheckAnySite() as client:`), or call `client.close()` when you're done. An `http_client` you pass in stays yours to close.

## Credits and rate limits

Every response object has a `meta` attribute with the values of the response headers:

| Attribute                                                      | Header                                       |
| -------------------------------------------------------------- | -------------------------------------------- |
| `credits_cost`, `credits_remaining`, `credits_reset`           | `X-Credits-*`, on requests that cost credits |
| `rate_limit_limit`, `rate_limit_remaining`, `rate_limit_reset` | `X-RateLimit-*`                              |
| `retry_after_seconds`                                          | `Retry-After`                                |
| `idempotent_replayed`                                          | `Idempotent-Replayed`                        |
| `request_id`                                                   | `X-Request-Id`                               |
| `status_code`, `etag`, `headers`                               | The status code, `ETag` and every header     |

`client.usage.retrieve()` returns your month's credits: the allowance, what you have used and what is left.

## Models

Responses are [pydantic](https://docs.pydantic.dev) models generated from the API's OpenAPI document. Attributes are snake_case (`site.scanned_at`), and `model_dump(by_alias=True)` returns the API's camelCase JSON. Within v1 the API may add fields and values, but never removes or renames them. The models keep what they don't know yet: new fields are in `model_extra`, and new values of a field such as `level` arrive as plain strings.

## Requirements

Python 3.9 or later.

## Versioning

This package follows [semantic versioning](https://semver.org) and is built for v1 of the API. The changelog ships with the package as `CHANGELOG.md`.

## License

MIT
