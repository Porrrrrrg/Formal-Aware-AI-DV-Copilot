"""Static/offline intent-alignment evaluation for SVA candidates."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.alignment.sva_features import SvaFeatures, extract_sva_features, signal_overlap
from app.alignment.weak_property_checks import vacuity_risk_flags, weak_property_flags
from app.models.core import CoreModel


class AlignmentLabel(str, Enum):
    """Bounded labels for static intent-alignment review."""

    ALIGNED = "aligned"
    LIKELY_ALIGNED = "likely_aligned"
    PARTIALLY_ALIGNED = "partially_aligned"
    LIKELY_MISALIGNED = "likely_misaligned"
    UNKNOWN_NEEDS_REVIEW = "unknown_needs_review"


class MatchStatus(str, Enum):
    """Coarse structural match status for one SVA dimension."""

    MATCH = "match"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    MISSING = "missing"
    UNKNOWN = "unknown"


class IntentAlignmentCase(CoreModel):
    """Input record for static intent-alignment evaluation."""

    case_id: str = Field(min_length=1)
    candidate_id: str | None = Field(default=None, min_length=1)
    property_id: str | None = Field(default=None, min_length=1)
    intent_summary: str = Field(min_length=1)
    candidate_sva: str = Field(min_length=1)
    reference_sva: str | None = Field(default=None, min_length=1)
    allowed_signals: list[str] = Field(default_factory=list)
    required_signals: list[str] = Field(default_factory=list)
    proof_status_context: dict[str, Any] | None = None
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_identifier(self) -> "IntentAlignmentCase":
        if not self.property_id and not self.candidate_id:
            raise ValueError("property_id or candidate_id is required")
        return self


class IntentAlignmentResult(CoreModel):
    """Strict static alignment result schema."""

    case_id: str = Field(min_length=1)
    property_id: str | None = Field(default=None, min_length=1)
    candidate_id: str | None = Field(default=None, min_length=1)
    intent_summary: str = Field(min_length=1)
    candidate_sva: str = Field(min_length=1)
    reference_sva: str | None = Field(default=None, min_length=1)
    alignment_label: AlignmentLabel
    alignment_score: float = Field(ge=0.0, le=1.0)
    trigger_match: MatchStatus
    consequent_match: MatchStatus
    delay_match: MatchStatus
    signal_coverage: float = Field(ge=0.0, le=1.0)
    forbidden_or_unknown_signal_count: int = Field(ge=0)
    weak_property_flags: list[str] = Field(default_factory=list)
    vacuity_risk_flags: list[str] = Field(default_factory=list)
    proof_status_context: dict[str, Any] | None = None
    manual_review_required: bool
    rationale: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    candidate_features: SvaFeatures
    reference_features: SvaFeatures | None = None

    @field_validator("weak_property_flags", "vacuity_risk_flags", "rationale", "evidence_refs")
    @classmethod
    def require_non_empty_items(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("list items must be non-empty strings")
        return value


def evaluate_intent_alignment(case: IntentAlignmentCase) -> IntentAlignmentResult:
    candidate = extract_sva_features(case.candidate_sva)
    reference = extract_sva_features(case.reference_sva) if case.reference_sva else None
    allowed_signals = set(case.allowed_signals)
    required_signals = set(case.required_signals or (reference.referenced_signals if reference else []))
    forbidden = set(candidate.referenced_signals) - allowed_signals if allowed_signals else set()

    trigger_match = compare_side(candidate.antecedent, reference.antecedent if reference else None)
    consequent_match = compare_side(candidate.consequent, reference.consequent if reference else None)
    delay_match = compare_tokens(candidate.delay_tokens, reference.delay_tokens if reference else None)
    coverage_basis = sorted(required_signals or set(reference.referenced_signals if reference else []))
    signal_coverage = coverage(candidate.referenced_signals, coverage_basis)
    weak_flags = weak_property_flags(
        candidate=candidate,
        reference=reference,
        required_signals=set(coverage_basis),
        forbidden_signals=forbidden,
    )
    vacuity_flags = vacuity_risk_flags(candidate, reference)
    score = score_alignment(
        trigger_match=trigger_match,
        consequent_match=consequent_match,
        delay_match=delay_match,
        signal_coverage=signal_coverage,
        forbidden_count=len(forbidden),
        weak_flags=weak_flags,
        vacuity_flags=vacuity_flags,
        reference_present=reference is not None,
    )
    label = label_for_score(
        score=score,
        forbidden_count=len(forbidden),
        weak_flags=weak_flags,
        reference_present=reference is not None,
        candidate=case,
    )
    manual_review_required = (
        label
        in {
            AlignmentLabel.PARTIALLY_ALIGNED,
            AlignmentLabel.LIKELY_MISALIGNED,
            AlignmentLabel.UNKNOWN_NEEDS_REVIEW,
        }
        or bool(forbidden)
        or bool(vacuity_flags)
        or structural_review_required(trigger_match, consequent_match, delay_match)
    )
    rationale = build_rationale(
        label=label,
        trigger_match=trigger_match,
        consequent_match=consequent_match,
        delay_match=delay_match,
        signal_coverage=signal_coverage,
        forbidden=forbidden,
        weak_flags=weak_flags,
        vacuity_flags=vacuity_flags,
        proof_status_context=case.proof_status_context,
    )
    return IntentAlignmentResult(
        case_id=case.case_id,
        property_id=case.property_id,
        candidate_id=case.candidate_id,
        intent_summary=case.intent_summary,
        candidate_sva=case.candidate_sva,
        reference_sva=case.reference_sva,
        alignment_label=label,
        alignment_score=round(score, 3),
        trigger_match=trigger_match,
        consequent_match=consequent_match,
        delay_match=delay_match,
        signal_coverage=round(signal_coverage, 3),
        forbidden_or_unknown_signal_count=len(forbidden),
        weak_property_flags=weak_flags,
        vacuity_risk_flags=vacuity_flags,
        proof_status_context=case.proof_status_context,
        manual_review_required=manual_review_required,
        rationale=rationale,
        evidence_refs=case.evidence_refs,
        candidate_features=candidate,
        reference_features=reference,
    )


def evaluate_intent_alignment_cases(cases: list[IntentAlignmentCase]) -> list[IntentAlignmentResult]:
    return [evaluate_intent_alignment(case) for case in cases]


def load_cases(cases_path: Path, candidates_path: Path | None = None, *, limit: int | None = None) -> list[IntentAlignmentCase]:
    case_rows = load_json_or_jsonl(cases_path)
    candidate_rows = load_json_or_jsonl(candidates_path) if candidates_path else []
    candidates_by_key = index_candidates(candidate_rows)
    cases: list[IntentAlignmentCase] = []
    for row in case_rows:
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("case_id", ""))
        property_id = as_optional_str(row.get("property_id"))
        candidate = pick_candidate(row, candidates_by_key)
        if candidates_path and candidate is None:
            continue
        candidate_sva = (
            as_optional_str(candidate.get("codex_repaired_sva") if candidate else None)
            or as_optional_str(candidate.get("candidate_sva") if candidate else None)
            or as_optional_str(candidate.get("sva") if candidate else None)
            or as_optional_str(row.get("candidate_sva"))
            or as_optional_str(row.get("reference_sva"))
        )
        if not case_id or not candidate_sva:
            continue
        proof_context = candidate.get("proof_status_context") if candidate else None
        if proof_context is None:
            proof_context = {
                key: candidate[key]
                for key in ("candidate_status", "scaffold_success", "syntax_scaffold_ok", "exact_match")
                if candidate and key in candidate
            } or None
        cases.append(
            IntentAlignmentCase(
                case_id=case_id,
                property_id=property_id,
                candidate_id=as_optional_str(candidate.get("candidate_id") if candidate else None),
                intent_summary=as_optional_str(row.get("intent")) or "No intent summary available.",
                candidate_sva=candidate_sva,
                reference_sva=as_optional_str(row.get("reference_sva")),
                allowed_signals=list(row.get("signals", []) or candidate.get("referenced_signals", []) or []),
                required_signals=list(row.get("signals", []) or []),
                proof_status_context=proof_context if isinstance(proof_context, dict) else None,
                evidence_refs=[str(cases_path), *(str(candidates_path) for _ in [0] if candidates_path)],
            )
        )
        if limit is not None and len(cases) >= limit:
            break
    return cases


def load_json_or_jsonl(path: Path | None) -> list[Any]:
    if path is None:
        return []
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    loaded = json.loads(text)
    return loaded if isinstance(loaded, list) else [loaded]


def index_candidates(rows: list[Any]) -> dict[tuple[str | None, str | None], dict[str, Any]]:
    indexed: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = (as_optional_str(row.get("case_id")), as_optional_str(row.get("property_id")))
        indexed.setdefault(key, row)
    return indexed


def pick_candidate(
    row: dict[str, Any],
    candidates_by_key: dict[tuple[str | None, str | None], dict[str, Any]],
) -> dict[str, Any] | None:
    key = (as_optional_str(row.get("case_id")), as_optional_str(row.get("property_id")))
    return candidates_by_key.get(key)


def compare_side(candidate_side: str | None, reference_side: str | None) -> MatchStatus:
    if reference_side is None:
        return MatchStatus.UNKNOWN
    if not candidate_side:
        return MatchStatus.MISSING
    candidate_norm = normalize_expr(candidate_side)
    reference_norm = normalize_expr(reference_side)
    if candidate_norm == reference_norm:
        return MatchStatus.MATCH
    overlap = signal_overlap(extract_sva_features(candidate_side).referenced_signals, extract_sva_features(reference_side).referenced_signals)
    return MatchStatus.PARTIAL if overlap >= 0.5 else MatchStatus.MISMATCH


def compare_tokens(candidate_tokens: list[str], reference_tokens: list[str] | None) -> MatchStatus:
    if reference_tokens is None:
        return MatchStatus.UNKNOWN
    if candidate_tokens == reference_tokens:
        return MatchStatus.MATCH
    if not candidate_tokens:
        return MatchStatus.MISSING
    return MatchStatus.PARTIAL if set(candidate_tokens) & set(reference_tokens) else MatchStatus.MISMATCH


def coverage(candidate_signals: list[str], required_signals: list[str]) -> float:
    if not required_signals:
        return 1.0
    return len(set(candidate_signals) & set(required_signals)) / len(set(required_signals))


def score_alignment(
    *,
    trigger_match: MatchStatus,
    consequent_match: MatchStatus,
    delay_match: MatchStatus,
    signal_coverage: float,
    forbidden_count: int,
    weak_flags: list[str],
    vacuity_flags: list[str],
    reference_present: bool,
) -> float:
    if not reference_present:
        return max(0.0, min(0.65, signal_coverage - 0.1 * forbidden_count))
    score = (
        0.25 * match_score(trigger_match)
        + 0.30 * match_score(consequent_match)
        + 0.20 * match_score(delay_match)
        + 0.25 * signal_coverage
    )
    score -= min(0.35, 0.08 * len(weak_flags))
    score -= min(0.2, 0.06 * len(vacuity_flags))
    score -= min(0.3, 0.12 * forbidden_count)
    return max(0.0, min(1.0, score))


def match_score(status: MatchStatus) -> float:
    return {
        MatchStatus.MATCH: 1.0,
        MatchStatus.PARTIAL: 0.55,
        MatchStatus.UNKNOWN: 0.35,
        MatchStatus.MISSING: 0.0,
        MatchStatus.MISMATCH: 0.0,
    }[status]


def structural_review_required(*statuses: MatchStatus) -> bool:
    review_statuses = {
        MatchStatus.PARTIAL,
        MatchStatus.MISMATCH,
        MatchStatus.MISSING,
        MatchStatus.UNKNOWN,
    }
    return any(status in review_statuses for status in statuses)


def label_for_score(
    *,
    score: float,
    forbidden_count: int,
    weak_flags: list[str],
    reference_present: bool,
    candidate: IntentAlignmentCase,
) -> AlignmentLabel:
    if not reference_present:
        return AlignmentLabel.UNKNOWN_NEEDS_REVIEW
    severe = {
        "consequent_missing",
        "consequent_signal_missing",
        "temporal_direction_changed",
        "unrelated_or_unknown_signal",
    }
    if forbidden_count or severe & set(weak_flags):
        return AlignmentLabel.LIKELY_MISALIGNED
    if "antecedent_missing" in weak_flags or "required_signals_missing" in weak_flags:
        return AlignmentLabel.PARTIALLY_ALIGNED if score >= 0.45 else AlignmentLabel.LIKELY_MISALIGNED
    if score >= 0.98 and not weak_flags and candidate.proof_status_context is None:
        return AlignmentLabel.ALIGNED
    if score >= 0.82:
        return AlignmentLabel.LIKELY_ALIGNED
    if score >= 0.45:
        return AlignmentLabel.PARTIALLY_ALIGNED
    return AlignmentLabel.LIKELY_MISALIGNED


def build_rationale(
    *,
    label: AlignmentLabel,
    trigger_match: MatchStatus,
    consequent_match: MatchStatus,
    delay_match: MatchStatus,
    signal_coverage: float,
    forbidden: set[str],
    weak_flags: list[str],
    vacuity_flags: list[str],
    proof_status_context: dict[str, Any] | None,
) -> list[str]:
    rationale = [
        f"Static alignment label is {label.value}.",
        f"Trigger={trigger_match.value}, consequent={consequent_match.value}, delay={delay_match.value}, signal_coverage={signal_coverage:.3f}.",
    ]
    if forbidden:
        rationale.append(f"Candidate references signals outside the allowed set: {sorted(forbidden)}.")
    if weak_flags:
        rationale.append(f"Weak-property flags: {', '.join(weak_flags)}.")
    if vacuity_flags:
        rationale.append(f"Vacuity risk flags: {', '.join(vacuity_flags)}.")
    if proof_status_context:
        rationale.append("Proof/status context is recorded as evidence only and does not imply intent alignment.")
    return rationale


def normalize_expr(value: str) -> str:
    return "".join(value.split())


def as_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
