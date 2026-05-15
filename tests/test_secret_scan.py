from __future__ import annotations

import json
from pathlib import Path

from scripts.secret_scan import main, scan_repository


def test_secret_scan_allows_documentation_placeholders(tmp_path: Path) -> None:
    doc = tmp_path / "safe.md"
    doc.write_text(
        "\n".join(
            [
                'export JASPERLOOP_LLM_CMD="<your-local-command>"',
                'export OPENAI_API_KEY="<set in shell, never commit>"',
                "FAKE_OPENAI_KEY_FOR_TEST_ONLY",
                "sk-REDACTED-EXAMPLE-NOT-A-REAL-KEY",
            ]
        ),
        encoding="utf-8",
    )

    assert scan_repository(tmp_path) == []


def test_secret_scan_catches_realistic_patterns_without_logging_value(tmp_path: Path) -> None:
    secret_value = "A" * 36
    openai_like = "sk-" + ("B" * 20)
    assigned_secret = "C" * 24
    fixture = tmp_path / "fixture.py"
    fixture.write_text(
        "\n".join(
            [
                "github_token = " + repr("ghp_" + secret_value),
                "openai_key = " + repr(openai_like),
                "api_key = " + repr(assigned_secret),
            ]
        ),
        encoding="utf-8",
    )

    findings = scan_repository(tmp_path)
    rule_ids = {finding["rule_id"] for finding in findings}
    assert {"github-token", "openai-api-key", "assigned-secret"} <= rule_ids
    assert all("value" not in finding for finding in findings)


def test_secret_scan_cli_writes_redacted_artifacts(tmp_path: Path, capsys) -> None:
    secret_value = "sk-" + ("D" * 20)
    (tmp_path / "config.txt").write_text(f"token = {secret_value!r}\n", encoding="utf-8")

    json_out = tmp_path / "out" / "scan.json"
    sarif_out = tmp_path / "out" / "scan.sarif"
    assert main(["--root", str(tmp_path), "--json-out", str(json_out), "--sarif-out", str(sarif_out)]) == 1

    captured = capsys.readouterr()
    assert secret_value not in captured.err
    assert secret_value not in json_out.read_text(encoding="utf-8")
    assert secret_value not in sarif_out.read_text(encoding="utf-8")

    findings = json.loads(json_out.read_text(encoding="utf-8"))
    assert findings[0]["path"] == "config.txt"
    assert findings[0]["line"] == 1
