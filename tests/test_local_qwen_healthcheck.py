from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEALTHCHECK = ROOT / "ops" / "local-llm" / "healthcheck.py"


def run_healthcheck(tmp_path: Path, *extra_args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "LOCAL_ONLY": "true",
            "CLOUD_OPENAI_API_KEY": "dummy-key-must-not-be-used",
            "CLOUD_OPENAI_MODEL": "dummy-model-must-not-be-used",
            "HEALTHCHECK_LOG": str(tmp_path / "healthcheck.jsonl"),
            "QWEN_HEALTH_REPORTS_DIR": str(tmp_path),
            "QWEN_MODEL": "",
            "QWEN_PROFILE": "safe_profile",
            "SERVED_MODEL_NAME": "",
        }
    )
    env.update(extra_env)
    return subprocess.run(
        [
            sys.executable,
            str(HEALTHCHECK),
            "--base-url",
            "http://127.0.0.1:9/v1",
            "--timeout-s",
            "1",
            *extra_args,
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


def test_healthcheck_records_local_unavailable_and_disables_cloud(tmp_path: Path) -> None:
    completed = run_healthcheck(tmp_path)

    assert completed.returncode == 0, completed.stderr
    run_manifest = tmp_path / "run_manifest.json"
    assert run_manifest.exists()
    health_files = sorted(tmp_path.glob("qwen_health_*.json"))
    assert len(health_files) == 1

    record = json.loads(run_manifest.read_text(encoding="utf-8"))
    for field in [
        "model_name",
        "quantization",
        "backend",
        "gpu_name",
        "vram_gb",
        "max_model_len",
        "gpu_memory_utilization",
        "max_num_seqs",
        "LOCAL_ONLY",
        "cloud_fallback_allowed",
        "git_sha",
        "prompt_version",
        "schema_version",
    ]:
        assert field in record

    assert record["selected_profile"] == "safe_profile"
    assert record["model_name"] == "Qwen/Qwen3-14B-AWQ"
    assert record["quantization"] == "AWQ"
    assert record["LOCAL_ONLY"] is True
    assert record["cloud_fallback_allowed"] is False
    assert record["local"]["status"] == "local_unavailable"
    assert record["fallback_policy"]["cloud_not_called"] is True
    assert record["fallback_policy"]["fallback_reasons"] == []


def test_qwen_32b_awq_requires_experimental_dense_profile(tmp_path: Path) -> None:
    blocked = run_healthcheck(tmp_path, "--model", "Qwen/Qwen3-32B-AWQ")
    assert blocked.returncode != 0
    assert "experimental_dense_profile" in blocked.stderr

    allowed = run_healthcheck(
        tmp_path,
        "--profile",
        "experimental_dense_profile",
        "--model",
        "Qwen/Qwen3-32B-AWQ",
    )
    assert allowed.returncode == 0, allowed.stderr
    record = json.loads((tmp_path / "run_manifest.json").read_text(encoding="utf-8"))
    assert record["selected_profile"] == "experimental_dense_profile"
    assert record["model_name"] == "Qwen/Qwen3-32B-AWQ"
