"""Generate src/checkanysite/models/_generated.py from openapi.json (ADR 0102).

What: loosens the OpenAPI component schemas for reading answers, then runs datamodel-code-generator
on them and formats the result with ruff.
Why loosen: within v1 the API may add fields and enum values, never remove or rename them. A client
that rejected an unknown enum value, a longer string or a new check name would break on the day
the API grows, so the models check types and required fields only. Unknown fields are kept by the
models' base class (models/_base.py).
Not here: exporting openapi.json from the server (scripts/export-openapi.ts) or the batch shapes,
which are written by hand in models/batch.py until the OpenAPI document describes them.

Run from sdks/python: `uv run python scripts/generate_models.py` (needs uv's `uvx` on PATH).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = ROOT / "openapi.json"
OUTPUT_PATH = ROOT / "src" / "checkanysite" / "models" / "_generated.py"

# Pinned so a regeneration changes the models only when the schemas change.
GENERATOR = "datamodel-code-generator==0.93.0"

# Schemas only the server reads (requests) or the SDK parses by hand (errors, in errors.py).
# Requests are built by the resources, and the batch answers are written by hand (models/batch.py)
# so their items read as .result or .error and carry the answer's .meta.
SKIPPED_SCHEMAS = {
    "Error",
    "ScanRequest",
    "SiteBatchRequest",
    "ScanBatchRequest",
    "SiteBatch",
    "ScanBatch",
    "BatchError",
}

# Answer shapes whose instances carry the response's headers as `.meta` (models/_base.py).
RESPONSE_MODELS = ("SiteResult", "Scan", "Usage")

# Clearer names for inline shapes the generator would name by number or by an odd singular.
# tests/test_models.py fails if a numbered name comes back, so a new clash gets a name here.
CLASS_NAMES = {
    "AiReadinessLevel1": "AiReadinessLevelState",
    "SiteSummarySocialItem": "SiteSummarySocialProfile",
    "SiteSummaryWikidatum": "SiteSummaryWikidataItem",
    "TechnologyTechnology": "TechnologyItem",
    "UsagePricesChecks": "UsagePricesCheck",
}

# Checks that guard what the server accepts; an answer is read without them.
CONSTRAINT_KEYS = {
    "enum",
    "const",
    "pattern",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minItems",
    "maxItems",
    "propertyNames",
}

# Formats read as plain strings: a URL or id is easier to pass on as `str` than as a pydantic type.
STRING_FORMATS = {"uri", "uuid", "email"}

HEADER = (
    "Generated from openapi.json by scripts/generate_models.py: do not edit by hand.\n"
    "Regenerate with `pnpm sdk:python:models` from the repository root (ADR 0102)."
)


def loosen(schema: Any) -> Any:
    """Return the schema without constraints that only requests need, recursively."""
    if isinstance(schema, list):
        return [loosen(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    loosened: dict[str, Any] = {}
    for key, value in schema.items():
        if key in CONSTRAINT_KEYS or (key == "format" and value in STRING_FORMATS):
            continue
        # Under `properties` the keys are field names, kept whatever they are ("pattern" too).
        loosened[key] = (
            {name: loosen(field) for name, field in value.items()}
            if key == "properties"
            else loosen(value)
        )
    # A record (keys from an enum, such as prices by check) is a plain mapping: new keys may appear.
    if "additionalProperties" in loosened and "properties" not in loosened:
        loosened.pop("required", None)
    return loosened


def prepared_document() -> dict[str, Any]:
    """The OpenAPI document with only the answer schemas, loosened."""
    document = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    schemas = {
        name: loosen(schema)
        for name, schema in document["components"]["schemas"].items()
        if name not in SKIPPED_SCHEMAS
    }
    return {
        "openapi": document["openapi"],
        "info": document["info"],
        "paths": {},
        "components": {"schemas": schemas},
    }


def add_exports(path: Path) -> None:
    """Append `__all__`, naming every generated class, so `checkanysite.models` re-exports them."""
    source = path.read_text(encoding="utf-8")
    names = re.findall(r"^class (\w+)\(", source, flags=re.MULTILINE)
    exports = "".join(f'    "{name}",\n' for name in sorted(names))
    path.write_text(f"{source.rstrip()}\n\n\n__all__ = [\n{exports}]\n", encoding="utf-8")


def main() -> int:
    base = "checkanysite.models._base"
    base_class_map = {name: f"{base}.ResponseModel" for name in RESPONSE_MODELS}
    with tempfile.TemporaryDirectory() as folder:
        input_path = Path(folder) / "openapi.json"
        input_path.write_text(json.dumps(prepared_document()), encoding="utf-8")
        subprocess.run(
            [
                "uvx",
                "--from",
                GENERATOR,
                "datamodel-codegen",
                "--input",
                str(input_path),
                "--input-file-type",
                "openapi",
                "--openapi-scopes",
                "schemas",
                "--output",
                str(OUTPUT_PATH),
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--base-class",
                f"{base}.Model",
                "--base-class-map",
                json.dumps(base_class_map),
                "--model-name-map",
                json.dumps(CLASS_NAMES),
                # 3.10 is the generator's lowest target; the next two flags keep the code valid on
                # Python 3.9, where pydantic can't evaluate `X | None` at run time.
                "--target-python-version",
                "3.10",
                "--no-use-union-operator",
                "--use-standard-collections",
                "--use-annotated",
                "--snake-case-field",
                "--naming-strategy",
                "parent-prefixed",
                "--use-schema-description",
                "--use-field-description",
                "--output-datetime-class",
                "datetime",
                "--keep-model-order",
                "--use-double-quotes",
                "--disable-timestamp",
                "--custom-file-header",
                f'"""{HEADER}"""',
            ],
            check=True,
        )
    add_exports(OUTPUT_PATH)
    subprocess.run(["ruff", "check", "--fix", "--quiet", str(OUTPUT_PATH)], check=True)
    subprocess.run(["ruff", "format", "--quiet", str(OUTPUT_PATH)], check=True)
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
