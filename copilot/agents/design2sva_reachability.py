"""Lightweight Design2SVA reachability helpers.

These utilities intentionally stop short of being a full SVA parser. They cover
the inline assertion forms emitted by the local Design2SVA flow and return
explicit ``unknown`` metadata for unsupported or ambiguous inputs.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

MAX_SVA_CHARS = 8192
MAX_EXPR_CHARS = 4096

UNKNOWN = "unknown"
EXTRACTED = "extracted"
APPROXIMATED = "approximated"
GENERATED = "generated"
NO_ANTECEDENT = "no_antecedent"
INVARIANT = "invariant"

REACHABLE = "reachable"
UNREACHABLE = "unreachable"
BOUNDED_UNCOVERED = "bounded_uncovered"
VACUOUS = "vacuous"
NOT_RUN = "not_run"
SYNTAX_ERROR = "syntax_error"

_ASSERT_PROPERTY_RE = re.compile(r"\bassert\s+property\b", re.IGNORECASE)
_LABEL_RE = re.compile(r"(?P<label>[A-Za-z_][A-Za-z0-9_$]*)\s*:\s*$")
_IDENTIFIER_RE = re.compile(r"[^A-Za-z0-9_$]+")


def extract_assertion_trigger(sva: str) -> dict[str, Any]:
    """Extract an assertion antecedent when one exists.

    The returned dictionary is JSON-friendly and always has ``ok``, ``status``,
    ``condition``, ``condition_kind``, ``reason``, and ``unknown_reason`` keys.
    ``condition_kind`` is ``antecedent`` when a top-level implication operator is
    found, otherwise ``invariant`` with ``status`` set to ``no_antecedent``.
    """

    if not isinstance(sva, str):
        return _unknown("non_string_sva")
    if len(sva) > MAX_SVA_CHARS:
        return _unknown("input_too_long", input_length=len(sva), max_length=MAX_SVA_CHARS)

    text = _strip_comments(sva).strip()
    if not text:
        return _unknown("empty_sva")

    payload_info = _extract_assert_property_payload(text)
    if not payload_info["ok"]:
        return payload_info

    payload = str(payload_info["payload"]).strip()
    if len(payload) > MAX_EXPR_CHARS:
        return _unknown(
            "property_expression_too_long",
            property_id=payload_info.get("property_id"),
            input_length=len(payload),
            max_length=MAX_EXPR_CHARS,
        )

    prefix = _split_property_prefix(payload)
    if not prefix["ok"]:
        prefix.update(
            {
                "property_id": payload_info.get("property_id"),
                "source_assertion": payload_info.get("source_assertion"),
            }
        )
        return prefix

    body = _strip_trailing_semicolon(str(prefix["body"]).strip())
    body = _strip_enclosing_parens(body)
    if not body:
        return _unknown(
            "empty_property_body",
            property_id=payload_info.get("property_id"),
            clocking_event=prefix.get("clocking_event"),
            disable_iff=prefix.get("disable_iff"),
            disable_condition=prefix.get("disable_condition"),
        )

    implication = _find_top_level_implication(body)
    warnings: list[str] = []
    possible_named_reference = _is_possible_named_property_reference(body, implication is not None)
    if possible_named_reference and prefix.get("clocking_event") is None:
        return _unknown(
            "named_property_reference",
            property_id=payload_info.get("property_id"),
            property_body=body,
            warnings=["inline_property_body_required_for_antecedent_extraction"],
        )
    if possible_named_reference:
        warnings.append("named_property_reference_possible")

    if implication is not None:
        operator_index, operator = implication
        condition = _strip_enclosing_parens(body[:operator_index].strip())
        if not condition:
            return _unknown(
                "empty_antecedent",
                property_id=payload_info.get("property_id"),
                clocking_event=prefix.get("clocking_event"),
                disable_iff=prefix.get("disable_iff"),
                disable_condition=prefix.get("disable_condition"),
                property_body=body,
                operator=operator,
            )
        status = EXTRACTED
        condition_kind = "antecedent"
        trigger_kind = "antecedent"
        trigger_status = EXTRACTED
        confidence = "high"
        reason = ""
        approximate = False
        has_antecedent = True
        requires_antecedent_cover = True
    else:
        condition = None
        operator = None
        status = NO_ANTECEDENT
        condition_kind = INVARIANT
        trigger_kind = INVARIANT
        trigger_status = NO_ANTECEDENT
        confidence = "high"
        reason = "no_top_level_implication"
        approximate = False
        has_antecedent = False
        requires_antecedent_cover = False

    if condition is not None and len(condition) > MAX_EXPR_CHARS:
        return _unknown(
            "condition_too_long",
            property_id=payload_info.get("property_id"),
            input_length=len(condition),
            max_length=MAX_EXPR_CHARS,
        )

    return {
        "ok": True,
        "status": status,
        "reason": reason,
        "unknown_reason": None,
        "property_id": payload_info.get("property_id"),
        "source_assertion": payload_info.get("source_assertion"),
        "clocking_event": prefix.get("clocking_event"),
        "disable_iff": prefix.get("disable_iff"),
        "disable_condition": prefix.get("disable_condition"),
        "property_body": body,
        "condition": condition,
        "condition_kind": condition_kind,
        "trigger_kind": trigger_kind,
        "trigger_status": trigger_status,
        "operator": operator,
        "confidence": confidence,
        "approximate": approximate,
        "has_antecedent": has_antecedent,
        "requires_antecedent_cover": requires_antecedent_cover,
        "warnings": warnings,
    }


def generate_antecedent_cover(
    sva: str,
    cover_property_id: str | None = None,
    source_property_id: str | None = None,
) -> dict[str, Any]:
    """Generate a companion cover property for an extracted antecedent."""

    extraction = extract_assertion_trigger(sva)
    if source_property_id and not extraction.get("property_id"):
        extraction = dict(extraction)
        extraction["property_id"] = source_property_id

    if not extraction.get("ok"):
        reason = str(extraction.get("unknown_reason") or extraction.get("reason") or UNKNOWN)
        return {
            "ok": False,
            "status": UNKNOWN,
            "reason": reason,
            "unknown_reason": reason,
            "property_id": None,
            "source_property_id": extraction.get("property_id"),
            "condition": None,
            "condition_kind": None,
            "trigger_kind": extraction.get("trigger_kind"),
            "trigger_status": extraction.get("trigger_status", UNKNOWN),
            "has_antecedent": extraction.get("has_antecedent"),
            "requires_antecedent_cover": extraction.get("requires_antecedent_cover"),
            "cover_sva": None,
            "extraction": extraction,
            "warnings": [],
        }

    if not extraction.get("has_antecedent"):
        return {
            "ok": False,
            "status": NO_ANTECEDENT,
            "reason": NO_ANTECEDENT,
            "unknown_reason": None,
            "property_id": None,
            "source_property_id": extraction.get("property_id"),
            "condition": None,
            "condition_kind": extraction.get("condition_kind"),
            "trigger_kind": extraction.get("trigger_kind"),
            "trigger_status": extraction.get("trigger_status"),
            "has_antecedent": False,
            "requires_antecedent_cover": False,
            "cover_sva": None,
            "extraction": extraction,
            "warnings": list(extraction.get("warnings") or []),
        }

    condition = str(extraction.get("condition") or "").strip()
    if not condition:
        reason = "empty_condition"
        return {
            "ok": False,
            "status": UNKNOWN,
            "reason": reason,
            "unknown_reason": reason,
            "property_id": None,
            "source_property_id": extraction.get("property_id"),
            "condition": None,
            "condition_kind": extraction.get("condition_kind"),
            "trigger_kind": extraction.get("trigger_kind"),
            "trigger_status": extraction.get("trigger_status"),
            "has_antecedent": extraction.get("has_antecedent"),
            "requires_antecedent_cover": extraction.get("requires_antecedent_cover"),
            "cover_sva": None,
            "extraction": extraction,
            "warnings": [],
        }

    cover_id = _sanitize_identifier(
        cover_property_id
        or _default_cover_property_id(
            str(extraction.get("property_id") or source_property_id or "anonymous"),
            str(extraction.get("condition_kind") or "trigger"),
        )
    )

    cover_items = []
    if extraction.get("clocking_event"):
        cover_items.append(str(extraction["clocking_event"]))
    if extraction.get("disable_iff"):
        cover_items.append(str(extraction["disable_iff"]))
    cover_items.append(f"({condition})")
    cover_body = " ".join(cover_items)

    warnings = list(extraction.get("warnings") or [])
    if extraction.get("approximate"):
        warnings.append("cover_uses_approximated_trigger_condition")
    if _is_trivial_condition(condition):
        warnings.append("trivial_trigger_condition")

    return {
        "ok": True,
        "status": GENERATED,
        "reason": "",
        "unknown_reason": None,
        "property_id": cover_id,
        "source_property_id": extraction.get("property_id"),
        "condition": condition,
        "condition_kind": extraction.get("condition_kind"),
        "trigger_kind": extraction.get("trigger_kind"),
        "trigger_status": extraction.get("trigger_status"),
        "has_antecedent": True,
        "requires_antecedent_cover": True,
        "cover_sva": f"{cover_id}: cover property ({cover_body});",
        "extraction": extraction,
        "warnings": warnings,
    }


def classify_reachability(
    cover_status: str | Mapping[str, Any] | None = None,
    proof_status: str | None = None,
    vacuity_status: str | None = None,
    syntax_status: str | None = None,
) -> dict[str, Any]:
    """Classify bounded trigger reachability from cover/proof status metadata."""

    if isinstance(cover_status, Mapping):
        metadata = cover_status
        if _metadata_has_no_antecedent(metadata):
            return _no_antecedent_reachability(
                cover_status=metadata,
                proof_status=proof_status,
                vacuity_status=vacuity_status,
                syntax_status=syntax_status,
            )
        cover_status = _first_present(
            metadata,
            "cover_status",
            "reachability_cover_status",
            "antecedent_cover_status",
            "trigger_cover_status",
        )
        proof_status = proof_status or _first_present(
            metadata,
            "proof_status",
            "assert_proof_status",
        )
        vacuity_status = vacuity_status or _first_present(
            metadata,
            "vacuity_status",
            "assert_vacuity_status",
        )
        syntax_status = syntax_status or _first_present(metadata, "syntax_status")

    normalized = {
        "cover_status": _normalize_status(cover_status),
        "proof_status": _normalize_status(proof_status),
        "vacuity_status": _normalize_status(vacuity_status),
        "syntax_status": _normalize_status(syntax_status),
    }
    status = UNKNOWN
    is_reachable: bool | None = None
    is_non_vacuous: bool | None = None
    reason = "insufficient_reachability_evidence"

    status_values = set(normalized.values())
    if status_values & {SYNTAX_ERROR, "syntax_failed"}:
        status = SYNTAX_ERROR
        reason = "syntax_status_blocks_reachability"
    elif normalized["cover_status"] in {"covered", REACHABLE, "hit", "passed", "pass"}:
        status = REACHABLE
        is_reachable = True
        is_non_vacuous = normalized["vacuity_status"] != VACUOUS
        reason = "cover_witness_reached_trigger"
    elif normalized["proof_status"] in {"covered", REACHABLE, "hit"}:
        status = REACHABLE
        is_reachable = True
        is_non_vacuous = normalized["vacuity_status"] != VACUOUS
        reason = "cover_proof_status_reached_trigger"
    elif normalized["proof_status"] in {"falsified", "failed", "fail", "cex", "counterexample"}:
        status = REACHABLE
        is_reachable = True
        is_non_vacuous = True
        reason = "assertion_counterexample_reached_trigger"
    elif normalized["cover_status"] == UNREACHABLE:
        status = UNREACHABLE
        is_reachable = False
        is_non_vacuous = False
        reason = "cover_proved_trigger_unreachable"
    elif normalized["proof_status"] == UNREACHABLE:
        status = UNREACHABLE
        is_reachable = False
        is_non_vacuous = False
        reason = "proof_status_reports_trigger_unreachable"
    elif normalized["vacuity_status"] == VACUOUS:
        status = VACUOUS
        is_reachable = False
        is_non_vacuous = False
        reason = "assertion_reported_vacuous_without_cover_witness"
    elif normalized["cover_status"] in {
        "uncovered",
        "not_covered",
        "cover_failed",
        "unhit",
        "missed",
    }:
        status = BOUNDED_UNCOVERED
        reason = "cover_not_hit_within_available_bound"
    elif normalized["proof_status"] in {
        "uncovered",
        "not_covered",
        "cover_failed",
        "unhit",
        "missed",
    }:
        status = BOUNDED_UNCOVERED
        reason = "proof_status_not_hit_within_available_bound"
    elif all(value in {None, "", NOT_RUN, UNKNOWN} for value in normalized.values()):
        status = NOT_RUN
        reason = "reachability_not_run"
    elif normalized["proof_status"] in {"undetermined", "inconclusive", UNKNOWN}:
        status = UNKNOWN
        reason = "proof_status_undetermined"
    elif normalized["proof_status"] in {"proven", "passed", "pass"}:
        status = UNKNOWN
        is_non_vacuous = normalized["vacuity_status"] not in {VACUOUS, UNKNOWN, NOT_RUN, None, ""}
        reason = "assertion_proof_does_not_establish_trigger_reachability"

    return {
        "ok": status in {REACHABLE, UNREACHABLE, BOUNDED_UNCOVERED, VACUOUS},
        "status": status,
        "reachability_status": status,
        "is_reachable": is_reachable,
        "is_non_vacuous": is_non_vacuous,
        "reason": reason,
        "cover_status": normalized["cover_status"],
        "proof_status": normalized["proof_status"],
        "vacuity_status": normalized["vacuity_status"],
        "syntax_status": normalized["syntax_status"],
    }


def cover_before_assert_metadata(
    sva: str,
    cover_status: str | Mapping[str, Any] | None = None,
    proof_status: str | None = None,
    vacuity_status: str | None = None,
    syntax_status: str | None = None,
    cover_property_id: str | None = None,
) -> dict[str, Any]:
    """Return extraction, companion cover, and status classification metadata."""

    cover = generate_antecedent_cover(sva, cover_property_id=cover_property_id)
    no_antecedent = cover.get("status") == NO_ANTECEDENT
    reachability = (
        _no_antecedent_reachability(
            cover_status=cover_status,
            proof_status=proof_status,
            vacuity_status=vacuity_status,
            syntax_status=syntax_status,
        )
        if no_antecedent
        else classify_reachability(
            cover_status=cover_status,
            proof_status=proof_status,
            vacuity_status=vacuity_status,
            syntax_status=syntax_status,
        )
    )
    if not cover.get("ok") and reachability["status"] in {UNKNOWN, NOT_RUN}:
        reachability = dict(reachability)
        reachability["status"] = UNKNOWN
        reachability["reachability_status"] = UNKNOWN
        reachability["reason"] = "trigger_extraction_unknown"
    return {
        "ok": bool(cover.get("ok") or no_antecedent),
        "status": cover.get("status", UNKNOWN) if cover.get("ok") or no_antecedent else UNKNOWN,
        "extraction": cover.get("extraction"),
        "cover": cover,
        "has_antecedent": cover.get("has_antecedent"),
        "requires_antecedent_cover": cover.get("requires_antecedent_cover"),
        "trigger_kind": cover.get("trigger_kind"),
        "trigger_status": cover.get("trigger_status"),
        "reachability": reachability,
    }


def _no_antecedent_reachability(
    cover_status: str | Mapping[str, Any] | None = None,
    proof_status: str | None = None,
    vacuity_status: str | None = None,
    syntax_status: str | None = None,
) -> dict[str, Any]:
    if isinstance(cover_status, Mapping):
        metadata = cover_status
        proof_status = proof_status or _first_present(
            metadata,
            "proof_status",
            "assert_proof_status",
        )
        vacuity_status = vacuity_status or _first_present(
            metadata,
            "vacuity_status",
            "assert_vacuity_status",
        )
        syntax_status = syntax_status or _first_present(metadata, "syntax_status")
        cover_status = _first_present(
            metadata,
            "cover_status",
            "reachability_cover_status",
            "antecedent_cover_status",
            "trigger_cover_status",
        )

    normalized = {
        "cover_status": _normalize_status(cover_status),
        "proof_status": _normalize_status(proof_status),
        "vacuity_status": _normalize_status(vacuity_status),
        "syntax_status": _normalize_status(syntax_status),
    }
    status = NO_ANTECEDENT
    reason = "invariant_has_no_antecedent_cover"

    return {
        "ok": True,
        "status": status,
        "reachability_status": status,
        "is_reachable": None,
        "is_non_vacuous": (
            normalized["vacuity_status"] != VACUOUS
            if normalized["proof_status"] in {"proven", "passed", "pass"}
            else None
        ),
        "reason": reason,
        "cover_status": normalized["cover_status"],
        "proof_status": normalized["proof_status"],
        "vacuity_status": normalized["vacuity_status"],
        "syntax_status": normalized["syntax_status"],
        "has_antecedent": False,
        "requires_antecedent_cover": False,
    }


def _unknown(reason: str, **metadata: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "status": UNKNOWN,
        "reason": reason,
        "unknown_reason": reason,
        "property_id": None,
        "source_assertion": None,
        "clocking_event": None,
        "disable_iff": None,
        "disable_condition": None,
        "property_body": None,
        "condition": None,
        "condition_kind": None,
        "trigger_kind": None,
        "trigger_status": UNKNOWN,
        "has_antecedent": None,
        "requires_antecedent_cover": None,
        "operator": None,
        "confidence": "none",
        "approximate": False,
        "warnings": [],
    }
    result.update(metadata)
    return result


def _strip_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    escaped = False
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            i += 1
            continue
        if char == "/" and nxt == "/":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            out.append(" ")
            continue
        if char == "/" and nxt == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(len(text), i + 2)
            out.append(" ")
            continue
        out.append(char)
        i += 1
    return "".join(out)


def _extract_assert_property_payload(text: str) -> dict[str, Any]:
    match = _ASSERT_PROPERTY_RE.search(text)
    if not match:
        return _unknown("missing_assert_property")

    label_match = _LABEL_RE.search(text[: match.start()])
    property_id = label_match.group("label") if label_match else None

    open_index = text.find("(", match.end())
    if open_index < 0:
        return _unknown("missing_property_parentheses", property_id=property_id)

    close_index = _find_matching_delimiter(text, open_index, "(", ")")
    if close_index is None:
        return _unknown("unbalanced_property_parentheses", property_id=property_id)

    source_assertion = text[match.start() : close_index + 1].strip()
    return {
        "ok": True,
        "payload": text[open_index + 1 : close_index],
        "property_id": property_id,
        "source_assertion": source_assertion,
    }


def _split_property_prefix(payload: str) -> dict[str, Any]:
    rest = payload.strip()
    clocking_event = None
    disable_iff = None
    disable_condition = None

    if rest.startswith("@"):
        clocking_event, rest = _consume_clocking_event(rest)
        if clocking_event is None:
            return _unknown("malformed_clocking_event", property_body=payload)

    disable_match = re.match(r"disable\s+iff\b", rest, flags=re.IGNORECASE)
    if disable_match:
        after_disable = disable_match.end()
        open_index = _skip_space(rest, after_disable)
        if open_index >= len(rest) or rest[open_index] != "(":
            return _unknown("malformed_disable_iff", clocking_event=clocking_event)
        close_index = _find_matching_delimiter(rest, open_index, "(", ")")
        if close_index is None:
            return _unknown("unbalanced_disable_iff", clocking_event=clocking_event)
        disable_iff = rest[: close_index + 1].strip()
        disable_condition = rest[open_index + 1 : close_index].strip()
        rest = rest[close_index + 1 :].strip()

    return {
        "ok": True,
        "clocking_event": clocking_event,
        "disable_iff": disable_iff,
        "disable_condition": disable_condition,
        "body": rest,
    }


def _consume_clocking_event(text: str) -> tuple[str | None, str]:
    index = _skip_space(text, 1)
    if index >= len(text):
        return None, text
    if text[index] == "(":
        close_index = _find_matching_delimiter(text, index, "(", ")")
        if close_index is None:
            return None, text
        return text[: close_index + 1].strip(), text[close_index + 1 :].strip()

    match = re.match(r"@\s*[A-Za-z_][A-Za-z0-9_$]*", text)
    if not match:
        return None, text
    return match.group(0).strip(), text[match.end() :].strip()


def _find_matching_delimiter(
    text: str,
    open_index: int,
    open_char: str,
    close_char: str,
) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
    return None


def _strip_enclosing_parens(expr: str) -> str:
    stripped = expr.strip()
    while stripped.startswith("("):
        close_index = _find_matching_delimiter(stripped, 0, "(", ")")
        if close_index != len(stripped) - 1:
            break
        stripped = stripped[1:-1].strip()
    return stripped


def _strip_trailing_semicolon(expr: str) -> str:
    stripped = expr.strip()
    return stripped[:-1].strip() if stripped.endswith(";") else stripped


def _find_top_level_implication(expr: str) -> tuple[int, str] | None:
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    in_string = False
    escaped = False
    operators = ("|->", "|=>", "#-#", "#=#")
    for index, char in enumerate(expr):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "(":
            paren_depth += 1
            continue
        if char == ")":
            paren_depth = max(0, paren_depth - 1)
            continue
        if char == "[":
            bracket_depth += 1
            continue
        if char == "]":
            bracket_depth = max(0, bracket_depth - 1)
            continue
        if char == "{":
            brace_depth += 1
            continue
        if char == "}":
            brace_depth = max(0, brace_depth - 1)
            continue

        if paren_depth or bracket_depth or brace_depth:
            continue
        for operator in operators:
            if expr.startswith(operator, index):
                return index, operator
        if _word_at(expr, index, "implies"):
            return index, "implies"
    return None


def _word_at(text: str, index: int, word: str) -> bool:
    if not text.startswith(word, index):
        return False
    before = text[index - 1] if index > 0 else " "
    after_index = index + len(word)
    after = text[after_index] if after_index < len(text) else " "
    return not _is_identifier_char(before) and not _is_identifier_char(after)


def _is_identifier_char(char: str) -> bool:
    return char.isalnum() or char in {"_", "$"}


def _skip_space(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _sanitize_identifier(identifier: str) -> str:
    cleaned = _IDENTIFIER_RE.sub("_", identifier.strip()).strip("_")
    if not cleaned:
        cleaned = "cov_antecedent"
    if not re.match(r"[A-Za-z_]", cleaned):
        cleaned = "cov_" + cleaned
    return cleaned


def _default_cover_property_id(source_property_id: str, condition_kind: str) -> str:
    suffix = "antecedent" if condition_kind == "antecedent" else "trigger"
    return f"cov_{source_property_id}_{suffix}"


def _is_trivial_condition(condition: str) -> bool:
    normalized = re.sub(r"\s+", "", condition.lower())
    return normalized in {"1", "1'b1", "1'bx", "true", "0", "1'b0", "false"}


def _is_possible_named_property_reference(expr: str, has_implication: bool) -> bool:
    if has_implication:
        return False
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*(?:\s*\([^;]*\))?", expr.strip()))


def _normalize_status(status: Any) -> str | None:
    if status is None:
        return None
    text = str(status).strip()
    if not text:
        return ""
    if "." in text and text.split(".")[-1].isupper():
        text = text.split(".")[-1].lower()
    normalized = re.sub(r"[\s-]+", "_", text.lower())
    aliases = {
        "not_covered": "not_covered",
        "cover_failed": "cover_failed",
        "unhit": "unhit",
        "hit": "hit",
        "pass": "pass",
        "passed": "passed",
        "fail": "fail",
        "failed": "failed",
        "cex": "cex",
        "counterexample": "counterexample",
        "syntax_failed": "syntax_failed",
        "parse_error": SYNTAX_ERROR,
        "elaboration_error": SYNTAX_ERROR,
        "not_flagged_vacuous": "not_flagged_vacuous",
        "non_vacuous": "non_vacuous",
        "not_vacuous": "not_vacuous",
        "dry_run": NOT_RUN,
        "none": NOT_RUN,
    }
    return aliases.get(normalized, normalized)


def _first_present(metadata: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if value is not None:
            return str(value)
    proof = metadata.get("proof_metadata")
    if isinstance(proof, Mapping):
        for key in keys:
            value = proof.get(key)
            if value is not None:
                return str(value)
    return None


def _metadata_has_no_antecedent(metadata: Mapping[str, Any]) -> bool:
    return (
        metadata.get("has_antecedent") is False
        or str(metadata.get("extraction_status") or "") == NO_ANTECEDENT
        or str(metadata.get("trigger_status") or "") == NO_ANTECEDENT
    )


def build_antecedent_metadata(sva: str, property_id: str) -> dict[str, Any]:
    """Compatibility wrapper used by the Design2SVA evaluator."""

    cover = generate_antecedent_cover(sva, source_property_id=property_id)
    extraction = cover.get("extraction") if isinstance(cover.get("extraction"), Mapping) else {}
    if cover.get("status") == NO_ANTECEDENT:
        return {
            "extraction_status": NO_ANTECEDENT,
            "reason": str(extraction.get("reason") or cover.get("reason") or NO_ANTECEDENT),
            "antecedent": None,
            "antecedent_kind": INVARIANT,
            "trigger_kind": INVARIANT,
            "trigger_status": NO_ANTECEDENT,
            "has_antecedent": False,
            "requires_antecedent_cover": False,
            "event_control": extraction.get("clocking_event"),
            "disable_iff": extraction.get("disable_iff"),
            "cover_property_id": "",
            "cover_sva": "",
            "cover_status": NOT_RUN,
            "antecedent_reachability": NO_ANTECEDENT,
        }
    if not cover.get("ok"):
        return {
            "extraction_status": UNKNOWN,
            "reason": str(cover.get("reason") or cover.get("unknown_reason") or UNKNOWN),
            "antecedent": None,
            "antecedent_kind": cover.get("condition_kind"),
            "trigger_kind": cover.get("trigger_kind"),
            "trigger_status": cover.get("trigger_status", UNKNOWN),
            "has_antecedent": cover.get("has_antecedent"),
            "requires_antecedent_cover": cover.get("requires_antecedent_cover"),
            "event_control": None,
            "disable_iff": None,
            "cover_property_id": "",
            "cover_sva": "",
            "cover_status": UNKNOWN,
            "antecedent_reachability": UNKNOWN,
        }

    extraction_status = str(extraction.get("status") or UNKNOWN)
    antecedent = str(cover.get("condition") or "")
    cover_sva = str(cover.get("cover_sva") or "")
    if extraction_status == APPROXIMATED:
        extraction_status = "unconditional"
        antecedent = "1'b1"
        cover_sva = render_compat_cover_property(
            str(cover.get("property_id") or f"cov_{property_id}_trigger"),
            str(extraction.get("clocking_event") or ""),
            str(extraction.get("disable_iff") or ""),
            antecedent,
        )

    return {
        "extraction_status": extraction_status,
        "reason": str(extraction.get("reason") or cover.get("reason") or ""),
        "antecedent": antecedent,
        "antecedent_kind": cover.get("condition_kind"),
        "trigger_kind": cover.get("trigger_kind"),
        "trigger_status": cover.get("trigger_status"),
        "has_antecedent": bool(cover.get("has_antecedent")),
        "requires_antecedent_cover": bool(cover.get("requires_antecedent_cover")),
        "event_control": extraction.get("clocking_event"),
        "disable_iff": extraction.get("disable_iff"),
        "cover_property_id": str(cover.get("property_id") or ""),
        "cover_sva": cover_sva,
        "cover_status": NOT_RUN if cover_sva else UNKNOWN,
        "antecedent_reachability": UNKNOWN,
    }


def render_compat_cover_property(
    property_id: str,
    event_control: str,
    disable_iff: str,
    antecedent: str,
) -> str:
    timing = " ".join(item for item in [event_control.strip(), disable_iff.strip()] if item)
    prefix = f"{timing} " if timing else ""
    return f"{property_id}: cover property ({prefix}({antecedent.strip()}));"


def apply_cover_status(
    metadata: dict[str, Any],
    cover_proof_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(metadata)
    if updated.get("has_antecedent") is False or updated.get("extraction_status") == NO_ANTECEDENT:
        updated["extraction_status"] = NO_ANTECEDENT
        updated["trigger_kind"] = updated.get("trigger_kind") or INVARIANT
        updated["trigger_status"] = NO_ANTECEDENT
        updated["has_antecedent"] = False
        updated["requires_antecedent_cover"] = False
        updated["cover_status"] = NOT_RUN
        updated["antecedent_reachability"] = NO_ANTECEDENT
        if cover_proof_metadata:
            updated["cover_proof_metadata"] = dict(cover_proof_metadata)
            updated["cover_status_ignored_reason"] = NO_ANTECEDENT
        return updated

    proof = cover_proof_metadata or {}
    status = str(
        proof.get("proof_status")
        or proof.get("status")
        or updated.get("cover_status")
        or ""
    )
    reachability = classify_reachability(
        cover_status=status,
        proof_status=status,
        vacuity_status=proof.get("vacuity_status"),
        syntax_status=proof.get("syntax_status"),
    )
    updated["cover_status"] = status or UNKNOWN
    updated["antecedent_reachability"] = (
        REACHABLE
        if reachability.get("is_reachable") is True
        else UNREACHABLE
        if reachability.get("is_reachable") is False
        else UNKNOWN
    )
    if proof:
        updated["cover_proof_metadata"] = proof
    return updated


def antecedent_reachable(metadata: dict[str, Any]) -> bool:
    if _metadata_has_no_antecedent(metadata):
        return True
    return str(metadata.get("antecedent_reachability")) == REACHABLE


def antecedent_unreachable(metadata: dict[str, Any]) -> bool:
    if _metadata_has_no_antecedent(metadata):
        return False
    return str(metadata.get("antecedent_reachability")) == UNREACHABLE


extract_antecedent = extract_assertion_trigger
extract_assertion_antecedent = extract_assertion_trigger
extract_antecedent_condition = extract_assertion_trigger
extract_trigger_condition = extract_assertion_trigger
build_antecedent_cover_property = generate_antecedent_cover
build_companion_cover_property = generate_antecedent_cover
generate_companion_cover = generate_antecedent_cover
generate_cover_property = generate_antecedent_cover
generate_cover_property_for_antecedent = generate_antecedent_cover
classify_cover_reachability = classify_reachability
classify_cover_proof_reachability = classify_reachability
build_cover_before_assert_metadata = cover_before_assert_metadata

__all__ = [
    "APPROXIMATED",
    "BOUNDED_UNCOVERED",
    "EXTRACTED",
    "GENERATED",
    "INVARIANT",
    "NO_ANTECEDENT",
    "NOT_RUN",
    "REACHABLE",
    "SYNTAX_ERROR",
    "UNKNOWN",
    "UNREACHABLE",
    "VACUOUS",
    "build_cover_before_assert_metadata",
    "antecedent_reachable",
    "antecedent_unreachable",
    "apply_cover_status",
    "build_antecedent_metadata",
    "build_antecedent_cover_property",
    "build_companion_cover_property",
    "classify_cover_reachability",
    "classify_cover_proof_reachability",
    "classify_reachability",
    "cover_before_assert_metadata",
    "extract_antecedent",
    "extract_assertion_antecedent",
    "extract_assertion_trigger",
    "extract_antecedent_condition",
    "extract_trigger_condition",
    "generate_antecedent_cover",
    "generate_companion_cover",
    "generate_cover_property",
    "generate_cover_property_for_antecedent",
]
