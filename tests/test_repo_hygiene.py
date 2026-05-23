from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RAW_EDA_SUFFIXES = {".fsdb", ".jou", ".log", ".rpt", ".vcd", ".wlf"}
DENIED_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    "jgproject",
    "INCA_libs",
    "xcelium.d",
    ".formal",
}
DENIED_PREFIXES = (
    "artifacts/",
    "jasper/reports/",
    "reports/local_llm/raw/",
    "reports/llm/raw/",
    "llm_logs/",
    "raw_llm_logs/",
    "models/",
    "hf_cache/",
    "transformers_cache/",
    "torch_cache/",
)
TRACE_PATH_MARKERS = ("/traces/", "/trace/", "/trace_", "_trace/")


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_repo_hygiene_docs_exist() -> None:
    required_paths = [
        ROOT / "docs" / "repo_map.md",
        ROOT / "docs" / "artifact_policy.md",
        ROOT / "reports" / "index.md",
        ROOT / ".gitattributes",
    ]

    for path in required_paths:
        assert path.is_file(), f"missing hygiene document: {path.relative_to(ROOT)}"


def test_no_raw_local_artifacts_are_tracked() -> None:
    violations: list[str] = []

    for tracked_file in tracked_files():
        if tracked_file == "jasper/reports/.gitkeep":
            continue

        path = Path(tracked_file)
        normalized = tracked_file.replace("\\", "/")
        normalized_with_slashes = f"/{normalized}/"
        path_parts = set(path.parts)

        if path.suffix in RAW_EDA_SUFFIXES:
            violations.append(tracked_file)
        elif path_parts & DENIED_PATH_PARTS:
            violations.append(tracked_file)
        elif normalized.startswith(DENIED_PREFIXES):
            violations.append(tracked_file)
        elif any(marker in normalized_with_slashes for marker in TRACE_PATH_MARKERS):
            violations.append(tracked_file)

    assert violations == []


def test_no_tracked_file_exceeds_one_megabyte() -> None:
    oversized = []
    for tracked_file in tracked_files():
        path = ROOT / tracked_file
        if path.stat().st_size > 1_000_000:
            oversized.append(tracked_file)

    assert oversized == []


def test_ignore_rules_cover_required_local_artifact_classes() -> None:
    ignore_text = (ROOT / ".gitignore").read_text()
    required_patterns = [
        "jasper/reports/**",
        "artifacts/**",
        "**/traces/**",
        "__pycache__/",
        ".venv/",
        "*.log",
        "*.rpt",
        "*.jou",
        "*.vcd",
        "*.fsdb",
        "*.wlf",
        "llm_logs/",
        "raw_llm_logs/",
        "reports/local_llm/raw/**",
    ]

    for pattern in required_patterns:
        assert pattern in ignore_text


def test_report_index_mentions_preserved_evidence_families() -> None:
    index_text = (ROOT / "reports" / "index.md").read_text()
    required_families = [
        "reports/release/stage3_*",
        "reports/release/stage4_*",
        "reports/status/repo_hygiene_audit_*",
        "reports/status/repo_cleanup_plan_*",
        "reports/jasper/*summary*.md",
        "reports/workflows/*",
        "reports/alignment/*summary*.md",
        "reports/fveval/*",
        "reports/local_llm/*",
    ]

    for family in required_families:
        assert family in index_text
