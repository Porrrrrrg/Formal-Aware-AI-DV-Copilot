from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.test_llm_backend_contract import TINY_PROMPT, run_contract  # noqa: E402


def test_replay_backend_passes_contract(tmp_path: Path) -> None:
    responses = tmp_path / "responses.jsonl"
    prompt_sha = hashlib.sha256(TINY_PROMPT.encode()).hexdigest()
    responses.write_text(
        json.dumps(
            {
                "prompt_sha256": prompt_sha,
                "response": {"ok": True, "message": "healthcheck"},
            }
        )
        + "\n"
    )
    command = subprocess.list2cmdline(
        [
            sys.executable,
            str(ROOT / "copilot" / "llm_adapters" / "replay_json.py"),
            "--responses",
            str(responses),
        ]
    )

    result = run_contract(command, shell=True, timeout_s=10)

    assert result["ok"] is True
    assert result["classification"] == "ok"


def test_empty_stdout_is_classified_empty_backend_output(tmp_path: Path) -> None:
    backend = tmp_path / "empty_backend.py"
    backend.write_text("import sys\nsys.exit(0)\n")

    result = run_contract([sys.executable, str(backend)], timeout_s=10)

    assert result["ok"] is False
    assert result["classification"] == "empty_stdout"
