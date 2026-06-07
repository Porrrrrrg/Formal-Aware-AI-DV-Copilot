#!/usr/bin/env python3
"""Evaluate retrieval-assisted Design2SVA on local fixture tasks."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, ValidationError
except ModuleNotFoundError:  # pragma: no cover - dependency-minimal local smoke runs.

    class ValidationError(Exception):  # type: ignore[no-redef]
        pass

    class Draft202012Validator:  # type: ignore[no-redef]
        def __init__(self, _schema: dict[str, Any]) -> None:
            pass

        def validate(self, _instance: dict[str, Any]) -> None:
            return None


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.design2sva_agent import (  # noqa: E402
    DEFAULT_REPLAY_PATH,
    generate_candidates,
    load_replay_records,
    normalize_candidate,
    structured_candidate,
    validate_candidate,
)
from copilot.agents.design2sva_repair_agent import repair_design2sva_candidate  # noqa: E402
from copilot.agents.design2sva_reachability import (  # noqa: E402
    antecedent_reachable,
    antecedent_unreachable,
    apply_cover_status,
    build_antecedent_metadata,
)
try:  # noqa: E402
    from copilot.agents.design2sva_harness_diagnostics import (  # type: ignore
        build_harness_diagnostic_bundle as external_harness_diagnostics,
        build_harness_diagnostic_predictions as external_diagnostic_cover_predictions,
    )
except ImportError:  # pragma: no cover - optional Stage 11 helper during partial checkouts.
    external_harness_diagnostics = None
    external_diagnostic_cover_predictions = None

try:  # noqa: E402
    from copilot.agents.design2sva_rootcause import (  # type: ignore
        classify_design2sva_root_cause as external_root_cause_classifier,
        summarize_root_cause_candidates as external_root_cause_summary,
    )
except ImportError:  # pragma: no cover - optional Stage 11 helper during partial checkouts.
    external_root_cause_classifier = None
    external_root_cause_summary = None
from copilot.retrieval import Design2SVAContextOptions, build_design2sva_context  # noqa: E402
from copilot.sva_library import (  # noqa: E402
    hallucinated_identifiers,
    normalize_sva,
    syntax_scaffold_ok,
)

DEFAULT_CASES = Path("benchmarks/design2sva_cases.json")
DEFAULT_OUT = Path("evaluation/results/design2sva_eval_local.json")
DEFAULT_MARKDOWN = Path("evaluation/results/design2sva_results.md")
DEFAULT_JASPER_REPLAY_PATH = Path("evaluation/fixtures/design2sva_anti_vacuity_replay.jsonl")
DEFAULT_NATIVE_ORACLE_PATH = Path(
    "evaluation/results/design2sva_native_reference_oracle_jasper.json"
)
TASK_SCHEMA = ROOT / "copilot" / "schemas" / "design2sva_task.schema.json"

DESIGN2SVA_FAILURE_TAXONOMY = {
    "syntax_error",
    "unknown_signal",
    "reset_clock_mismatch",
    "unsupported_helper_code",
    "overstrong_assertion",
    "weak_vacuous_assertion",
    "unreachable_antecedent",
    "unreachable_cover_goal",
    "temporal_mismatch",
    "proven_non_vacuous",
}

FAILURE_CATEGORIES = DESIGN2SVA_FAILURE_TAXONOMY | {
    "backend_blocked",
    "not_run",
}

ROOT_CAUSE_LABELS = {
    "native_harness_unreachable",
    "design2sva_embedding_bug",
    "reset_clock_mismatch",
    "cover_generation_bug",
    "reference_task_invalid",
    "jasper_parser_misclassification",
    "candidate_generation_failure",
    "unknown",
}


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(resolve_repo_path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    schema = json.loads(TASK_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    cases = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"{path} contains a non-object case entry")
        validator.validate(item)
        cases.append(item)
    return cases


def load_native_oracle_results(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    resolved = resolve_repo_path(path)
    if not resolved.exists():
        return {}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    rows = payload.get("results", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    indexed = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("case_id") or "")
        if case_id:
            indexed[case_id] = row
    return indexed


def build_context(case: dict[str, Any], context_budget: int) -> dict[str, Any]:
    rtl_path = resolve_repo_path(Path(str(case["design_rtl_path"])))
    return build_design2sva_context(
        [rtl_path],
        Design2SVAContextOptions(
            module_name=str(case.get("module_name") or case["design_id"]),
            focus_signals=tuple(str(signal) for signal in case.get("visible_signals", [])),
            property_intent=str(case.get("intent", "")),
            visible_signal_budget=context_budget,
        ),
    )


def jasper_backend() -> Any:
    try:
        from copilot.backends.jasper_backend import JasperBackend
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency-minimal smoke runs.
        if exc.name != "pydantic":
            raise
        return LightweightJasperBackend()

    return JasperBackend()


class LightweightStatus:
    def __init__(self, value: str) -> None:
        self.value = value


class LightweightCheckResult:
    def __init__(self, status: str) -> None:
        self.status = LightweightStatus(status)


class LightweightBackendResult:
    backend = "jaspergold"
    raw_log_paths: list[str] = []
    counterexample_paths: list[str] = []

    def __init__(
        self,
        *,
        legacy: dict[str, Any],
        dry_run: bool,
        metadata: dict[str, Any],
    ) -> None:
        syntax = legacy_syntax_status(legacy)
        proof = str(legacy.get("proof_status") or "not_run")
        vacuity = str(legacy.get("vacuity_status") or "not_run")
        self.status = LightweightStatus("dry_run" if dry_run else legacy_overall_status(legacy))
        self.syntax_result = LightweightCheckResult(syntax)
        self.proof_result = LightweightCheckResult(proof)
        self.vacuity_result = LightweightCheckResult(vacuity)
        self.report_dir = str(legacy.get("report_dir") or "")
        self.raw_report_paths = {
            "properties": legacy.get("properties_report"),
            "cover": legacy.get("cover_report"),
            "vacuity": legacy.get("vacuity_report"),
        }
        self.metadata = metadata

    @classmethod
    def blocked(cls, report_dir: Path, message: str) -> "LightweightBackendResult":
        result = cls.__new__(cls)
        result.status = LightweightStatus("blocked")
        result.syntax_result = LightweightCheckResult("error")
        result.proof_result = LightweightCheckResult("not_run")
        result.vacuity_result = LightweightCheckResult("not_run")
        result.report_dir = str(report_dir)
        result.raw_report_paths = {
            "properties": None,
            "cover": None,
            "vacuity": None,
        }
        result.metadata = {"backend_blocked": {"message": message}}
        result.feedback = message
        return result

    def to_legacy_check_dict(self) -> dict[str, Any]:
        return {
            "proof_status": self.proof_result.status.value,
            "vacuity_status": self.vacuity_result.status.value,
        }


class LightweightJasperBackend:
    def check_generated_sva(
        self,
        case: dict[str, Any],
        prediction: dict[str, Any],
        system: str,
        out_root: Path | None = None,
        dry_run: bool = False,
    ) -> LightweightBackendResult:
        from tools.check_generated_sva import check_generated_sva

        try:
            legacy = check_generated_sva(
                case=case,
                prediction=prediction,
                system=system,
                out_root=out_root,
                dry_run=dry_run,
            )
        except RuntimeError as exc:
            root = resolve_repo_path(out_root or Path("jasper/reports/sva_generation"))
            return LightweightBackendResult.blocked(
                report_dir=root / system / str(case.get("case_id", "unknown_case")),
                message=str(exc),
            )
        metadata: dict[str, Any] = {}
        if isinstance(legacy.get("artifact_paths"), dict):
            metadata["artifact_paths"] = legacy["artifact_paths"]
        if isinstance(legacy.get("embedding_audit"), dict):
            metadata["embedding_audit"] = legacy["embedding_audit"]
        return LightweightBackendResult(legacy=legacy, dry_run=dry_run, metadata=metadata)


def legacy_syntax_status(legacy: dict[str, Any]) -> str:
    syntax_pass = legacy.get("syntax_pass")
    if syntax_pass is True:
        return "passed"
    if syntax_pass is False:
        return "syntax_error"
    return "not_run"


def legacy_overall_status(legacy: dict[str, Any]) -> str:
    proof = str(legacy.get("proof_status") or "").lower()
    vacuity = str(legacy.get("vacuity_status") or "").lower()
    if vacuity == "vacuous":
        return "vacuous"
    if proof in {"proven", "covered"}:
        return "passed"
    if proof in {"falsified", "uncovered", "unreachable"}:
        return "failed"
    return "unknown"


def run_case(
    case: dict[str, Any],
    k: int,
    max_repair_rounds: int,
    reference_oracle: bool,
    use_llm: bool,
    llm_command: str | None,
    replay_records: list[dict[str, Any]] | None,
    jasper_check: bool,
    jasper_dry_run: bool,
    jasper_replay_records: list[dict[str, Any]] | None,
    jasper_out_root: Path,
    context_budget: int,
    native_oracle: dict[str, Any] | None = None,
    run_harness_diagnostics: bool = False,
    repair_with_llm: bool = False,
    repair_llm_command: str | None = None,
) -> dict[str, Any]:
    context = build_context(case, context_budget=context_budget)
    if reference_oracle:
        initial_candidates = [reference_oracle_candidate(case, context)]
        effective_max_repair_rounds = 0
    else:
        initial_candidates = generate_candidates(
            case,
            context,
            k=k,
            use_llm=use_llm,
            llm_command=llm_command,
            replay_records=replay_records,
        )
        effective_max_repair_rounds = max_repair_rounds
    candidate_paths = []
    for candidate_index, candidate in enumerate(initial_candidates):
        rounds = []
        current = candidate
        for round_index in range(effective_max_repair_rounds + 1):
            evaluated = evaluate_candidate(
                case=case,
                context=context,
                candidate=current,
                candidate_index=candidate_index,
                round_index=round_index,
                jasper_check=jasper_check,
                jasper_dry_run=jasper_dry_run,
                jasper_replay_records=jasper_replay_records,
                jasper_out_root=jasper_out_root,
                native_oracle=native_oracle,
                run_harness_diagnostics=run_harness_diagnostics,
            )
            rounds.append(evaluated)
            formal_mode = jasper_check and (jasper_replay_records is not None or not jasper_dry_run)
            if row_success(evaluated["metrics"], formal_mode=formal_mode):
                break
            if round_index == effective_max_repair_rounds:
                break
            current = repair_candidate(
                case,
                context,
                current,
                evaluated["metrics"],
                candidate_index,
                round_index + 1,
                replay_records=replay_records,
                repair_with_llm=repair_with_llm,
                repair_llm_command=repair_llm_command,
            )
        candidate_paths.append(
            {
                "candidate_index": candidate_index,
                "rounds": rounds,
                "final_metrics": rounds[-1]["metrics"],
            }
        )

    audit_metrics = None
    if reference_oracle and candidate_paths and candidate_paths[0]["rounds"]:
        audit_metrics = candidate_paths[0]["rounds"][0]["metrics"]

    return {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": case["property_id"],
        "context": context,
        "native_reference_oracle": native_oracle or {},
        "harness_reachability_audit": build_reference_harness_reachability_audit(
            case,
            metrics=audit_metrics,
            native_oracle=native_oracle,
        ),
        "candidate_paths": candidate_paths,
    }


def evaluate_candidate(
    case: dict[str, Any],
    context: dict[str, Any],
    candidate: dict[str, Any],
    candidate_index: int,
    round_index: int,
    jasper_check: bool,
    jasper_dry_run: bool,
    jasper_replay_records: list[dict[str, Any]] | None,
    jasper_out_root: Path,
    native_oracle: dict[str, Any] | None = None,
    run_harness_diagnostics: bool = False,
) -> dict[str, Any]:
    validation_error = ""
    valid_json = True
    try:
        validate_candidate(candidate)
    except ValidationError as exc:
        valid_json = False
        validation_error = exc.message

    sva = str(candidate.get("sva", ""))
    allowed = sorted(allowed_identifiers(case, context))
    hallucinated = hallucinated_identifiers(sva, allowed + [str(case["property_id"])])
    helper_issue = helper_code_disallowed(case, str(candidate.get("helper_code", "")))
    reset_clock_issue = reset_clock_mismatch(case, sva)
    reference = reference_sva(case)
    exact_match = normalize_sva(sva) == normalize_sva(reference) if reference else None
    antecedent_metadata = build_antecedent_metadata(
        sva,
        str(candidate.get("property_id") or case["property_id"]),
    )
    backend_result = None
    cover_backend_result = None
    proof_metadata = default_proof_metadata()
    if jasper_replay_records is not None:
        proof_metadata = replay_proof_metadata(
            jasper_replay_records,
            case,
            candidate_index,
            round_index,
            check_kind="assertion",
            default_backend="jaspergold_replay",
        )
        cover_metadata = replay_proof_metadata(
            jasper_replay_records,
            case,
            candidate_index,
            round_index,
            check_kind="cover",
            default_backend="jaspergold_replay",
        )
        antecedent_metadata = apply_cover_status(antecedent_metadata, cover_metadata)
    elif jasper_check:
        backend_result = jasper_backend().check_generated_sva(
            case=legacy_case_shape(case),
            prediction=candidate,
            system=f"design2sva_c{candidate_index}_r{round_index}",
            out_root=jasper_out_root,
            dry_run=jasper_dry_run,
        )
        proof_metadata = proof_metadata_from_backend(backend_result)
        if requires_antecedent_cover(antecedent_metadata) and antecedent_metadata.get(
            "cover_sva"
        ):
            cover_prediction = {
                "property_id": antecedent_metadata["cover_property_id"],
                "sva": antecedent_metadata["cover_sva"],
                "helper_code": "",
                "check_kind": "cover",
            }
            cover_backend_result = jasper_backend().check_generated_sva(
                case=legacy_case_shape(case),
                prediction=cover_prediction,
                system=f"design2sva_c{candidate_index}_r{round_index}_antecedent_cover",
                out_root=jasper_out_root,
                dry_run=jasper_dry_run,
            )
            antecedent_metadata = apply_cover_status(
                antecedent_metadata,
                proof_metadata_from_backend(cover_backend_result),
            )

    harness_diagnostics = build_clock_reset_diagnostics(
        case,
        jasper_check=jasper_check,
        jasper_dry_run=jasper_dry_run,
        jasper_replay_records=jasper_replay_records,
        jasper_out_root=jasper_out_root,
        candidate_index=candidate_index,
        round_index=round_index,
        run_checks=run_harness_diagnostics,
    )
    embedding_audit = build_embedding_audit(
        case=case,
        candidate=candidate,
        antecedent_metadata=antecedent_metadata,
        assertion_backend_result=backend_result,
        cover_backend_result=cover_backend_result,
    )
    metrics = {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": case["property_id"],
        "candidate_index": candidate_index,
        "round": round_index,
        "valid_json": valid_json,
        "validation_error": validation_error,
        "syntax_ok": syntax_scaffold_ok(sva),
        "exact_match": exact_match,
        "has_hallucinated_signal": bool(hallucinated),
        "hallucinated_identifiers": hallucinated,
        "reset_clock_mismatch": reset_clock_issue,
        "unsupported_helper_code_issue": helper_issue,
        "source": candidate.get("source", "unknown"),
        "property_type": property_type_from_antecedent_metadata(antecedent_metadata),
        "proof_metadata": proof_metadata,
        "antecedent_metadata": antecedent_metadata,
        "antecedent_reachable": antecedent_reachable(antecedent_metadata),
        "cover_reachable": antecedent_reachable(antecedent_metadata),
        "clock_reset_metadata": clock_reset_metadata(case),
        "clock_reset_diagnostics": harness_diagnostics,
        "reset_release_reachable": harness_diagnostics.get("reset_release_reachable"),
        "post_reset_reachable": harness_diagnostics.get("post_reset_reachable"),
        "clock_event_assumed": harness_diagnostics.get("clock_event_assumed"),
        "reset_polarity_used": harness_diagnostics.get("reset_polarity_used"),
        "disable_iff_used": harness_diagnostics.get("disable_iff_used"),
        "harness_reachability_status": harness_reachability_status(antecedent_metadata),
        "embedding_audit": embedding_audit,
        "native_reference_oracle": native_oracle or {},
    }
    metrics["failure_category"] = classify_failure(metrics)
    metrics["root_cause_candidate"] = classify_root_cause_candidate(metrics, native_oracle)
    metrics["root_cause_detail"] = classify_root_cause_detail(metrics, native_oracle)
    metrics["wrapper_parity_pass"] = wrapper_parity_pass(metrics, native_oracle)
    candidate = dict(candidate)
    candidate["repair_metadata"] = {
        "round": round_index,
        "failure_category": metrics["failure_category"],
        "feedback": failure_feedback(metrics),
        "changed_by_repair": round_index > 0,
    }
    candidate["proof_metadata"] = candidate_schema_proof_metadata(proof_metadata)
    if valid_json:
        validate_candidate(candidate)
    return {"candidate": candidate, "metrics": metrics}


def reference_oracle_candidate(case: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    reference = reference_sva(case).strip()
    if not reference:
        raise ValueError(f"{case['case_id']} has no evaluation_metadata.reference_sva")
    raw = {
        "property_id": str(case["property_id"]),
        "sva": reference,
        "helper_code": "",
        "intent_summary": "Reference oracle assertion from local fixture metadata.",
        "source": "reference_oracle",
    }
    return normalize_candidate(
        case,
        context,
        raw,
        source="reference_oracle",
        round_index=0,
    )


def build_reference_harness_reachability_audit(
    case: dict[str, Any],
    metrics: dict[str, Any] | None = None,
    native_oracle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reference = reference_sva(case).strip()
    if metrics is not None:
        antecedent_metadata = dict(metrics.get("antecedent_metadata") or {})
        proof_metadata = dict(metrics.get("proof_metadata") or default_proof_metadata())
        syntax_ok = bool(metrics.get("syntax_ok"))
        reset_clock_issue = bool(metrics.get("reset_clock_mismatch"))
    else:
        antecedent_metadata = (
            build_antecedent_metadata(reference, str(case["property_id"]))
            if reference
            else {
                "extraction_status": "unknown",
                "reason": "missing_reference_sva",
                "antecedent": None,
                "event_control": None,
                "disable_iff": None,
                "cover_property_id": "",
                "cover_sva": "",
                "cover_status": "unknown",
                "antecedent_reachability": "unknown",
            }
        )
        proof_metadata = default_proof_metadata()
        syntax_ok = syntax_scaffold_ok(reference) if reference else False
        reset_clock_issue = reset_clock_mismatch(case, reference) if reference else True

    reachable = antecedent_reachable(antecedent_metadata)
    proven = proof_status_is_proven(proof_metadata)
    non_vacuous = proven and proof_not_vacuous(proof_metadata) and (
        reachable or not requires_antecedent_cover(antecedent_metadata)
    )
    return {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": case["property_id"],
        "reference_available": bool(reference),
        "reference_sva": reference,
        "clock_reset_metadata": clock_reset_metadata(case),
        "reference_reset_clock_mismatch": reset_clock_issue,
        "reference_syntax_ok": syntax_ok,
        "reference_proof_metadata": proof_metadata,
        "reference_antecedent_metadata": antecedent_metadata,
        "reference_antecedent_reachable": reachable,
        "reference_proven": proven,
        "reference_non_vacuous": non_vacuous,
        "harness_reachability_status": harness_reachability_status(antecedent_metadata),
        "cover_property_id": antecedent_metadata.get("cover_property_id"),
        "cover_sva": antecedent_metadata.get("cover_sva"),
        "cover_status": antecedent_metadata.get("cover_status"),
        "native_reference_oracle": native_oracle or {},
    }


def repair_candidate(
    case: dict[str, Any],
    context: dict[str, Any],
    candidate: dict[str, Any],
    metrics: dict[str, Any],
    candidate_index: int,
    round_index: int,
    replay_records: list[dict[str, Any]] | None = None,
    repair_with_llm: bool = False,
    repair_llm_command: str | None = None,
) -> dict[str, Any]:
    repaired = (
        replay_candidate_for_round(case, replay_records, candidate_index, round_index)
        if replay_records is not None
        else None
    )
    if repaired is None and repair_with_llm:
        repaired = repair_design2sva_candidate(
            task=case,
            context=context,
            current_candidate=candidate,
            metrics=metrics,
            formal_debug_bundle=None,
            jasper_feedback=failure_feedback(metrics),
            active_assumptions=case.get("active_assumptions", []),
            round_index=round_index,
            use_llm=True,
            llm_command=repair_llm_command,
        )
    if repaired is None:
        repaired = structured_candidate(case)
    repaired["source"] = "repair"
    repaired["failure_category"] = metrics["failure_category"]
    repaired["feedback"] = failure_feedback(metrics)
    repaired["changed_by_repair"] = normalize_sva(str(candidate.get("sva", ""))) != normalize_sva(
        str(repaired.get("sva", ""))
    )
    return normalize_candidate(case, context, repaired, source="repair", round_index=round_index)


def classify_failure(metrics: dict[str, Any]) -> str:
    if not metrics["valid_json"]:
        return "syntax_error"
    if metrics["unsupported_helper_code_issue"]:
        return "unsupported_helper_code"
    if metrics["has_hallucinated_signal"]:
        return "unknown_signal"
    if not metrics["syntax_ok"]:
        return "syntax_error"
    proof = metrics.get("proof_metadata", {})
    if proof.get("status") == "blocked":
        return "backend_blocked"
    if proof.get("syntax_status") == "syntax_error":
        return "syntax_error"
    if metrics["reset_clock_mismatch"]:
        return "reset_clock_mismatch"
    proof_status = str(proof.get("proof_status") or "").lower()
    vacuity_status = str(proof.get("vacuity_status") or "").lower()
    backend_status = str(proof.get("status") or "").lower()
    antecedent = metrics.get("antecedent_metadata", {})
    if proof_status == "falsified":
        return "overstrong_assertion"
    if vacuity_status == "vacuous" or backend_status == "vacuous":
        return "weak_vacuous_assertion"
    if antecedent_unreachable(antecedent) and requires_antecedent_cover(antecedent):
        if str(antecedent.get("extraction_status")) == "extracted":
            return "unreachable_antecedent"
        return "unreachable_cover_goal"
    if proof_status == "uncovered":
        return "unreachable_cover_goal"
    if proof_status == "unreachable":
        if requires_antecedent_cover(antecedent) and str(
            antecedent.get("extraction_status")
        ) == "extracted":
            return "unreachable_antecedent"
        return "unreachable_cover_goal"
    if proof_status in {"undetermined", "unknown"}:
        return "temporal_mismatch"
    if formal_success(metrics):
        return "proven_non_vacuous"
    if metrics["exact_match"] is False:
        return "temporal_mismatch"
    if backend_status == "dry_run" or proof_status in {"", "not_run"}:
        return "not_run"
    return "temporal_mismatch"


def failure_feedback(metrics: dict[str, Any]) -> str:
    category = str(metrics.get("failure_category", "not_run"))
    if category == "unknown_signal":
        return "Candidate references unknown signals: " + ", ".join(
            metrics["hallucinated_identifiers"]
        )
    if category == "unsupported_helper_code":
        return "Candidate uses helper code when the task policy disallows helper code."
    if category == "reset_clock_mismatch":
        return "Candidate clock/reset event does not match the task clock/reset contract."
    if category == "syntax_error":
        return "Candidate failed local or Jasper SVA syntax checks."
    if category == "unreachable_antecedent":
        return (
            "Candidate trigger is unreachable. Weaken or correct the antecedent, remove "
            "impossible state assumptions, align reset polarity, or use a simpler "
            "interface-level safety invariant."
        )
    if category == "unreachable_cover_goal":
        return (
            "Candidate cover goal is unreachable or uncovered. Replace impossible cover "
            "conditions with a reachable trigger or fall back to a simpler invariant."
        )
    if category == "weak_vacuous_assertion":
        return (
            "Candidate appears weak or vacuous. Repair should target reachable trigger "
            "conditions before preserving assertion shape."
        )
    if category == "overstrong_assertion":
        return "Candidate was falsified; it may be overstrong for the design and harness."
    if category == "temporal_mismatch":
        return (
            "Candidate syntax is valid but temporal behavior does not match "
            "available reference feedback."
        )
    return "No repair feedback was required."


def summarize(
    results: list[dict[str, Any]],
    k: int,
    jasper_check: bool,
    jasper_dry_run: bool,
    jasper_replay: bool = False,
) -> dict[str, Any]:
    first_round_rows = []
    all_initial_rows = []
    all_rows = []
    repair_rows = []
    final_rows = []
    reference_audits = []
    for result in results:
        audit = result.get("harness_reachability_audit")
        if isinstance(audit, dict):
            reference_audits.append(audit)
        for path in result["candidate_paths"]:
            rounds = path["rounds"]
            if not rounds:
                continue
            all_initial_rows.append(rounds[0]["metrics"])
            all_rows.extend(round_record["metrics"] for round_record in rounds)
            final_rows.append(path["final_metrics"])
            if path["candidate_index"] == 0:
                first_round_rows.append(rounds[0]["metrics"])
            repair_rows.extend(round_record["metrics"] for round_record in rounds[1:])

    formal_mode = jasper_check and (jasper_replay or not jasper_dry_run)
    first_by_case = group_initial_by_case(all_initial_rows)
    final_by_case = group_initial_by_case(final_rows)
    syntax_at_1 = rate(first_round_rows, lambda row: row["syntax_ok"])
    syntax_at_k = rate(
        list(first_by_case.values()),
        lambda rows: any(row["syntax_ok"] for row in rows[:k]),
    )
    proven_at_1 = rate(first_round_rows, formal_success) if formal_mode else 0.0
    proven_at_k = (
        rate(
            list(first_by_case.values()),
            lambda rows: any(formal_success(row) for row in rows[:k]),
        )
        if formal_mode
        else 0.0
    )
    non_vacuous_at_k = (
        rate(
            list(first_by_case.values()),
            lambda rows: any(
                row["proof_metadata"].get("vacuity_status") != "vacuous" and formal_success(row)
                for row in rows[:k]
            ),
        )
        if formal_mode
        else 0.0
    )
    antecedent_reachable_at_1 = (
        rate(first_round_rows, antecedent_reachable_row) if formal_mode else 0.0
    )
    antecedent_reachable_at_k = (
        rate(
            list(first_by_case.values()),
            lambda rows: any(antecedent_reachable_row(row) for row in rows[:k]),
        )
        if formal_mode
        else 0.0
    )
    cover_reachable_at_k = (
        rate(
            list(first_by_case.values()),
            lambda rows: any(cover_reachable_row(row) for row in rows[:k]),
        )
        if formal_mode
        else 0.0
    )
    proven_non_vacuous_at_k = (
        rate(
            list(final_by_case.values()),
            lambda rows: any(formal_success(row) for row in rows[:k]),
        )
        if formal_mode
        else 0.0
    )
    reference_proven_at_1 = (
        rate(reference_audits, lambda audit: bool(audit.get("reference_proven")))
        if formal_mode
        else 0.0
    )
    reference_non_vacuous_at_1 = (
        rate(reference_audits, lambda audit: bool(audit.get("reference_non_vacuous")))
        if formal_mode
        else 0.0
    )
    reference_antecedent_reachable_at_1 = (
        rate(reference_audits, lambda audit: bool(audit.get("reference_antecedent_reachable")))
        if formal_mode
        else 0.0
    )
    harness_status_counts = dict(
        sorted(
            collections.Counter(
                str(audit.get("harness_reachability_status") or "unknown")
                for audit in reference_audits
            ).items()
        )
    )
    root_cause_counts = summarize_root_cause_counts(all_rows)
    root_cause_detail_counts = dict(
        sorted(
            collections.Counter(
                str(row.get("root_cause_detail") or "unknown") for row in all_rows
            ).items()
        )
    )
    failure_by_design_counts = nested_failure_counts(all_rows, "design_id")
    failure_by_property_type_counts = nested_failure_counts(all_rows, "property_type")
    backend_status_counts = dict(
        sorted(
            collections.Counter(
                str((row.get("proof_metadata") or {}).get("status") or "unknown")
                for row in all_rows
            ).items()
        )
    )
    backend_blocked = bool(all_rows) and all(
        str((row.get("proof_metadata") or {}).get("status") or "").lower() == "blocked"
        for row in all_rows
    )
    wrapper_parity_rows = [
        row for row in all_rows if str(row.get("source") or "") == "reference_oracle"
    ]
    wrapper_parity_pass_rate = (
        rate(wrapper_parity_rows, lambda row: bool(row.get("wrapper_parity_pass")))
        if formal_mode
        else 0.0
    )
    successes_after_feedback = [
        row_success(row, formal_mode=formal_mode)
        for row in repair_rows
        if int(row["round"]) > 0
    ]
    return {
        "num_cases": len(results),
        "k": k,
        "cases_by_design": dict(
            sorted(collections.Counter(result["design_id"] for result in results).items())
        ),
        "syntax@1": syntax_at_1,
        "syntax@k": syntax_at_k,
        "proven@1": proven_at_1,
        "proven@k": proven_at_k,
        "non_vacuous@k": non_vacuous_at_k,
        "antecedent_reachable@1": antecedent_reachable_at_1,
        "antecedent_reachable@k": antecedent_reachable_at_k,
        "cover_reachable@k": cover_reachable_at_k,
        "proven_non_vacuous@k": proven_non_vacuous_at_k,
        "reference_proven@1": reference_proven_at_1,
        "reference_non_vacuous@1": reference_non_vacuous_at_1,
        "reference_antecedent_reachable@1": reference_antecedent_reachable_at_1,
        "wrapper_parity_pass_rate": wrapper_parity_pass_rate,
        "harness_reachability_status": aggregate_harness_reachability_status(
            harness_status_counts
        ),
        "harness_reachability_status_counts": harness_status_counts,
        "formal_metrics_status": formal_metrics_status(
            formal_mode,
            jasper_replay,
            backend_blocked=backend_blocked,
        ),
        "backend_status_counts": backend_status_counts,
        "hallucinated_signal_rate": rate(
            all_initial_rows,
            lambda row: row["has_hallucinated_signal"],
        ),
        "fallback_rate": rate(
            all_initial_rows,
            lambda row: row["source"] == "structured_fallback",
        ),
        "valid_json_rate": rate(all_initial_rows, lambda row: row["valid_json"]),
        "real_llm_count": sum(1 for row in all_initial_rows if row["source"] == "llm"),
        "candidate_count_by_case": dict(
            sorted(collections.Counter(row["case_id"] for row in all_initial_rows).items())
        ),
        "average_rounds": (
            sum(
                int(path["final_metrics"]["round"])
                for result in results
                for path in result["candidate_paths"]
            )
            / max(1, sum(len(result["candidate_paths"]) for result in results))
        ),
        "repair_success_after_feedback": (
            sum(1 for success in successes_after_feedback if success)
            / len(successes_after_feedback)
            if successes_after_feedback
            else 0.0
        ),
        "repaired_non_vacuous_success_after_feedback": (
            rate(repair_rows, formal_success) if formal_mode and repair_rows else 0.0
        ),
        "source_counts": dict(
            sorted(collections.Counter(row["source"] for row in all_initial_rows).items())
        ),
        "failure_categories": dict(
            sorted(collections.Counter(row["failure_category"] for row in all_rows).items())
        ),
        "root_cause_candidates": root_cause_counts,
        "root_cause_details": root_cause_detail_counts,
        "root_cause_candidate_counts": root_cause_counts,
        "root_cause_detail_counts": root_cause_detail_counts,
        "failure_by_design_counts": failure_by_design_counts,
        "failure_by_property_type_counts": failure_by_property_type_counts,
        "failure_taxonomy": sorted(DESIGN2SVA_FAILURE_TAXONOMY),
        "root_cause_taxonomy": sorted(ROOT_CAUSE_LABELS),
        "rows": all_rows,
    }


def render_markdown(summary: dict[str, Any], mode: str) -> str:
    return f"""# Design2SVA Results

