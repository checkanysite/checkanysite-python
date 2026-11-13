# Changelog

All notable changes to the `checkanysite` Python library. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [semantic versioning](https://semver.org).

## 0.1.2 (2026-11-13)

The same client as 0.1.1, with links to where its source lives.

- The package links its source on GitHub, [checkanysite/checkanysite-python](https://github.com/checkanysite/checkanysite-python), with its issues and this changelog, and its documentation to the library's own page.

## 0.1.1 (2026-11-13)

The first version for general use: the same client as 0.1.0, with a full README and a quickstart example. 0.1.0 was yanked until the API went live and is available again.

- A rewritten README: installation, usage, stored results and scans, checks, batches, the async client, errors, request IDs, retries, timeouts, configuration, credits and rate limits.
- The quickstart example uses a stored result when there is one, scans the site when there isn't, and prints what the AI check found with a link to the evidence.

## 0.1.0 (2026-11-12)

The first version, for the CheckAnySite API v1.

- `CheckAnySite` and `AsyncCheckAnySite`, configured by argument or by `CHECKANYSITE_API_KEY` and `CHECKANYSITE_BASE_URL`.
- The Lookup API: `sites.retrieve` and `sites.batch`.
- The Scan API: `scans.create`, `scans.retrieve` and `scans.batch`; `scans.wait`, `scans.create_and_wait` and `scans.batch_and_wait`, which poll as often as `Retry-After` asks and raise `ScanTimeoutError` at their timeout.
- `usage.retrieve`.
- Typed answers generated from the API's OpenAPI document, keeping fields and values added later; `.meta` with the request id, credits and rate limit from the headers.
- Errors by status (`BadRequestError` … `InternalServerError`), connection errors and timeouts, each with the API's code, message, parameter and request id.
- Retries with exponential backoff and jitter, honouring `Retry-After`; an automatic `Idempotency-Key` on every POST, kept across its retries.
- A client never closed closes its connections when it is garbage collected, so it leaves no `ResourceWarning`.
