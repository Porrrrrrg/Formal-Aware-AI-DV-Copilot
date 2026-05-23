"""Conservative static SVA feature extraction.

This module intentionally does not attempt to parse full SystemVerilog
Assertions. It extracts stable surface features for offline comparison and
flags ambiguous cases for review.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from app.models.core import CoreModel

SVA_KEYWORDS = {
    "and",
    "assert",
    "assume",
    "begin",
    "bit",
    "disable",
    "else",
    "end",
    "eventually",
    "fell",
    "iff",
    "inside",
    "int",
    "intersect",
    "logic",
    "not",
    "or",
    "posedge",
    "property",
    "rose",
    "s_eventually",
    "sequence",
    "stable",
    "strong",
    "throughout",
    "until",
    "weak",
}

TEMPORAL_OPERATOR_RE = re.compile(
    r"(\|->|\|=>|##\s*\d+|##\s*\[[^\]]+\]|\bthroughout\b|\buntil\b|\bstrong\b|\bs_eventually\b)"
)
COMPARISON_OPERATOR_RE = re.compile(r"(===|!==|==|!=|<=|>=|<|>| inside )")
IDENTIFIER_RE = re.compile(r"(?<!\$)\b[A-Za-z_][A-Za-z0-9_$]*\b")
CONSTANT_RE = re.compile(r"(?<![A-Za-z0-9_$])(?:\d+'[bhd][0-9a-fA-F_xzXZ]+|\d+|1'b[01xXzZ]|[01])\b")


class SvaFeatures(CoreModel):
    """Surface features extracted from one SVA property."""

    raw_sva: str = Field(min_length=1)
    normalized_sva: str = Field(min_length=1)
    referenced_signals: list[str] = Field(default_factory=list)
    clock_pattern: str | None = None
    reset_disable_iff: str | None = None
    antecedent: str | None = None
    consequent: str | None = None
    implication_operator: str | None = None
    temporal_operators: list[str] = Field(default_factory=list)
    delay_tokens: list[str] = Field(default_factory=list)
    comparison_operators: list[str] = Field(default_factory=list)
    uses_onehot: bool = False
    uses_onehot0: bool = False
    constants: list[str] = Field(default_factory=list)
    tautology_flags: list[str] = Field(default_factory=list)


def extract_sva_features(sva: str) -> SvaFeatures:
    normalized = normalize_sva(sva)
    clock_pattern = first_match(r"@\s*\(([^)]*)\)", normalized)
    reset_disable_iff = first_match(r"disable\s+iff\s*\(([^)]*)\)", normalized)
    property_body = extract_property_body(normalized)
    antecedent, consequent, implication = split_implication(property_body)
    temporal_operators = sorted(set(_compact(match.group(1)) for match in TEMPORAL_OPERATOR_RE.finditer(normalized)))
    delay_tokens = sorted({op for op in temporal_operators if op.startswith("##") or op in {"|->", "|=>"}})
    comparison_text = normalized.replace("|->", " ").replace("|=>", " ")
    comparison_operators = sorted(set(match.group(1).strip() for match in COMPARISON_OPERATOR_RE.finditer(comparison_text)))
    constants = sorted(set(match.group(0) for match in CONSTANT_RE.finditer(normalized)))
    signals = extract_signals(normalized)
    tautology_flags = detect_tautologies(normalized, antecedent, consequent)

    return SvaFeatures(
        raw_sva=sva,
        normalized_sva=normalized,
        referenced_signals=signals,
        clock_pattern=clock_pattern.strip() if clock_pattern else None,
        reset_disable_iff=reset_disable_iff.strip() if reset_disable_iff else None,
        antecedent=antecedent,
        consequent=consequent,
        implication_operator=implication,
        temporal_operators=temporal_operators,
        delay_tokens=delay_tokens,
        comparison_operators=comparison_operators,
        uses_onehot="$onehot(" in normalized,
        uses_onehot0="$onehot0(" in normalized,
        constants=constants,
        tautology_flags=tautology_flags,
    )


def normalize_sva(sva: str) -> str:
    return re.sub(r"\s+", " ", sva.strip())


def first_match(pattern: str, value: str) -> str | None:
    match = re.search(pattern, value)
    return match.group(1) if match else None


def extract_property_body(normalized: str) -> str:
    match = re.search(r"assert\s+property\s*\((.*)\)\s*;?\s*$", normalized)
    if not match:
        match = re.search(r"assume\s+property\s*\((.*)\)\s*;?\s*$", normalized)
    body = match.group(1) if match else normalized
    body = re.sub(r"@\s*\([^)]*\)", " ", body)
    body = re.sub(r"disable\s+iff\s*\([^)]*\)", " ", body)
    return normalize_sva(body)


def split_implication(body: str) -> tuple[str | None, str | None, str | None]:
    for operator in ("|->", "|=>"):
        if operator in body:
            left, right = body.split(operator, 1)
            return left.strip() or None, right.strip() or None, operator
    return None, body.strip() or None, None


def extract_signals(text: str) -> list[str]:
    signals: set[str] = set()
    for match in IDENTIFIER_RE.finditer(strip_literals(strip_property_label(text))):
        token = match.group(0)
        lower = token.lower()
        if lower not in SVA_KEYWORDS and not token.startswith("$"):
            signals.add(token)
    return sorted(signals)


def strip_literals(text: str) -> str:
    text = re.sub(r"\d+'[bhd][0-9a-fA-F_xzXZ]+", " ", text)
    return re.sub(r"\b\d+\b", " ", text)


def strip_property_label(text: str) -> str:
    return re.sub(r"^\s*[A-Za-z_][A-Za-z0-9_$]*\s*:\s*", "", text)


def detect_tautologies(normalized: str, antecedent: str | None, consequent: str | None) -> list[str]:
    flags: list[str] = []
    compact = normalized.replace(" ", "")
    if "1'b1|->1'b1" in compact or "1|->1" in compact:
        flags.append("constant_true_implication")
    if "==1'b1" in compact and "!=1'b1" in compact:
        flags.append("mixed_constant_comparison")
    for side_name, side in (("antecedent", antecedent), ("consequent", consequent)):
        if side and re.search(r"\b([A-Za-z_][A-Za-z0-9_$]*)\s*==\s*\1\b", side):
            flags.append(f"{side_name}_self_equality")
        if side and side.strip() in {"1", "1'b1", "1'bx", "true"}:
            flags.append(f"{side_name}_constant_true")
    return sorted(set(flags))


def signal_overlap(left: list[str], right: list[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def feature_payload(features: SvaFeatures) -> dict[str, Any]:
    return features.model_dump(mode="json")


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)
