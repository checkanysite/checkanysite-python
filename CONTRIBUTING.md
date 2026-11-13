# Contributing

This repository is the source of the `checkanysite` Python library, as it is released to PyPI. The library is developed in CheckAnySite's main repository and copied here after each change, so a pull request is read here, then made there and copied back with its author named in the changelog.

## Issues

- **A bug:** the library's version (`checkanysite.__version__`), the request ID from the error or the response (`error.request_id`, `meta.request_id`), what you ran and what you expected.
- **A question about the API itself:** the [docs](https://docs.checkanysite.com) answer most; an issue here is fine too.
- **A security problem:** never in an issue. See [SECURITY.md](SECURITY.md).

## Working on the library

With [uv](https://docs.astral.sh/uv/):

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest
```

The models in `src/checkanysite/models/_generated.py` are generated from `openapi.json`, the API's OpenAPI document (also served at https://api.checkanysite.com/v1/openapi.json). Regenerate them with `uv run python scripts/generate_models.py` rather than editing that file.