## Summary

Mode: `{mode}`

| Metric | Value |
| --- | ---: |
| Cases | {summary["num_cases"]} |
| k | {summary["k"]} |
| syntax@1 | {summary["syntax@1"]:.3f} |
| syntax@k | {summary["syntax@k"]:.3f} |
| proven@1 | {summary["proven@1"]:.3f} |
| proven@k | {summary["proven@k"]:.3f} |
| non_vacuous@k | {summary["non_vacuous@k"]:.3f} |
| antecedent_reachable@1 | {summary["antecedent_reachable@1"]:.3f} |
| antecedent_reachable@k | {summary["antecedent_reachable@k"]:.3f} |
| cover_reachable@k | {summary["cover_reachable@k"]:.3f} |
| proven_non_vacuous@k | {summary["proven_non_vacuous@k"]:.3f} |
| reference_proven@1 | {summary["reference_proven@1"]:.3f} |
| reference_non_vacuous@1 | {summary["reference_non_vacuous@1"]:.3f} |
| reference_antecedent_reachable@1 | {summary["reference_antecedent_reachable@1"]:.3f} |
| wrapper_parity_pass_rate | {summary["wrapper_parity_pass_rate"]:.3f} |
| harness_reachability_status | {summary["harness_reachability_status"]} |
| root_cause_candidates | {format_counts(summary["root_cause_candidates"])} |
| root_cause_details | {format_counts(summary["root_cause_details"])} |
| Hallucinated signal rate | {summary["hallucinated_signal_rate"]:.3f} |
| Fallback rate | {summary["fallback_rate"]:.3f} |
| Valid JSON rate | {summary["valid_json_rate"]:.3f} |
| Average rounds | {summary["average_rounds"]:.3f} |
| Repair success after feedback | {summary["repair_success_after_feedback"]:.3f} |
| Repaired proven_non_vacuous | {summary["repaired_non_vacuous_success_after_feedback"]:.3f} |

