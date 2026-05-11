from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

LOCAL_ARTIFACT_DIRS = [
    Path("artifacts"),
    Path(".pytest_cache"),
    Path(".ruff_cache"),
    Path(".mypy_cache"),
]

LOCAL_ARTIFACT_GLOBS = [
    "**/__pycache__",
    "jasper/reports/*",
]


def iter_existing_targets() -> list[Path]:
    targets: list[Path] = []
    for relative_path in LOCAL_ARTIFACT_DIRS:
        path = ROOT / relative_path
        if path.exists():
            targets.append(path)

    for pattern in LOCAL_ARTIFACT_GLOBS:
        for path in ROOT.glob(pattern):
            if path.name == ".gitkeep":
                continue
            if path.exists():
                targets.append(path)

    return sorted(set(targets))


def remove_target(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove ignored local artifacts from this worktree.")
    parser.add_argument("--apply", action="store_true", help="Delete targets. Default is dry-run.")
    args = parser.parse_args()

    targets = iter_existing_targets()
    if not targets:
        print("No local artifact targets found.")
        return 0

    for target in targets:
        relative = target.relative_to(ROOT)
        action = "remove" if args.apply else "would remove"
        print(f"{action}: {relative}")

    if args.apply:
        for target in targets:
            remove_target(target)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
