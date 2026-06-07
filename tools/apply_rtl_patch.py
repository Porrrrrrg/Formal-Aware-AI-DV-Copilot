#!/usr/bin/env python3
"""Apply an RTL repair patch to a scratch copy by default."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rtl_patch_safety import (  # noqa: E402
    PatchSafetyError,
    allowed_relative_paths,
    validate_patch_paths,
    validate_unified_diff_shape,
)


def apply_rtl_patch(
    *,
    unified_diff: str,
    allowed_patch_files: list[Path],
    scratch_dir: Path,
    repo_root: Path,
    out_path: Path | None = None,
    apply_in_place: bool = False,
    acknowledge_risk: bool = False,
) -> dict[str, Any]:
    validate_unified_diff_shape(unified_diff)
    repo_root = repo_root.resolve()
    touched = validate_patch_paths(unified_diff, allowed_patch_files, repo_root)
    if apply_in_place and not acknowledge_risk:
        raise PatchSafetyError("--apply-in-place requires --acknowledge-risk.")

    target_root = repo_root if apply_in_place else scratch_dir.resolve()
    if not apply_in_place:
        prepare_scratch_copy(allowed_patch_files, repo_root, target_root)
    patch_path = target_root / "rtl_repair.patch"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(unified_diff, encoding="utf-8")
    run_git_apply_check(patch_path, target_root)
    run_git_apply(patch_path, target_root)

    manifest = {
        "schema_version": "applied_rtl_patch_manifest_v1",
        "apply_in_place": apply_in_place,
        "repo_root": str(repo_root),
        "scratch_dir": None if apply_in_place else str(target_root),
        "patch_path": str(patch_path),
        "touched_files": touched,
        "allowed_patch_files": sorted(
            allowed_relative_paths(allowed_patch_files, repo_root)
        ),
    }
    output = out_path or target_root / "applied_patch_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(output)
    return manifest


def prepare_scratch_copy(allowed_patch_files: list[Path], repo_root: Path, scratch_dir: Path) -> None:
    scratch_dir.mkdir(parents=True, exist_ok=True)
    for file_path in allowed_patch_files:
        resolved = file_path.resolve()
        relative = resolved.relative_to(repo_root)
        target = scratch_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved, target)


def run_git_apply_check(patch_path: Path, cwd: Path) -> None:
    if shutil.which("git") is None:
        return
    completed = subprocess.run(
        ["git", "apply", "--check", str(patch_path)],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PatchSafetyError(f"git apply --check failed: {completed.stderr.strip()}")


def run_git_apply(patch_path: Path, cwd: Path) -> None:
    if shutil.which("git") is None:
        raise PatchSafetyError("git is required to apply RTL patches in this tool.")
    completed = subprocess.run(
        ["git", "apply", str(patch_path)],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PatchSafetyError(f"git apply failed: {completed.stderr.strip()}")


def load_candidate(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--allowed-patch-file", action="append", default=[], type=Path)
    parser.add_argument("--scratch-dir", type=Path, default=Path("artifacts/rtl_patch_scratch"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--apply-in-place", action="store_true")
    parser.add_argument("--acknowledge-risk", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate = load_candidate(args.candidate)
    if args.diff:
        unified_diff = args.diff.read_text(encoding="utf-8")
    else:
        unified_diff = str(candidate.get("unified_diff") or "")
    try:
        manifest = apply_rtl_patch(
            unified_diff=unified_diff,
            allowed_patch_files=args.allowed_patch_file,
            scratch_dir=args.scratch_dir,
            repo_root=args.repo_root,
            out_path=args.out,
            apply_in_place=args.apply_in_place,
            acknowledge_risk=args.acknowledge_risk,
        )
    except PatchSafetyError as exc:
        print(f"apply_rtl_patch: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
