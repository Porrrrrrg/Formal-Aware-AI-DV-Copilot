#!/usr/bin/env python3
"""Build an RTL project manifest that points at scratch-patched RTL files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover - dependency-minimal local smoke runs.

    class Draft202012Validator:  # type: ignore[no-redef]
        def __init__(self, _schema: dict[str, Any]) -> None:
            pass

        def validate(self, _instance: dict[str, Any]) -> None:
            return None


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "copilot" / "schemas" / "rtl_project_manifest.schema.json"


def build_patched_manifest(
    *,
    original_manifest: dict[str, Any],
    applied_patch_manifest: dict[str, Any],
    out_path: Path | None = None,
) -> dict[str, Any]:
    scratch_dir = applied_patch_manifest.get("scratch_dir")
    repo_root = applied_patch_manifest.get("repo_root")
    if not scratch_dir:
        raise ValueError("applied_patch_manifest must describe a scratch patch, not in-place apply.")
    if not repo_root:
        raise ValueError("applied_patch_manifest is missing repo_root.")

    scratch_root = Path(str(scratch_dir)).resolve()
    original_root = Path(str(repo_root)).resolve()
    updated = json.loads(json.dumps(original_manifest))
    updated["rtl_files"] = [
        patched_path_for(Path(str(path)), original_root, scratch_root)
        for path in list_value(original_manifest.get("rtl_files"))
    ]
    updated["assumption_files"] = [
        patched_path_for(Path(str(path)), original_root, scratch_root)
        for path in list_value(original_manifest.get("assumption_files"))
    ]
    validate_manifest(updated)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    return updated


def patched_path_for(path: Path, original_root: Path, scratch_root: Path) -> str:
    resolved = path if path.is_absolute() else original_root / path
    relative = resolved.resolve().relative_to(original_root)
    return (scratch_root / relative).as_posix()


def validate_manifest(manifest: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)


def list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--applied-patch-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = build_patched_manifest(
            original_manifest=load_json(args.manifest),
            applied_patch_manifest=load_json(args.applied_patch_manifest),
            out_path=args.out,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should report schema/path blockers clearly.
        print(f"build_patched_manifest: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"patched_manifest": args.out.as_posix(), "rtl_files": manifest["rtl_files"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
