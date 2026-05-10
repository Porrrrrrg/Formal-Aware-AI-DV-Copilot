from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from app.core.artifacts import (
    ArtifactStore,
    artifact_manifest_key,
    candidate_key,
    make_attempt_id,
    make_candidate_id,
    make_outcome_id,
    make_problem_id,
    make_run_id,
    normalize_artifact_key,
    problem_spec_key,
    run_manifest_key,
    verifier_outcome_key,
    verifier_stream_key,
)
from app.models.core import (
    ArtifactEncoding,
    ArtifactKind,
    ArtifactManifest,
    ArtifactRecord,
    Candidate,
    Diagnostic,
    DiagnosticLevel,
    ErrorKind,
    ErrorRecord,
    Language,
    ProblemSpec,
    RunManifest,
    RunStatus,
    ToolName,
    ToolchainVersions,
    VerifierOutcome,
    VerificationStatus,
    advance_run_status,
    core_schema_document,
    load_core_schema,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "v1" / "core.schema.json"


@pytest.fixture()
def ids() -> dict[str, str]:
    run_id = make_run_id(
        "0123456789abcdef",
        now=datetime(2026, 5, 10, 16, 0, 0, tzinfo=timezone.utc),
        nonce="abc123",
    )
    statement = "(set-logic QF_BV)\n(check-sat)"
    problem_id = make_problem_id(ToolName.Z3, statement)
    attempt_id = make_attempt_id(1)
    candidate_id = make_candidate_id(attempt_id, "codex", statement)
    outcome_id = make_outcome_id(attempt_id, ToolName.Z3, "sat")
    return {
        "run_id": run_id,
        "statement": statement,
        "problem_id": problem_id,
        "attempt_id": attempt_id,
        "candidate_id": candidate_id,
        "outcome_id": outcome_id,
    }


@pytest.fixture()
def samples(ids: dict[str, str]) -> dict[str, object]:
    created_at = datetime(2026, 5, 10, 16, 0, 0, tzinfo=timezone.utc)
    run = RunManifest(
        run_id=ids["run_id"],
        created_at=created_at,
        git_sha="0123456789abcdef",
        dataset_version="local-smoke-v1",
        prompt_version="prompt-v1",
        model_snapshot="replay",
        toolchain=ToolchainVersions(z3="4.13.0"),
        problem_id=ids["problem_id"],
        artifacts_key=artifact_manifest_key(ids["run_id"]),
        random_seed=7,
    )
    problem = ProblemSpec(
        problem_id=ids["problem_id"],
        tool=ToolName.Z3,
        language=Language.SMT2,
        statement=ids["statement"],
        context_refs=[problem_spec_key(ids["problem_id"])],
    )
    candidate = Candidate(
        candidate_id=ids["candidate_id"],
        run_id=ids["run_id"],
        problem_id=ids["problem_id"],
        attempt_id=ids["attempt_id"],
        producer="codex",
        content=ids["statement"],
        model="replay",
        tokens_in=3,
        tokens_out=4,
    )
    stdout_ref = verifier_stream_key(ids["run_id"], ids["attempt_id"], ToolName.Z3, "stdout")
    stderr_ref = verifier_stream_key(ids["run_id"], ids["attempt_id"], ToolName.Z3, "stderr")
    outcome = VerifierOutcome(
        outcome_id=ids["outcome_id"],
        run_id=ids["run_id"],
        problem_id=ids["problem_id"],
        candidate_id=ids["candidate_id"],
        attempt_id=ids["attempt_id"],
        ok=False,
        status=VerificationStatus.FAILED,
        tool=ToolName.Z3,
        exit_code=1,
        elapsed_ms=42,
        stdout_ref=stdout_ref,
        stderr_ref=stderr_ref,
        diagnostics=[Diagnostic(level=DiagnosticLevel.ERROR, message="counterexample found")],
        error=ErrorRecord(kind=ErrorKind.ADAPTER_ERROR, message="tool returned failure"),
    )
    record = ArtifactRecord(
        key=stdout_ref,
        path=stdout_ref,
        kind=ArtifactKind.STDOUT,
        sha256="0" * 64,
        size_bytes=0,
        media_type="text/plain",
        encoding=ArtifactEncoding.TEXT,
        created_at=created_at,
    )
    manifest = ArtifactManifest(
        manifest_id=ids["run_id"],
        run_id=ids["run_id"],
        generated_at=created_at,
        artifacts=[record],
    )
    return {
        "RunManifest": run,
        "ProblemSpec": problem,
        "Candidate": candidate,
        "VerifierOutcome": outcome,
        "ArtifactManifest": manifest,
    }


def test_committed_schema_matches_pydantic_models() -> None:
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert committed == core_schema_document()


def test_core_models_round_trip_and_validate_against_schema(samples: dict[str, object]) -> None:
    schema = load_core_schema(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)
    model_types = {
        "RunManifest": RunManifest,
        "ProblemSpec": ProblemSpec,
        "Candidate": Candidate,
        "VerifierOutcome": VerifierOutcome,
        "ArtifactManifest": ArtifactManifest,
    }

    for name, instance in samples.items():
        model_type = model_types[name]
        json_payload = instance.model_dump_json()
        reloaded = model_type.model_validate_json(json_payload)
        assert reloaded == instance
        validator.evolve(schema={"$ref": f"#/$defs/{name}"}).validate(
            reloaded.model_dump(mode="json")
        )


def test_schema_rejects_extra_top_level_fields(samples: dict[str, object]) -> None:
    schema = load_core_schema(SCHEMA_PATH)
    payload = samples["VerifierOutcome"].model_dump(mode="json")
    payload["raw_stderr"] = "tool-specific raw output does not belong here"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).evolve(
            schema={"$ref": "#/$defs/VerifierOutcome"}
        ).validate(payload)


