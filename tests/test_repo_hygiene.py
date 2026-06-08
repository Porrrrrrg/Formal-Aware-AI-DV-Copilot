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
    "local_reports/",
    "reports/",
    "runs/",
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
        ROOT / "README.md",
        ROOT / "docs" / "architecture.md",
        ROOT / "docs" / "evaluation.md",
        ROOT / "docs" / "limitations_and_claims.md",
        ROOT / "docs" / "artifact_policy.md",
        ROOT / "docs" / "environment" / "jaspergold.md",
        ROOT / "docs" / "environment" / "llm_backend.md",
        ROOT / "docs" / "environment" / "moore.md",
        ROOT / "docs" / "reports" / "final_research_summary.md",
        ROOT / "docs" / "reports" / "experiment_history.md",
        ROOT / "evaluation" / "results" / "final_results.md",
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
        "local_reports/",
        "runs/",
        "/reports/",
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


def test_final_docs_preserve_result_boundaries() -> None:
    final_results = (ROOT / "evaluation" / "results" / "final_results.md").read_text()
    final_summary = (
        ROOT / "docs" / "reports" / "final_research_summary.md"
    ).read_text()
    experiment_history = (
        ROOT / "docs" / "reports" / "experiment_history.md"
    ).read_text()
    combined = "\n".join([final_results, final_summary, experiment_history])

    required_phrases = [
        "local Qwen",
        "JasperGold",
        "not Codex CLI",
        "not official FVEval",
        "production DV signoff",
        "v1.1.9",
    ]

    for phrase in required_phrases:
        assert phrase in combined
