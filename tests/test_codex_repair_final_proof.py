from __future__ import annotations

from pathlib import Path

import pytest

from tools.run_codex_repair_final_proof import (
    DEFAULT_ARTIFACT,
    DEFAULT_EXPECTED_SHA256,
    load_jsonl,
    make_case_and_prediction,
    normalized_sha256,
)


def load_restored_artifact_or_skip() -> list[dict[str, object]]:
    artifact = Path(DEFAULT_ARTIFACT)
    if not artifact.exists():
        pytest.skip(f"optional restored Codex repair artifact is not present: {artifact}")
    return load_jsonl(artifact)


def test_restored_codex_repair_artifact_shape_and_hash() -> None:
    artifact = Path(DEFAULT_ARTIFACT)
    rows = load_restored_artifact_or_skip()

    assert normalized_sha256(artifact) == DEFAULT_EXPECTED_SHA256
    assert len(rows) == 34
    assert len({row["case_id"] for row in rows}) == 18


def test_restored_codex_repair_row_maps_to_generated_sva_check_input() -> None:
    row = load_restored_artifact_or_skip()[0]

    case, prediction = make_case_and_prediction(row, 1)

    assert case == {
        "case_id": "repair_arbiter_mutex_syntax__attempt_01",
        "design_id": "arbiter_rr2",
        "property_id": "p_mutex",
    }
    assert prediction["property_id"] == "p_mutex"
    assert prediction["sva"].endswith(";")
