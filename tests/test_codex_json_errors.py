from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.llm_adapters import codex_json  # noqa: E402


def test_codex_json_permission_error_is_short_and_classified(monkeypatch, capsys) -> None:
    def raise_permission(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise PermissionError("[WinError 5] Access is denied")

    monkeypatch.setattr(codex_json.subprocess, "run", raise_permission)
    monkeypatch.setattr(sys, "argv", ["codex_json.py", "--cd", str(ROOT)])
    monkeypatch.setattr(sys, "stdin", io.StringIO("Return JSON."))

    rc = codex_json.main()

    captured = capsys.readouterr()
    assert rc == 127
    assert "permission_denied" in captured.err
    assert "Access is denied" in captured.err
