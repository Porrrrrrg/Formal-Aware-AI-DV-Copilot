"""Weak-property heuristics for SVA intent-alignment review."""

from __future__ import annotations

import re

from app.alignment.sva_features import SvaFeatures, extract_signals


def weak_property_flags(
    *,
    candidate: SvaFeatures,
    reference: SvaFeatures | None,
    required_signals: set[str],
    forbidden_signals: set[str],
) -> list[str]:
    flags: set[str] = set(candidate.tautology_flags)
    candidate_signals = set(candidate.referenced_signals)
    reference_signals = set(reference.referenced_signals) if reference else set()

    if candidate.implication_operator is None and _is_simple_boolean_check(candidate):
        flags.add("simple_signal_check_without_trigger")
    if reference and reference.antecedent and not candidate.antecedent:
        flags.add("antecedent_missing")
    if reference and reference.consequent and not candidate.consequent:
        flags.add("consequent_missing")
    if reference and reference.delay_tokens and candidate.delay_tokens != reference.delay_tokens:
        flags.add("delay_missing_or_changed")
    if required_signals and not required_signals.issubset(candidate_signals):
        flags.add("required_signals_missing")
    if reference_signals and not reference_signals.issubset(candidate_signals | forbidden_signals):
        flags.add("reference_signals_missing")
    if forbidden_signals:
        flags.add("unrelated_or_unknown_signal")
    if reference and _looks_temporally_reversed(candidate, reference):
        flags.add("temporal_direction_changed")
    if reference and reference.clock_pattern and not candidate.clock_pattern:
        flags.add("clock_context_missing")
    if reference and reference.reset_disable_iff and not candidate.reset_disable_iff:
        flags.add("reset_context_missing")
    if reference and reference.antecedent and candidate.antecedent:
        ref_ant_signals = set(extract_signals(reference.antecedent))
        cand_ant_signals = set(extract_signals(candidate.antecedent))
        if ref_ant_signals and cand_ant_signals < ref_ant_signals:
            flags.add("antecedent_narrower_signal_set")
    if reference and reference.consequent and candidate.consequent:
        ref_cons_signals = set(extract_signals(reference.consequent))
        cand_cons_signals = set(extract_signals(candidate.consequent))
        if ref_cons_signals and not ref_cons_signals.issubset(cand_cons_signals | forbidden_signals):
            flags.add("consequent_signal_missing")

    return sorted(flags)


def vacuity_risk_flags(candidate: SvaFeatures, reference: SvaFeatures | None) -> list[str]:
    flags: set[str] = set()
    if candidate.antecedent:
        ant = candidate.antecedent.replace(" ", "")
        if re.search(r"([A-Za-z_][A-Za-z0-9_$]*)&&!?\1", ant) or "1'b0" in ant or ant == "0":
            flags.add("antecedent_may_be_unsatisfiable")
    if reference and reference.antecedent and not candidate.antecedent:
        flags.add("reference_trigger_removed")
    if candidate.consequent and candidate.consequent.strip() in {"1", "1'b1", "true"}:
        flags.add("consequent_constant_true")
    if candidate.implication_operator and not candidate.antecedent:
        flags.add("empty_antecedent")
    return sorted(flags)


def _is_simple_boolean_check(features: SvaFeatures) -> bool:
    if not features.consequent:
        return False
    expr = features.consequent.strip()
    return bool(re.fullmatch(r"!?[A-Za-z_][A-Za-z0-9_$]*(\s*(==|!=|===|!==)\s*[01](?:'b[01])?)?", expr))


def _looks_temporally_reversed(candidate: SvaFeatures, reference: SvaFeatures) -> bool:
    if not candidate.antecedent or not candidate.consequent or not reference.antecedent or not reference.consequent:
        return False
    cand_ant = set(extract_signals(candidate.antecedent))
    cand_cons = set(extract_signals(candidate.consequent))
    ref_ant = set(extract_signals(reference.antecedent))
    ref_cons = set(extract_signals(reference.consequent))
    return bool(cand_ant and cand_cons and cand_ant == ref_cons and cand_cons == ref_ant)
