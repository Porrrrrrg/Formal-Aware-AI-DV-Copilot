#!/usr/bin/env python3
"""Small JSON validation helper.

Uses jsonschema if installed. Without jsonschema, it still checks that JSON is
well-formed and required top-level keys from the schema are present.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def fallback_validate(schema: dict[str, object], data: dict[str, object]) -> list[str]:
    errors = []
    required = schema.get("required", [])
    if isinstance(required, list):
        for key in required:
            if isinstance(key, str) and key not in data:
                errors.append(f"missing required key: {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", type=Path)
    parser.add_argument("json_file", type=Path)
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text())
    data = json.loads(args.json_file.read_text())

    try:
        import jsonschema  # type: ignore
    except ModuleNotFoundError:
        errors = fallback_validate(schema, data)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("valid JSON; jsonschema not installed, used required-key fallback")
        return 0

    jsonschema.validate(instance=data, schema=schema)
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
