from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.output_quality import source_summary  # noqa: E402
from scripts import doctor_llm_backend as doctor  # noqa: E402


def test_missing_codex_bin_is_classified_missing_executable(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    report = doctor.inspect_executable("CODEX_BIN", str(missing), timeout_s=1)

    assert report["exists"] is False
    assert report["short_command_test"]["status"] == doctor.STATUS_MISSING_EXECUTABLE


def test_permission_error_is_classified_permission_denied(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fake = tmp_path / "codex.exe"
    fake.write_text("")

    def raise_permission(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise PermissionError("[WinError 5] Access is denied")

    monkeypatch.setattr(doctor.subprocess, "run", raise_permission)
    report = doctor.inspect_executable("CODEX_BIN", str(fake), timeout_s=1)

    assert report["short_command_test"]["status"] == doctor.STATUS_PERMISSION_DENIED
    assert "Access is denied" in report["short_command_test"]["error"]


def test_interactive_stderr_is_classified_interactive_only() -> None:
    completed = subprocess.CompletedProcess(
        args=["fake"],
        returncode=2,
        stdout="",
        stderr="must be run in an interactive terminal",
    )

    assert doctor.classify_completed_process(completed) == doctor.STATUS_INTERACTIVE_ONLY


def test_fallback_source_is_not_llm_success() -> None:
    summary = source_summary([{"source": "structured_fallback", "llm_error": "backend failed"}])

    assert summary["llm_success_rate"] == 0.0
    assert summary["fallback_rate"] == 1.0
    assert summary["llm_error_rate"] == 1.0