Formal metrics status: `{summary["formal_metrics_status"]}`.

## Boundaries

- Dry-run and replay rows validate local infrastructure and JSON contracts.
- They are not production signoff.
- `proven@*` and `non_vacuous@k` remain `0.000` with status `not_run`
  unless real JasperGold checks are explicitly enabled and available.
- Exact/reference agreement is a local scaffold signal, not semantic equivalence.
- Stage 11/12 root-cause labels are diagnostic candidates, not a claim that
  Design2SVA generation succeeded.
"""


def group_initial_by_case(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        grouped[str(row["case_id"])].append(row)
    return grouped


def property_type_from_antecedent_metadata(antecedent_metadata: dict[str, Any]) -> str:
    trigger_kind = str(
        antecedent_metadata.get("trigger_kind")
        or antecedent_metadata.get("antecedent_kind")
        or "unknown"
    )
    if trigger_kind == "antecedent":
        return "implication"
    if trigger_kind == "invariant":
        return "invariant"
    return trigger_kind or "unknown"


def nested_failure_counts(rows: list[dict[str, Any]], group_key: str) -> dict[str, dict[str, int]]:
    grouped: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for row in rows:
        group = str(row.get(group_key) or "unknown")
        grouped[group][str(row.get("failure_category") or "unknown")] += 1
    return {
        group: dict(sorted(counter.items()))
        for group, counter in sorted(grouped.items())
    }


def rate(rows: list[Any], predicate) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if predicate(row)) / len(rows)


def formal_metrics_status(
    formal_mode: bool,
    jasper_replay: bool,
    *,
    backend_blocked: bool = False,
) -> str:
    if jasper_replay:
        return "replayed"
    if backend_blocked:
        return "blocked"
    return "measured" if formal_mode else "not_run"


def aggregate_harness_reachability_status(counts: dict[str, int]) -> str:
    if not counts:
        return "not_run"
    nonzero = {status for status, count in counts.items() if count > 0}
    if not nonzero:
        return "not_run"
    if len(nonzero) == 1:
        return next(iter(nonzero))
    if "unreachable" in nonzero:
        return "unreachable"
    if "syntax_error" in nonzero:
        return "syntax_error"
    if nonzero <= {"not_run", "unknown"}:
        return "not_run" if "not_run" in nonzero else "unknown"
    return "mixed"


def classify_root_cause_candidate(
    metrics: dict[str, Any],
    native_oracle: dict[str, Any] | None,
) -> str:
    if external_root_cause_classifier is not None:
        label = external_root_cause_classifier(metrics, native_oracle=native_oracle)
        if label in ROOT_CAUSE_LABELS:
            return str(label)

    proof = metrics.get("proof_metadata", {})
    antecedent = metrics.get("antecedent_metadata", {})
    failure = str(metrics.get("failure_category") or "")
    source = str(metrics.get("source") or "")
    native = native_oracle or {}
    native_status = str(native.get("native_proof_status") or "").lower()
    native_proves = native.get("native_reference_proves")
    native_unreachable = native_status in {"unreachable", "uncovered"} or str(
        native.get("root_cause_candidate") or ""
    ) == "native_harness_unreachable"

    if metrics.get("reset_clock_mismatch") or reset_clock_diagnostic_mismatch(metrics):
        return "reset_clock_mismatch"
    if invariant_misclassified_as_unreachable(metrics):
        return "cover_generation_bug"
    if parser_status_contradiction(proof):
        return "jasper_parser_misclassification"
    if native_proves is False and native_unreachable:
        return "native_harness_unreachable"
    if native_proves is False:
        return "reference_task_invalid"
    if native_proves is True and source == "reference_oracle" and failure not in {
        "proven_non_vacuous",
        "not_run",
    }:
        return "design2sva_embedding_bug"
    if native_proves is True and source != "reference_oracle" and failure not in {
        "proven_non_vacuous",
        "not_run",
    }:
        return "candidate_generation_failure"
    if str(antecedent.get("extraction_status") or "").lower() == "unknown" and failure.startswith(
        "unreachable"
    ):
        return "cover_generation_bug"
    return "unknown"


def classify_root_cause_detail(
    metrics: dict[str, Any],
    native_oracle: dict[str, Any] | None,
) -> str:
    native = native_oracle or {}
    source = str(metrics.get("source") or "")
    failure = str(metrics.get("failure_category") or "")
    proof = metrics.get("proof_metadata") if isinstance(metrics.get("proof_metadata"), dict) else {}
    antecedent = (
        metrics.get("antecedent_metadata")
        if isinstance(metrics.get("antecedent_metadata"), dict)
        else {}
    )
    backend_detail = embedding_audit_root_cause_detail(metrics)

    if source == "reference_oracle" and wrapper_parity_pass(metrics, native_oracle):
        return "reference_oracle_matches_native_formal_behavior"
    if failure == "backend_blocked":
        return "formal_backend_blocked"
    if metrics.get("reset_clock_mismatch") or reset_clock_diagnostic_mismatch(metrics):
        return "clock_or_reset_contract_differs_from_native"
    if failure == "not_run":
        return "formal_check_not_run"
    if invariant_misclassified_as_unreachable(metrics):
        return "invariant_assertion_reported_unreachable_without_antecedent_cover_obligation"
    if native.get("native_reference_proves") is True and source == "reference_oracle":
        proof_status = str(proof.get("proof_status") or "").lower()
        reachability = str(antecedent.get("antecedent_reachability") or "").lower()
        if proof_status in {"unreachable", "uncovered"}:
            return "native_reference_proves_but_wrapper_reports_reference_unreachable"
        if reachability == "unreachable":
            return "native_reference_proves_but_wrapper_antecedent_cover_unreachable"
        if failure not in {"proven_non_vacuous", "not_run"}:
            return "native_reference_proves_but_wrapper_reference_fails"
    if failure == "unreachable_antecedent":
        return "generated_implication_antecedent_unreachable"
    if failure == "unreachable_cover_goal":
        return "generated_cover_goal_unreachable"
    if failure == "proven_non_vacuous":
        return "assertion_proven_non_vacuous"
    if backend_detail and not backend_detail.startswith("wrapper_reuses_native_harness"):
        return backend_detail
    return failure or "unknown"


def embedding_audit_root_cause_detail(metrics: dict[str, Any]) -> str:
    audit = metrics.get("embedding_audit")
    if not isinstance(audit, dict):
        return ""
    backend_audit = audit.get("backend_audit")
    if isinstance(backend_audit, dict):
        detail = backend_audit.get("root_cause_detail")
        if isinstance(detail, str) and detail:
            return detail
    detail = audit.get("root_cause_detail")
    return detail if isinstance(detail, str) else ""


def wrapper_parity_pass(
    metrics: dict[str, Any],
    native_oracle: dict[str, Any] | None,
) -> bool:
    if str(metrics.get("source") or "") != "reference_oracle":
        return False
    native = native_oracle or {}
    native_proves = native.get("native_reference_proves")
    if native_proves is False:
        return False
    return formal_success(metrics)


def reset_clock_diagnostic_mismatch(metrics: dict[str, Any]) -> bool:
    diagnostics = metrics.get("clock_reset_diagnostics")
    if not isinstance(diagnostics, dict):
        return False
    status = str(diagnostics.get("status") or "").lower()
    return status in {"reset_clock_mismatch", "clock_reset_mismatch"}


def invariant_misclassified_as_unreachable(metrics: dict[str, Any]) -> bool:
    antecedent = metrics.get("antecedent_metadata")
    if not isinstance(antecedent, dict):
        return False
    if requires_antecedent_cover(antecedent):
        return False
    proof_status = str((metrics.get("proof_metadata") or {}).get("proof_status") or "").lower()
    return proof_status in {"unreachable", "uncovered"} or antecedent_unreachable(antecedent)


def parser_status_contradiction(proof: dict[str, Any]) -> bool:
    status = str(proof.get("status") or "").lower()
    syntax_status = str(proof.get("syntax_status") or "").lower()
    proof_status = str(proof.get("proof_status") or "").lower()
    if syntax_status == "syntax_error" and proof_status in {"proven", "covered"}:
        return True
    return status == "passed" and proof_status in {"unreachable", "uncovered"}


def summarize_root_cause_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    if external_root_cause_summary is not None:
        summary = external_root_cause_summary(rows)
        if isinstance(summary, dict):
            return dict(sorted((str(key), int(value)) for key, value in summary.items()))
    return dict(
        sorted(
            collections.Counter(
                str(row.get("root_cause_candidate") or "unknown") for row in rows
            ).items()
        )
    )


def format_counts(counts: dict[str, Any]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def formal_success(row: dict[str, Any]) -> bool:
    proof = row.get("proof_metadata", {})
    proof_status = str(proof.get("proof_status") or "").lower()
    vacuity_status = str(proof.get("vacuity_status") or "").lower()
    if proof_status != "proven" or vacuity_status == "vacuous":
        return False
    metadata = row.get("antecedent_metadata")
    if isinstance(metadata, dict) and not requires_antecedent_cover(metadata):
        return True
    return antecedent_reachable_row(row)


def row_sva_usable_for_rtl_triage(row: dict[str, Any]) -> bool:
    return (
        bool(row.get("valid_json"))
        and bool(row.get("syntax_ok"))
        and not bool(row.get("has_hallucinated_signal"))
        and not bool(row.get("unsupported_helper_code_issue"))
        and not bool(row.get("reset_clock_mismatch"))
        and (formal_success(row) or falsified_with_reachable_cex(row))
    )


def falsified_with_reachable_cex(row: dict[str, Any]) -> bool:
    proof = row.get("proof_metadata", {})
    if not isinstance(proof, dict):
        return False
    syntax_status = str(proof.get("syntax_status") or "").lower()
    proof_status = str(proof.get("proof_status") or "").lower()
    if syntax_status in {"syntax_error", "failed", "error"}:
        return False
    if proof_status not in {"falsified", "cex", "failed", "fail"}:
        return False
    return bool(row.get("antecedent_reachable") is True or antecedent_reachable_row(row))


def antecedent_reachable_row(row: dict[str, Any]) -> bool:
    metadata = row.get("antecedent_metadata")
    return isinstance(metadata, dict) and antecedent_reachable(metadata)


def cover_reachable_row(row: dict[str, Any]) -> bool:
    metadata = row.get("antecedent_metadata")
    if not isinstance(metadata, dict):
        return False
    return str(metadata.get("cover_status") or "").lower() in {"covered", "proven", "reachable"}


def requires_antecedent_cover(metadata: dict[str, Any]) -> bool:
    extraction_status = str(metadata.get("extraction_status") or "").lower()
    trigger_kind = str(
        metadata.get("trigger_kind")
        or metadata.get("condition_kind")
        or metadata.get("trigger_condition_kind")
        or ""
    ).lower()
    if trigger_kind in {"invariant", "no_antecedent", "invariant/no_antecedent"}:
        return False
    if extraction_status in {"invariant", "no_antecedent", "invariant/no_antecedent"}:
        return False
    if metadata.get("cover_sva") in {None, ""} and extraction_status != "extracted":
        return False
    return extraction_status == "extracted" or trigger_kind == "antecedent"


def default_proof_metadata(backend: str = "jaspergold") -> dict[str, Any]:
    return {
        "backend": backend,
        "status": "not_run",
        "syntax_status": "not_run",
        "proof_status": None,
        "vacuity_status": None,
        "report_dir": None,
    }


def candidate_schema_proof_metadata(proof_metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "backend": str(proof_metadata.get("backend") or "jaspergold"),
        "status": str(proof_metadata.get("status") or "not_run"),
        "syntax_status": str(proof_metadata.get("syntax_status") or "not_run"),
        "proof_status": proof_metadata.get("proof_status"),
        "vacuity_status": proof_metadata.get("vacuity_status"),
        "report_dir": proof_metadata.get("report_dir"),
    }


def proof_metadata_from_backend(backend_result: Any) -> dict[str, Any]:
    legacy = backend_result.to_legacy_check_dict()
    artifact_paths = backend_artifact_paths(backend_result)
    return {
        "backend": backend_result.backend,
        "status": backend_result.status.value,
        "syntax_status": backend_result.syntax_result.status.value,
        "proof_status": legacy.get("proof_status"),
        "vacuity_status": legacy.get("vacuity_status"),
        "report_dir": backend_result.report_dir,
        "artifact_paths": artifact_paths,
    }


def backend_artifact_paths(backend_result: Any | None) -> dict[str, Any]:
    if backend_result is None:
        return {}
    metadata = getattr(backend_result, "metadata", {}) or {}
    if isinstance(metadata, dict) and isinstance(metadata.get("artifact_paths"), dict):
        return dict(metadata["artifact_paths"])
    return {
        "report_dir": getattr(backend_result, "report_dir", None),
        "raw_reports": getattr(backend_result, "raw_report_paths", {}),
        "logs": getattr(backend_result, "raw_log_paths", []),
        "counterexamples": getattr(backend_result, "counterexample_paths", []),
    }


def build_embedding_audit(
    case: dict[str, Any],
    candidate: dict[str, Any],
    antecedent_metadata: dict[str, Any],
    assertion_backend_result: Any | None,
    cover_backend_result: Any | None,
) -> dict[str, Any]:
    assertion_artifacts = backend_artifact_paths(assertion_backend_result)
    cover_artifacts = backend_artifact_paths(cover_backend_result)
    metadata = getattr(assertion_backend_result, "metadata", {}) or {}
    backend_audit = metadata.get("embedding_audit", {}) if isinstance(metadata, dict) else {}
    return {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": candidate.get("property_id") or case["property_id"],
        "native_property_expression": native_property_expression(case),
        "reference_sva": reference_sva(case),
        "candidate_sva": str(candidate.get("sva", "")),
        "cover_before_assert_sva": antecedent_metadata.get("cover_sva") or "",
        "artifact_paths": {
            "assertion": assertion_artifacts,
            "cover_before_assert": cover_artifacts,
        },
        "checks": build_embedding_checks(case, candidate, antecedent_metadata, backend_audit),
        "backend_audit": backend_audit if isinstance(backend_audit, dict) else {},
    }


def native_property_expression(case: dict[str, Any]) -> str:
    return reference_sva(case)


def build_embedding_checks(
    case: dict[str, Any],
    candidate: dict[str, Any],
    antecedent_metadata: dict[str, Any],
    backend_audit: Any,
) -> dict[str, Any]:
    sva = str(candidate.get("sva", ""))
    property_id = str(candidate.get("property_id") or case["property_id"])
    helper_code = str(candidate.get("helper_code") or "")
    labels = extract_sva_labels(sva)
    if isinstance(backend_audit, dict) and isinstance(backend_audit.get("checks"), dict):
        checks = dict(backend_audit["checks"])
    else:
        checks = {}
    checks.update(
        {
            "label_collision": labels.count(property_id) > 1,
            "wrong_top_module": False,
            "missing_bind_or_instantiation": False,
            "wrong_include_path": False,
            "clock_reset_mismatch": reset_clock_mismatch(case, sva),
            "disable_iff_mismatch": disable_iff_mismatch(case, sva),
            "helper_code_placement_issue": helper_code_disallowed(case, helper_code),
            "cover_generated": bool(antecedent_metadata.get("cover_sva")),
        }
    )
    return checks


def extract_sva_labels(sva: str) -> list[str]:
    labels = []
    for line in sva.splitlines():
        prefix = line.split(":", 1)[0].strip()
        if (
            prefix
            and " " not in prefix
            and "\t" not in prefix
            and line.strip().startswith(prefix + ":")
        ):
            labels.append(prefix)
    return labels


def disable_iff_mismatch(case: dict[str, Any], sva: str) -> bool:
    clock_reset = case.get("clock_reset", {})
    if not isinstance(clock_reset, dict):
        return False
    reset = str(clock_reset.get("reset") or "")
    if not reset or "disable iff" not in sva:
        return False
    polarity = str(clock_reset.get("reset_polarity") or "unknown")
    expected = f"disable iff (!{reset})" if polarity == "active_low" else f"disable iff ({reset})"
    return expected not in sva


def proof_status_is_proven(proof_metadata: dict[str, Any]) -> bool:
    return str(proof_metadata.get("proof_status") or "").lower() == "proven"


def proof_not_vacuous(proof_metadata: dict[str, Any]) -> bool:
    return str(proof_metadata.get("vacuity_status") or "").lower() != "vacuous"


def harness_reachability_status(antecedent_metadata: dict[str, Any]) -> str:
    reachability = str(antecedent_metadata.get("antecedent_reachability") or "").lower()
    if reachability in {"reachable", "unreachable"}:
        return reachability
    cover_status = str(antecedent_metadata.get("cover_status") or "").lower()
    if cover_status in {"not_run", "dry_run", "none", ""}:
        return "not_run"
    if cover_status in {"uncovered", "not_covered", "bounded_uncovered"}:
        return "bounded_uncovered"
    if cover_status in {"syntax_error", "syntax_failed", "parse_error", "elaboration_error"}:
        return "syntax_error"
    return "unknown"


def clock_reset_metadata(case: dict[str, Any]) -> dict[str, Any]:
    clock_reset = case.get("clock_reset", {})
    if not isinstance(clock_reset, dict):
        clock_reset = {}
    return {
        "clock": str(clock_reset.get("clock") or ""),
        "clock_edge": str(clock_reset.get("clock_edge") or ""),
        "reset": str(clock_reset.get("reset") or ""),
        "reset_polarity": str(clock_reset.get("reset_polarity") or ""),
        "module_name": str(case.get("module_name") or case.get("design_id") or ""),
        "harness_header_path": str(case.get("harness_header_path") or ""),
        "design_rtl_path": str(case.get("design_rtl_path") or ""),
    }


def build_clock_reset_diagnostics(
    case: dict[str, Any],
    jasper_check: bool,
    jasper_dry_run: bool,
    jasper_replay_records: list[dict[str, Any]] | None,
    jasper_out_root: Path,
    candidate_index: int,
    round_index: int,
    run_checks: bool,
) -> dict[str, Any]:
    if external_harness_diagnostics is not None:
        metadata = external_harness_diagnostics(case)
    else:
        metadata = fallback_harness_diagnostics(case)
    if not isinstance(metadata, dict):
        metadata = fallback_harness_diagnostics(case)

    predictions = (
        external_diagnostic_cover_predictions(case)
        if external_diagnostic_cover_predictions is not None
        else fallback_diagnostic_cover_predictions(case)
    )
    if not isinstance(predictions, list):
        predictions = []
    metadata["cover_checks"] = predictions

    if not (run_checks and jasper_check and jasper_replay_records is None):
        return metadata

    check_results = []
    for check_index, prediction in enumerate(predictions):
        backend_result = jasper_backend().check_generated_sva(
            case=legacy_case_shape(case),
            prediction=prediction,
            system=(
                f"design2sva_c{candidate_index}_r{round_index}"
                f"_harness_diag_{check_index}"
            ),
            out_root=jasper_out_root,
            dry_run=jasper_dry_run,
        )
        proof = proof_metadata_from_backend(backend_result)
        check_results.append(
            {
                "property_id": prediction.get("property_id"),
                "proof_metadata": proof,
                "artifact_paths": proof.get("artifact_paths", {}),
            }
        )
    metadata["check_results"] = check_results
    apply_harness_check_statuses(metadata, check_results)
    return metadata


def fallback_harness_diagnostics(case: dict[str, Any]) -> dict[str, Any]:
    clock_reset = case.get("clock_reset", {})
    if not isinstance(clock_reset, dict):
        clock_reset = {}
    reset = str(clock_reset.get("reset") or "")
    polarity = str(clock_reset.get("reset_polarity") or "unknown")
    return {
        "reset_release_reachable": "not_run",
        "post_reset_reachable": "not_run",
        "clock_event_assumed": bool(clock_reset.get("clock")),
        "reset_polarity_used": polarity,
        "disable_iff_used": disable_iff_for_case(case),
        "clock": str(clock_reset.get("clock") or ""),
        "reset": reset,
        "status": "not_run",
    }


def fallback_diagnostic_cover_predictions(case: dict[str, Any]) -> list[dict[str, Any]]:
    clock_reset = case.get("clock_reset", {})
    if not isinstance(clock_reset, dict):
        clock_reset = {}
    clock = str(clock_reset.get("clock") or "clk")
    reset = str(clock_reset.get("reset") or "")
    disable_iff = disable_iff_for_case(case)
    timing = f"@(posedge {clock})"
    suffix = str(case["property_id"])
    visible_non_reset = [
        str(signal)
        for signal in case.get("visible_signals", [])
        if str(signal) not in {clock, reset}
    ]
    non_reset_expr = " || ".join(visible_non_reset[:3]) if visible_non_reset else "1'b1"
    released = reset_release_expr(reset, str(clock_reset.get("reset_polarity") or "unknown"))
    checks = [
        ("reset_release", released),
        ("post_reset_cycle", "1'b1"),
        ("clock_advance", "1'b1"),
        ("visible_non_reset_value", f"({non_reset_expr})"),
    ]
    predictions = []
    for name, expr in checks:
        prop_id = f"cov_{suffix}_{name}"
        body = f"{timing} {disable_iff} ({expr})" if disable_iff else f"{timing} ({expr})"
        predictions.append(
            {
                "property_id": prop_id,
                "sva": f"{prop_id}: cover property ({body});",
                "helper_code": "",
            }
        )
    return predictions


def disable_iff_for_case(case: dict[str, Any]) -> str:
    clock_reset = case.get("clock_reset", {})
    if not isinstance(clock_reset, dict):
        return ""
    reset = str(clock_reset.get("reset") or "")
    if not reset:
        return ""
    reset_expr = (
        f"!{reset}"
        if str(clock_reset.get("reset_polarity") or "unknown") == "active_low"
        else reset
    )
    return f"disable iff ({reset_expr})"


def reset_release_expr(reset: str, polarity: str) -> str:
    if not reset:
        return "1'b1"
    return reset if polarity == "active_low" else f"!{reset}"


def apply_harness_check_statuses(
    metadata: dict[str, Any],
    check_results: list[dict[str, Any]],
) -> None:
    statuses = {
        str(item.get("property_id") or ""): str(
            (item.get("proof_metadata") or {}).get("proof_status") or ""
        ).lower()
        for item in check_results
    }
    for field, token in [
        ("reset_release_reachable", "reset_release"),
        ("post_reset_reachable", "post_reset_cycle"),
    ]:
        matched = next((status for name, status in statuses.items() if token in name), "")
        if matched:
            metadata[field] = "reachable" if matched in {"covered", "proven"} else matched


def replay_proof_metadata(
    records: list[dict[str, Any]],
    case: dict[str, Any],
    candidate_index: int,
    round_index: int,
    check_kind: str,
    default_backend: str,
) -> dict[str, Any]:
    record = replay_check_record(records, case, candidate_index, round_index, check_kind)
    proof = record.get("proof_metadata", {}) if isinstance(record, dict) else {}
    if isinstance(record, dict) and isinstance(record.get("check"), dict):
        proof = record["check"].get("proof_metadata", proof)
    if not isinstance(proof, dict):
        proof = {}
    return {
        "backend": str(proof.get("backend") or default_backend),
        "status": str(proof.get("status") or "not_run"),
        "syntax_status": str(proof.get("syntax_status") or "not_run"),
        "proof_status": proof.get("proof_status"),
        "vacuity_status": proof.get("vacuity_status"),
        "report_dir": proof.get("report_dir"),
    }


def replay_check_record(
    records: list[dict[str, Any]],
    case: dict[str, Any],
    candidate_index: int,
    round_index: int,
    check_kind: str,
) -> dict[str, Any]:
    for record in records:
        if not isinstance(record, dict):
            continue
        if not replay_case_matches(record, case):
            continue
        if str(record.get("check_kind") or "assertion") != check_kind:
            continue
        if int(record.get("candidate_index", candidate_index)) != candidate_index:
            continue
        if int(record.get("round", 0)) != round_index:
            continue
        if "proof_metadata" in record or isinstance(record.get("check"), dict):
            return record
    return {}


def replay_candidate_for_round(
    case: dict[str, Any],
    records: list[dict[str, Any]] | None,
    candidate_index: int,
    round_index: int,
) -> dict[str, Any] | None:
    if records is None:
        return None
    for record in records:
        if not isinstance(record, dict) or not replay_case_matches(record, case):
            continue
        if int(record.get("candidate_index", candidate_index)) != candidate_index:
            continue
        if int(record.get("round", 0)) != round_index:
            continue
        response = record.get("response")
        if isinstance(response, dict):
            return dict(response)
    return None


def replay_case_matches(record: dict[str, Any], case: dict[str, Any]) -> bool:
    return str(record.get("case_id", "")) == str(case["case_id"]) and str(
        record.get("property_id", case["property_id"])
    ) == str(case["property_id"])


def row_success(row: dict[str, Any], formal_mode: bool) -> bool:
    if formal_mode:
        return formal_success(row)
    proof = row.get("proof_metadata", {})
    if str(proof.get("proof_status") or "").lower() in {"unreachable", "uncovered"}:
        return False
    return (
        row["valid_json"]
        and row["syntax_ok"]
        and not row["has_hallucinated_signal"]
        and not row["reset_clock_mismatch"]
        and not row["unsupported_helper_code_issue"]
        and row["exact_match"] is not False
    )


def allowed_identifiers(case: dict[str, Any], context: dict[str, Any]) -> set[str]:
    allowed = {str(signal) for signal in case.get("visible_signals", [])}
    allowed.update(str(signal) for signal in context.get("visible_signals", []))
    allowed.add(str(case["property_id"]))
    return allowed


def helper_code_disallowed(case: dict[str, Any], helper_code: str) -> bool:
    policy = case.get("helper_code_policy", {})
    allowed = bool(policy.get("allowed")) if isinstance(policy, dict) else False
    return bool(helper_code.strip()) and not allowed


def reset_clock_mismatch(case: dict[str, Any], sva: str) -> bool:
    clock_reset = case.get("clock_reset", {})
    if not isinstance(clock_reset, dict):
        return False
    clock = str(clock_reset.get("clock") or "")
    reset = str(clock_reset.get("reset") or "")
    polarity = str(clock_reset.get("reset_polarity") or "unknown")
    if clock and f"@(posedge {clock})" not in sva:
        return True
    if "disable iff" not in sva or not reset:
        return False
    expected = f"disable iff (!{reset})" if polarity == "active_low" else f"disable iff ({reset})"
    return expected not in sva


def reference_sva(case: dict[str, Any]) -> str:
    metadata = case.get("evaluation_metadata", {})
    if isinstance(metadata, dict):
        return str(metadata.get("reference_sva") or "")
    return ""


def legacy_case_shape(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": case["property_id"],
        "clock": case["clock_reset"]["clock"],
        "reset": case["clock_reset"].get("reset"),
        "signals": list(case.get("visible_signals", [])),
        "intent": case["intent"],
        "reference_sva": reference_sva(case),
    }


def run_mode(args: argparse.Namespace) -> str:
    if args.reference_oracle:
        return "reference_oracle"
    if args.replay:
        return "replay"
    if args.llm:
        return "real_llm"
    return "deterministic_scaffold"


def formal_check_mode(
    args: argparse.Namespace,
    jasper_replay_records: list[dict[str, Any]] | None,
) -> str:
    if jasper_replay_records is not None:
        return "replay"
    if args.jasper_check:
        return "jasper"
    return "not_run"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--max-repair-rounds", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--reference-oracle",
        action="store_true",
        help="Evaluate local evaluation_metadata.reference_sva without invoking generation.",
    )
    parser.add_argument("--replay", nargs="?", const=DEFAULT_REPLAY_PATH, type=Path)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--repair-with-llm", action="store_true")
    parser.add_argument("--repair-llm-command")
    parser.add_argument("--jasper-check", action="store_true")
    parser.add_argument("--jasper-replay", nargs="?", const=DEFAULT_JASPER_REPLAY_PATH, type=Path)
    parser.add_argument("--jasper-out-root", type=Path, default=Path("jasper/reports/design2sva"))
    parser.add_argument(
        "--native-oracle-results",
        nargs="?",
        const=DEFAULT_NATIVE_ORACLE_PATH,
        type=Path,
        help="Optional Stage 11 native-reference oracle JSON for root-cause labeling.",
    )
    parser.add_argument(
        "--harness-diagnostics",
        action="store_true",
        help="Run basic reset/post-reset cover checks through the Jasper wrapper.",
    )
    parser.add_argument(
        "--debug-artifacts",
        action="store_true",
        help=(
            "Accepted for Stage 11 Jasper runs. Generated wrapper and embedding "
            "audit artifacts are recorded in result rows."
        ),
    )
    parser.add_argument("--context-budget", type=int, default=24)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    replay_records = load_replay_records(resolve_repo_path(args.replay)) if args.replay else None
    jasper_replay_records = (
        load_replay_records(resolve_repo_path(args.jasper_replay)) if args.jasper_replay else None
    )
    native_oracle_results = load_native_oracle_results(args.native_oracle_results)
    jasper_dry_run = bool(args.dry_run)
    jasper_check = bool(args.jasper_check or jasper_replay_records is not None)
    results = [
        run_case(
            case=case,
            k=args.k,
            max_repair_rounds=args.max_repair_rounds,
            reference_oracle=args.reference_oracle,
            use_llm=bool(args.llm and not args.reference_oracle),
            llm_command=args.llm_command,
            repair_with_llm=bool(args.repair_with_llm and not args.reference_oracle),
            repair_llm_command=args.repair_llm_command,
            replay_records=None if args.reference_oracle else replay_records,
            jasper_check=jasper_check,
            jasper_dry_run=jasper_dry_run,
            jasper_replay_records=jasper_replay_records,
            jasper_out_root=resolve_repo_path(args.jasper_out_root),
            context_budget=args.context_budget,
            native_oracle=native_oracle_results.get(str(case["case_id"])),
            run_harness_diagnostics=bool(args.harness_diagnostics),
        )
        for case in cases
    ]
    summary = summarize(
        results,
        k=args.k,
        jasper_check=jasper_check,
        jasper_dry_run=jasper_dry_run,
        jasper_replay=jasper_replay_records is not None,
    )
    public_summary = {key: value for key, value in summary.items() if key != "rows"}
    payload = {
        "summary": public_summary,
        "mode": run_mode(args),
        "formal_check_mode": formal_check_mode(args, jasper_replay_records),
        "native_oracle_results": (
            str(args.native_oracle_results) if args.native_oracle_results else None
        ),
        "results": results,
    }
    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        markdown_path = resolve_repo_path(args.markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(summary, run_mode(args)), encoding="utf-8")
    print(json.dumps(public_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
