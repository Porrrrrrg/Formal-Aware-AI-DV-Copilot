"""Safety checks for RTL repair unified diffs."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

RTL_EXTENSIONS = {".sv", ".v", ".svh", ".vh"}
FORBIDDEN_NAMES = {"generated_properties.sv", "generated_harness.sv"}
FORBIDDEN_PARTS = {"reports", "schemas", "docs", "tests", "jasper", "artifacts"}


class PatchSafetyError(ValueError):
    """Raised when an RTL repair patch violates safety policy."""


def diff_touched_paths(unified_diff: str) -> list[str]:
    paths: list[str] = []
    for line in unified_diff.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                paths.extend([parts[2], parts[3]])
        elif line.startswith("--- ") or line.startswith("+++ "):
            value = line[4:].strip()
            if value != "/dev/null":
                paths.append(value.split("\t", 1)[0])
    return sorted({normalize_diff_path(path) for path in paths if path})


def normalize_diff_path(path_text: str) -> str:
    text = path_text.strip().strip('"').replace("\\", "/")
    if text.startswith("a/") or text.startswith("b/"):
        text = text[2:]
    path = PurePosixPath(text)
    if path.is_absolute():
        raise PatchSafetyError(f"Patch path must be relative, got absolute path: {path_text}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise PatchSafetyError(f"Patch path may not contain traversal segments: {path_text}")
    return path.as_posix()


def allowed_relative_paths(allowed_patch_files: list[Path], repo_root: Path) -> set[str]:
    root = repo_root.resolve()
    paths: set[str] = set()
    for file_path in allowed_patch_files:
        resolved = file_path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise PatchSafetyError(f"Allowed patch file is outside repo root: {file_path}") from exc
        paths.add(relative.as_posix())
    return paths


def validate_patch_paths(
    unified_diff: str,
    allowed_patch_files: list[Path],
    repo_root: Path,
) -> list[str]:
    touched = diff_touched_paths(unified_diff)
    if not touched:
        raise PatchSafetyError("Patch does not touch any files.")
    allowed = allowed_relative_paths(allowed_patch_files, repo_root)
    for path in touched:
        validate_rtl_path(path)
        if path not in allowed:
            raise PatchSafetyError(f"Patch touches file outside allowed_patch_files: {path}")
    return touched


def validate_rtl_path(path_text: str) -> None:
    path = PurePosixPath(path_text)
    lowered_parts = {part.lower() for part in path.parts}
    if path.name.lower() in FORBIDDEN_NAMES:
        raise PatchSafetyError(f"Patch may not touch generated formal artifacts: {path_text}")
    if lowered_parts & FORBIDDEN_PARTS:
        raise PatchSafetyError(f"Patch may not touch non-RTL project area: {path_text}")
    if Path(path.name).suffix.lower() not in RTL_EXTENSIONS:
        raise PatchSafetyError(f"Patch target is not an RTL file: {path_text}")


def validate_unified_diff_shape(unified_diff: str) -> None:
    if not re.search(r"^diff --git ", unified_diff, flags=re.MULTILINE):
        raise PatchSafetyError("Patch must be a git-style unified diff.")
