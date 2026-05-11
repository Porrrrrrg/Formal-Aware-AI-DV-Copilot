from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from app.cli import COMMANDS, main


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