def test_problem_tool_language_compatibility(ids: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="z3 problems must use smt2"):
        ProblemSpec(
            problem_id=ids["problem_id"],
            tool=ToolName.Z3,
            language=Language.LEAN,
            statement=ids["statement"],
        )


def test_artifact_keys_are_canonical(ids: dict[str, str]) -> None:
    assert run_manifest_key(ids["run_id"]) == f"runs/20260510/{ids['run_id']}/manifest.json"
    assert problem_spec_key(ids["problem_id"]) == f"problems/{ids['problem_id']}.json"
    assert candidate_key(ids["run_id"], ids["candidate_id"]).endswith(
        f"/candidates/{ids['candidate_id']}.json"
    )
    assert verifier_outcome_key(ids["run_id"], ids["outcome_id"]).endswith(
        f"/verifier/{ids['outcome_id']}.json"
    )
    assert "\\" not in artifact_manifest_key(ids["run_id"])

    with pytest.raises(ValueError):
        normalize_artifact_key("../escape.txt")


def test_artifact_store_writes_reads_and_verifies_sha256(tmp_path: Path, samples: dict[str, object]) -> None:
    store = ArtifactStore(tmp_path)
    run_record = store.write_model(samples["RunManifest"])
    stdout_record = store.write_text(
        samples["VerifierOutcome"].stdout_ref,
        "sat\n",
        kind=ArtifactKind.STDOUT,
        producer="test",
    )

    assert store.verify_record(run_record)
    assert store.verify_record(stdout_record)
    assert store.read_json(run_record.key)["run_id"] == samples["RunManifest"].run_id
    assert stdout_record.sha256 != "0" * 64


def test_run_status_state_machine(samples: dict[str, object]) -> None:
    run = samples["RunManifest"]
    running = advance_run_status(run, RunStatus.RUNNING)
    assert running.status == RunStatus.RUNNING

    with pytest.raises(ValueError, match="invalid run status transition"):
        advance_run_status(running, RunStatus.QUEUED)
