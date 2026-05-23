"""Root-cause classification for Design2SVA harness diagnostics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

NATIVE_HARNESS_UNREACHABLE = "native_harness_unreachable"
DESIGN2SVA_EMBEDDING_BUG = "design2sva_embedding_bug"
RESET_CLOCK_MISMATCH = "reset_clock_mismatch"
COVER_GENERATION_BUG = "cover_generation_bug"
REFERENCE_TASK_INVALID = "reference_task_invalid"
JASPER_PARSER_MISCLASSIFICATION = "jasper_parser_misclassification"
CANDIDATE_GENERATION_FAILURE = "candidate_generation_failure"
UNKNOWN = "unknown"

ROOT_CAUSE_LABELS = (
    NATIVE_HARNESS_UNREACHABLE,
    DESIGN2SVA_EMBEDDING_BUG,
    RESET_CLOCK_MISMATCH,
    COVER_GENERATION_BUG,
    REFERENCE_TASK_INVALID,
    JASPER_PARSER_MISCLASSIFICATION,
    CANDIDATE_GENERATION_FAILURE,
    UNKNOWN,
)
DESIGN2SVA_ROOT_CAUSE_LABELS = ROOT_CAUSE_LABELS
ROOT_CAUSE_CANDIDATES = ROOT_CAUSE_LABELS

_TRUE_TEXT = {"1", "true", "yes", "y", "on"}
_FALSE_TEXT = {"0", "false", "no", "n", "off"}
_PROVEN = {"proven", "passed", "pass"}
_COVERED = {"covered", "reachable", "hit"}
_FAILED_PROOF = {"falsified", "failed", "fail", "cex", "counterexample"}
_UNREACHABLE = {
    "unreachable",
    "uncovered",
    "not_covered",
    "cover_failed",
    "unhit",
    "missed",
    "bounded_uncovered",
    "vacuous",
}
_SYNTAX_OR_ERROR = {
    "syntax_error",
    "syntax_failed",
    "parse_error",
    "elaboration_error",
    "error",
}
_NOT_RUN = {"", "not_run", "dry_run", "none", "unknown"}
_REFERENCE_SOURCES = {
    "reference_oracle",
    "reference_embedding",
    "design2sva_reference_embedding",
    "native_reference",
    "fixture_reference",
}


def classify_root_cause_candidate(
    row: Mapping[str, Any],
    native_oracle: Mapping[str, Any] | None = None,
) -> str:
    """Return the Stage 11 root-cause candidate label for a Design2SVA row.

    ``row`` may be a metrics row, a round record containing ``metrics``, or any
    mapping that exposes the same status fields. ``native_oracle`` is optional
    reference/native proof information used to separate harness and embedding
    failures from ordinary candidate-generation failures.
    """

    metrics = _metrics_from(row)
    native = _native_from(row, native_oracle)

    if _backend_blocked(metrics):
        return UNKNOWN
    if native and _native_harness_unreachable(native):
        return NATIVE_HARNESS_UNREACHABLE
    if native and _native_reference_invalid(native):
        return REFERENCE_TASK_INVALID
    if (
        native
        and _native_proves_non_vacuously(native)
        and _is_reference_embedding_row(metrics)
        and _row_failed_or_unreachable(metrics)
    ):
        return DESIGN2SVA_EMBEDDING_BUG
    if _has_reset_clock_mismatch(metrics):
        return RESET_CLOCK_MISMATCH
    if _has_cover_generation_bug(metrics):
        return COVER_GENERATION_BUG
    if _has_jasper_parser_contradiction(metrics):
        return JASPER_PARSER_MISCLASSIFICATION
    if _ordinary_candidate_failed_after_harness_proves(metrics, native):
        return CANDIDATE_GENERATION_FAILURE
    return UNKNOWN


def summarize_root_cause_candidates(
    rows: Iterable[Mapping[str, Any]],
    native_oracle_by_case: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    include_zero: bool = False,
) -> dict[str, int]:
    """Count Stage 11 root-cause labels for a sequence of Design2SVA rows."""

    counts: Counter[str] = Counter()
    for row in rows:
        metrics = _metrics_from(row)
        native = None
        if native_oracle_by_case is not None:
            case_id = _first_present(metrics, row, keys=("case_id", "task_id", "property_id"))
            if case_id is not None:
                native = native_oracle_by_case.get(str(case_id))
        counts[classify_root_cause_candidate(row, native)] += 1

    if include_zero:
        return {label: counts.get(label, 0) for label in ROOT_CAUSE_LABELS}
    return {label: counts[label] for label in ROOT_CAUSE_LABELS if counts.get(label, 0)}


root_cause_counts = summarize_root_cause_candidates
classify_design2sva_root_cause = classify_root_cause_candidate
classify_design2sva_rootcause = classify_root_cause_candidate
classify_root_cause = classify_root_cause_candidate
summarize_root_cause_counts = summarize_root_cause_candidates


def _metrics_from(row: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("metrics", "final_metrics"):
        value = row.get(key)
        if isinstance(value, Mapping):
            return value
    return row


def _native_from(
    row: Mapping[str, Any],
    native_oracle: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    if native_oracle is not None:
        return native_oracle
    for key in (
        "native_oracle",
        "native_oracle_info",
        "native_harness_audit",
        "native_harness",
        "native_reference_audit",
        "native_reference_oracle",
    ):
        value = row.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _native_harness_unreachable(native: Mapping[str, Any]) -> bool:
    if _truthy(native.get("native_harness_unreachable")):
        return True
    status = _status(
        _first_present(
            native,
            keys=(
                "native_harness_reachability_status",
                "harness_reachability_status",
                "reachability_status",
                "native_status",
                "status",
            ),
        )
    )
    if status in {"unreachable", "bounded_uncovered", "vacuous"}:
        return True

    antecedent = _mapping(native.get("reference_antecedent_metadata")) or _mapping(
        native.get("antecedent_metadata")
    )
    if antecedent and _status(antecedent.get("antecedent_reachability")) == "unreachable":
        return True
    if antecedent and _status(antecedent.get("cover_status")) in _UNREACHABLE:
        return True

    proof = _proof_metadata(native)
    proof_status = _status(proof.get("proof_status") or native.get("native_proof_status"))
    vacuity_status = _status(proof.get("vacuity_status") or native.get("native_vacuity_status"))
    return proof_status == "unreachable" or vacuity_status == "vacuous"


def _native_reference_invalid(native: Mapping[str, Any]) -> bool:
    if _truthy(native.get("reference_task_invalid")) or _truthy(
        native.get("invalid_reference_task")
    ):
        return True
    if _explicit_false(native.get("reference_task_valid")):
        return True
    if _explicit_false(native.get("reference_available")):
        return True
    if _explicit_false(native.get("reference_syntax_ok")):
        return True
    if _truthy(native.get("reference_reset_clock_mismatch")):
        return True

    status = _status(
        _first_present(
            native,
            keys=("harness_reachability_status", "native_harness_reachability_status"),
        )
    )
    if status in _SYNTAX_OR_ERROR:
        return True

    proof = _proof_metadata(native)
    proof_status = _status(proof.get("proof_status") or native.get("native_proof_status"))
    syntax_status = _status(proof.get("syntax_status") or native.get("native_syntax_status"))
    overall_status = _status(native.get("native_status") or native.get("status"))
    if syntax_status in _SYNTAX_OR_ERROR or proof_status in _FAILED_PROOF:
        return True
    if overall_status in _FAILED_PROOF | _SYNTAX_OR_ERROR:
        return True
    if _explicit_false(native.get("reference_proven")):
        return status == "reachable" or proof_status not in _NOT_RUN | _UNREACHABLE
    return False


def _native_proves_non_vacuously(native: Mapping[str, Any]) -> bool:
    if _truthy(native.get("native_reference_proves")):
        return _status(native.get("native_vacuity_status")) != "vacuous"
    if _truthy(native.get("reference_non_vacuous")):
        return True
    if _explicit_false(native.get("reference_non_vacuous")):
        return False
    proof = _proof_metadata(native)
    proof_status = _status(
        proof.get("proof_status") or native.get("proof_status") or native.get("native_proof_status")
    )
    vacuity_status = _status(
        proof.get("vacuity_status")
        or native.get("vacuity_status")
        or native.get("native_vacuity_status")
    )
    if _truthy(native.get("reference_proven")):
        return vacuity_status != "vacuous" and not _explicit_false(
            native.get("reference_antecedent_reachable")
        )
    if proof_status not in _PROVEN:
        return False
    if vacuity_status == "vacuous":
        return False
    if _explicit_false(native.get("reference_antecedent_reachable")):
        return False
    reachability = _status(
        _first_present(
            native,
            keys=("harness_reachability_status", "native_harness_reachability_status"),
        )
    )
    if reachability in {"reachable", ""} | _NOT_RUN:
        return True
    return False


def _is_reference_embedding_row(metrics: Mapping[str, Any]) -> bool:
    source = _status(metrics.get("source"))
    if source in _REFERENCE_SOURCES:
        return True
    for key in ("is_reference_embedding", "reference_embedding", "design2sva_reference_embedding"):
        if _truthy(metrics.get(key)):
            return True
    mode = _status(metrics.get("mode") or metrics.get("run_mode") or metrics.get("system"))
    return mode in _REFERENCE_SOURCES


def _row_failed_or_unreachable(metrics: Mapping[str, Any]) -> bool:
    if _backend_blocked(metrics):
        return False
    if _row_proves_non_vacuously(metrics):
        return False
    if _row_unreachable(metrics):
        return True
    failure_category = _status(metrics.get("failure_category"))
    if failure_category and failure_category != "proven_non_vacuous":
        return True
    if _explicit_false(metrics.get("valid_json")) or _explicit_false(metrics.get("syntax_ok")):
        return True
    proof = _proof_metadata(metrics)
    proof_status = _status(proof.get("proof_status"))
    syntax_status = _status(proof.get("syntax_status"))
    return proof_status in _FAILED_PROOF or syntax_status in _SYNTAX_OR_ERROR


def _row_proves_non_vacuously(metrics: Mapping[str, Any]) -> bool:
    if _status(metrics.get("failure_category")) == "proven_non_vacuous":
        return True
    proof = _proof_metadata(metrics)
    proof_status = _status(proof.get("proof_status"))
    vacuity_status = _status(proof.get("vacuity_status"))
    if proof_status not in _PROVEN:
        return False
    if vacuity_status == "vacuous":
        return False
    return _antecedent_reachable(metrics) is not False


def _row_unreachable(metrics: Mapping[str, Any]) -> bool:
    failure_category = _status(metrics.get("failure_category"))
    if failure_category in {"unreachable_antecedent", "unreachable_cover_goal"}:
        return True
    antecedent = _mapping(metrics.get("antecedent_metadata"))
    if antecedent:
        if _status(antecedent.get("antecedent_reachability")) == "unreachable":
            return True
        if _status(antecedent.get("cover_status")) in _UNREACHABLE:
            return True
    proof = _proof_metadata(metrics)
    return _status(proof.get("proof_status")) in _UNREACHABLE


def _antecedent_reachable(metrics: Mapping[str, Any]) -> bool | None:
    value = metrics.get("antecedent_reachable")
    if _truthy(value):
        return True
    if _explicit_false(value):
        return False
    antecedent = _mapping(metrics.get("antecedent_metadata"))
    if not antecedent:
        return None
    reachability = _status(antecedent.get("antecedent_reachability"))
    if reachability == "reachable":
        return True
    if reachability == "unreachable":
        return False
    return None


def _has_reset_clock_mismatch(metrics: Mapping[str, Any]) -> bool:
    if _truthy(metrics.get("reset_clock_mismatch")):
        return True
    if _status(metrics.get("failure_category")) == "reset_clock_mismatch":
        return True
    return _has_diagnostic_text(metrics, ("reset_clock_mismatch", "reset/clock", "clock/reset"))


def _has_cover_generation_bug(metrics: Mapping[str, Any]) -> bool:
    if _truthy(metrics.get("cover_generation_bug")):
        return True
    if _status(metrics.get("failure_category")) == "unreachable_cover_goal":
        return True

    antecedent = _mapping(metrics.get("antecedent_metadata"))
    if antecedent:
        extraction_status = _status(antecedent.get("extraction_status"))
        cover_status = _status(antecedent.get("cover_status"))
        if extraction_status in {"unconditional", "approximated", "unknown"}:
            if cover_status in _UNREACHABLE | _SYNTAX_OR_ERROR:
                return True
            if _status(metrics.get("failure_category")) == "unreachable_antecedent":
                return True

    return _has_diagnostic_text(
        metrics,
        ("cover_generation_bug", "cover generation", "unreachable cover", "unreachable_cover"),
    )


def _has_jasper_parser_contradiction(metrics: Mapping[str, Any]) -> bool:
    if _truthy(metrics.get("jasper_parser_misclassification")):
        return True
    if _has_diagnostic_text(
        metrics,
        ("jasper_parser_misclassification", "parser contradiction", "status contradiction"),
    ):
        return True

    proof = _proof_metadata(metrics)
    backend_status = _status(proof.get("status") or metrics.get("status"))
    proof_status = _status(proof.get("proof_status") or metrics.get("proof_status"))
    syntax_status = _status(proof.get("syntax_status") or metrics.get("syntax_status"))
    vacuity_status = _status(proof.get("vacuity_status") or metrics.get("vacuity_status"))
    failure_category = _status(metrics.get("failure_category"))

    if syntax_status in _SYNTAX_OR_ERROR and proof_status in _PROVEN | _COVERED | _FAILED_PROOF:
        return True
    if backend_status in {"passed", "pass", "proven", "success"}:
        return proof_status in _FAILED_PROOF | _UNREACHABLE or vacuity_status == "vacuous"
    if backend_status in {"failed", "fail", "syntax_failed", "error"}:
        return proof_status in _PROVEN | _COVERED and vacuity_status != "vacuous"
    if failure_category == "proven_non_vacuous":
        return proof_status not in _PROVEN or vacuity_status == "vacuous"
    return False


def _ordinary_candidate_failed_after_harness_proves(
    metrics: Mapping[str, Any],
    native: Mapping[str, Any] | None,
) -> bool:
    if _backend_blocked(metrics):
        return False
    if _is_reference_embedding_row(metrics):
        return False
    harness_proves = (
        _native_proves_non_vacuously(native)
        if native is not None
        else _truthy(metrics.get("harness_proves"))
        or _truthy(metrics.get("reference_non_vacuous"))
        or _truthy(metrics.get("reference_proven_non_vacuous"))
    )
    return bool(harness_proves and _row_failed_or_unreachable(metrics))


def _proof_metadata(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("proof_metadata", "reference_proof_metadata", "native_proof_metadata"):
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return mapping


def _backend_blocked(metrics: Mapping[str, Any]) -> bool:
    proof = _proof_metadata(metrics)
    return _status(metrics.get("failure_category")) == "backend_blocked" or _status(
        proof.get("status") or metrics.get("status")
    ) == "blocked"


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _status(value) in _TRUE_TEXT


def _explicit_false(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    return _status(value) in _FALSE_TEXT


def _status(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if "." in text and text.rsplit(".", 1)[-1].isupper():
        text = text.rsplit(".", 1)[-1]
    return text.lower().replace("-", "_").replace(" ", "_")


def _first_present(*mappings: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if value is not None:
                return value
    return None


def _has_diagnostic_text(metrics: Mapping[str, Any], needles: tuple[str, ...]) -> bool:
    haystack = " ".join(
        str(value)
        for key, value in metrics.items()
        if key
        in {
            "diagnostic",
            "diagnostics",
            "feedback",
            "failure_category",
            "validation_error",
            "error",
            "errors",
            "reason",
            "root_cause_candidate",
        }
    ).lower()
    return any(needle in haystack for needle in needles)


__all__ = [
    "CANDIDATE_GENERATION_FAILURE",
    "COVER_GENERATION_BUG",
    "DESIGN2SVA_EMBEDDING_BUG",
    "DESIGN2SVA_ROOT_CAUSE_LABELS",
    "JASPER_PARSER_MISCLASSIFICATION",
    "NATIVE_HARNESS_UNREACHABLE",
    "REFERENCE_TASK_INVALID",
    "RESET_CLOCK_MISMATCH",
    "ROOT_CAUSE_CANDIDATES",
    "ROOT_CAUSE_LABELS",
    "UNKNOWN",
    "classify_design2sva_root_cause",
    "classify_design2sva_rootcause",
    "classify_root_cause",
    "classify_root_cause_candidate",
    "root_cause_counts",
    "summarize_root_cause_counts",
    "summarize_root_cause_candidates",
]
