from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from app.cli import COMMANDS, MOORE_TASK_TYPES, main


def test_cli_help_lists_stage5a_commands() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", "--help"],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "jasperloop" in result.stdout
    for subcommand in COMMANDS:
        assert subcommand in result.stdout
    assert "align-intent" in result.stdout


@pytest.mark.parametrize("subcommand", sorted(COMMANDS))
def test_dry_run_writes_manifest_without_external_calls(tmp_path: Path, subcommand: str) -> None:
    out_dir = tmp_path / subcommand

    exit_code = main([subcommand, "--dry-run", "--out-dir", str(out_dir)])

    manifest_path = out_dir / "jasperloop_run_manifest.json"
    core_run_path = out_dir / "core_run_manifest.json"
    artifact_manifest_path = out_dir / "core_artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert core_run_path.exists()
    assert artifact_manifest_path.exists()
    assert manifest["command"] == "jasperloop"
    assert manifest["subcommand"] == subcommand
    assert manifest["dry_run"] is True
    assert manifest["external_calls_allowed"] is False
    assert manifest["runner_invoked"] is False
    assert manifest["evidence_type"] == COMMANDS[subcommand].evidence_type
    assert manifest["claim_boundary"]
    assert manifest["git_sha"]
    assert manifest["created_at_utc"].endswith("Z")
    assert manifest["out_dir"] == str(out_dir)


ROOT = Path(__file__).resolve().parents[1]


def test_console_entrypoint_is_configured() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["jasperloop"] == "app.cli:main"


def test_eval_and_moore_handoff_dry_run_manifest_boundaries(tmp_path: Path) -> None:
    for subcommand in ["eval", "moore-handoff"]:
        out_dir = tmp_path / subcommand

        assert main([subcommand, "--dry-run", "--out-dir", str(out_dir)]) == 0

        manifest = json.loads(
            (out_dir / "jasperloop_run_manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["external_calls_allowed"] is False
        assert manifest["planned_internal_runner"] == COMMANDS[subcommand].planned_runner
        assert "JasperGold" in " ".join(manifest["notes"])


@pytest.mark.parametrize(
    "argv",
    [
        ["moore-handoff", "--help"],
        ["moore-handoff", "prepare", "--help"],
        ["moore-handoff", "validate", "--help"],
        ["moore-handoff", "import-result", "--help"],
        ["align-intent", "--help"],
    ],
)
def test_moore_handoff_nested_help(argv: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", *argv],
        check=True,
        text=True,
        capture_output=True,
    )

    assert argv[0] in result.stdout or "Moore" in result.stdout


@pytest.mark.parametrize("task_type", MOORE_TASK_TYPES)
def test_moore_handoff_prepare_dry_run_for_all_task_types(
    tmp_path: Path,
    task_type: str,
) -> None:
    out_dir = tmp_path / task_type

    exit_code = main(["moore-handoff", "prepare", task_type, "--dry-run", "--out-dir", str(out_dir)])

    manifest_path = out_dir / "handoff_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert manifest["manifest_type"] == "MooreHandoffManifest"
    assert manifest["git_sha"]
    assert manifest["branch"]
    assert manifest["task_type"] == task_type
    assert manifest["dry_run"] is True
    assert manifest["external_calls_allowed"] is False
    assert manifest["raw_prompt_text_included"] is False
    assert manifest["input_artifact_refs"]
    assert all("sha256" in ref for ref in manifest["input_artifact_refs"])


def test_moore_handoff_validate_catches_missing_input_artifacts(tmp_path: Path) -> None:
    manifest_path = tmp_path / "handoff_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_type": "MooreHandoffManifest",
                "schema_version": "stage5b.moore_handoff.v1",
                "input_artifact_refs": [
                    {
                        "path": "missing/input_artifact.json",
                        "sha256": "0" * 64,
                    }
                ],
                "expected_outputs": ["reports/jasper/example_summary.md"],
                "forbidden_outputs": ["*.log"],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["moore-handoff", "validate", "--manifest", str(manifest_path), "--dry-run"])

    assert exit_code == 2


def test_moore_handoff_import_result_rejects_forbidden_raw_log_paths(tmp_path: Path) -> None:
    source = tmp_path / "moore_manifest.json"
    source.write_text(
        json.dumps(
            {
                "run_id": "moore_test",
                "summary": {"candidate_count": 1},
                "artifacts": [{"path": "jasper/reports/case/run.log"}],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        ["moore-handoff", "import-result", "--manifest", str(source), "--dry-run", "--out-dir", str(tmp_path)]
    )

    assert exit_code == 2


@pytest.mark.parametrize("use_manifest_option", [True, False])
def test_moore_handoff_import_result_emits_artifact_manifest(
    tmp_path: Path,
    use_manifest_option: bool,
) -> None:
    source = tmp_path / "moore_manifest.json"
    source.write_text(
        json.dumps(
            {
                "run_id": "moore_test",
                "summary": {"candidate_count": 1},
                "artifacts": [{"path": "reports/jasper/lightweight_summary.md"}],
            }
        ),
        encoding="utf-8",
    )

    manifest_arg = ["--manifest", str(source)] if use_manifest_option else [str(source)]
    exit_code = main(["moore-handoff", "import-result", *manifest_arg, "--dry-run", "--out-dir", str(tmp_path)])

    artifact_manifest = json.loads(
        (tmp_path / "moore_import_artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert exit_code == 0
    assert artifact_manifest["artifacts"]
    assert artifact_manifest["metadata"]["external_calls_allowed"] is False


def test_moore_handoff_import_result_accepts_utf8_bom_manifest(tmp_path: Path) -> None:
    source = tmp_path / "moore_manifest.json"
    source.write_text(
        json.dumps(
            {
                "run_id": "moore_test",
                "summary": {"candidate_count": 1},
                "artifacts": [{"path": "reports/jasper/lightweight_summary.md"}],
            }
        ),
        encoding="utf-8-sig",
    )

    exit_code = main(
        ["moore-handoff", "import-result", "--manifest", str(source), "--dry-run", "--out-dir", str(tmp_path)]
    )

    assert exit_code == 0
    assert (tmp_path / "moore_import_artifact_manifest.json").exists()


def test_moore_handoff_prepare_dry_run_does_not_invoke_planned_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    real_run = subprocess.run

    def recording_run(cmd: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr("app.cli.subprocess.run", recording_run)

    exit_code = main(
        [
            "moore-handoff",
            "prepare",
            "codex-repair-final-proof",
            "--dry-run",
            "--out-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert calls
    assert all("run_moore_codex_repair_final_proof.sh" not in call for call in calls)
