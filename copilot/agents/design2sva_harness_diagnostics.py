"""Design2SVA reset, clock, and harness diagnostic cover generation.

The helpers in this module only build cover-check prediction dictionaries. They
do not run a formal backend, so generated diagnostics report reachability as
``not_run``/``unknown`` until a caller attaches real cover results.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

UNKNOWN = "unknown"
NOT_RUN = "not_run"
REACHABLE = "reachable"
UNREACHABLE = "unreachable"
BOUNDED_UNCOVERED = "bounded_uncovered"

_IDENTIFIER_RE = re.compile(r"[^A-Za-z0-9_$]+")


def build_harness_diagnostic_predictions(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return cover-check predictions for basic harness reachability questions."""

    predictions = [
        build_reset_release_prediction(case),
        build_post_reset_cycle_prediction(case),
        build_clock_advance_prediction(case),
    ]
    predictions.extend(build_visible_signal_nonreset_predictions(case))
    return predictions


def build_harness_diagnostic_bundle(case: Mapping[str, Any]) -> dict[str, Any]:
    """Return diagnostics grouped with case metadata for JSON reporting."""

    info = _case_info(case)
    predictions = build_harness_diagnostic_predictions(case)
    return {
        "case_id": str(case.get("case_id") or ""),
        "property_id": str(case.get("property_id") or ""),
        "reachability_status": NOT_RUN,
        "reset_release_reachable": UNKNOWN,
        "post_reset_reachable": UNKNOWN,
        "clock_event_assumed": info["clock_event"],
        "reset_polarity_used": info["reset_polarity"],
        "disable_iff_used": bool(info["disable_iff"]),
        "predictions": predictions,
    }


def build_reset_release_prediction(case: Mapping[str, Any]) -> dict[str, Any]:
    """Build a cover property for reset assertion followed by reset release."""

    info = _case_info(case)
    reset_sequence = _reset_release_sequence(info)
    property_id = _diagnostic_property_id(info, "reset_release")
    sva = _render_cover_property(
        property_id=property_id,
        clock_event=info["clock_event"],
        disable_iff=None,
        condition=reset_sequence,
    )
    return _prediction(
        case=case,
        info=info,
        diagnostic_kind="reset_release",
        property_id=property_id,
        sva=sva,
        disable_iff=None,
        condition=reset_sequence,
    )


def build_post_reset_cycle_prediction(case: Mapping[str, Any]) -> dict[str, Any]:
    """Build a cover property that asks whether any non-reset cycle exists."""

    info = _case_info(case)
    property_id = _diagnostic_property_id(info, "post_reset_cycle")
    condition = "1'b1"
    sva = _render_cover_property(
        property_id=property_id,
        clock_event=info["clock_event"],
        disable_iff=info["disable_iff"],
        condition=condition,
    )
    return _prediction(
        case=case,
        info=info,
        diagnostic_kind="post_reset_cycle",
        property_id=property_id,
        sva=sva,
        disable_iff=info["disable_iff"],
        condition=condition,
    )


def build_clock_advance_prediction(case: Mapping[str, Any]) -> dict[str, Any]:
    """Build a cover property that asks for two consecutive non-reset samples."""

    info = _case_info(case)
    property_id = _diagnostic_property_id(info, "clock_advance")
    condition = "1'b1 ##1 1'b1"
    sva = _render_cover_property(
        property_id=property_id,
        clock_event=info["clock_event"],
        disable_iff=info["disable_iff"],
        condition=condition,
    )
    return _prediction(
        case=case,
        info=info,
        diagnostic_kind="clock_advance",
        property_id=property_id,
        sva=sva,
        disable_iff=info["disable_iff"],
        condition=condition,
    )


def build_visible_signal_nonreset_predictions(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build one non-reset-value cover property for each visible non-clock/reset signal."""

    info = _case_info(case)
    predictions = []
    for signal in _visible_interface_signals(case, info):
        property_id = _diagnostic_property_id(info, f"sig_{signal}_nonreset")
        condition = f"{signal} != '0"
        sva = _render_cover_property(
            property_id=property_id,
            clock_event=info["clock_event"],
            disable_iff=info["disable_iff"],
            condition=condition,
        )
        predictions.append(
            _prediction(
                case=case,
                info=info,
                diagnostic_kind="visible_signal_non_reset",
                property_id=property_id,
                sva=sva,
                disable_iff=info["disable_iff"],
                condition=condition,
                signal=signal,
            )
        )
    return predictions


def apply_diagnostic_cover_status(
    prediction: Mapping[str, Any],
    cover_status: str | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return ``prediction`` annotated with reachability from a cover result."""

    updated = dict(prediction)
    status = _cover_status_from_metadata(cover_status)
    reachability = _reachability_from_cover_status(status)
    updated["cover_status"] = status
    updated["reachability_status"] = reachability
    updated["reachability_ok"] = reachability == REACHABLE
    updated["is_reachable"] = (
        True
        if reachability == REACHABLE
        else False
        if reachability == UNREACHABLE
        else None
    )

    kind = str(updated.get("diagnostic_kind") or "")
    if kind == "reset_release":
        updated["reset_release_reachable"] = (
            reachability if reachability in {REACHABLE, UNREACHABLE} else UNKNOWN
        )
    elif kind in {"post_reset_cycle", "clock_advance", "visible_signal_non_reset"}:
        updated["post_reset_reachable"] = (
            reachability if reachability in {REACHABLE, UNREACHABLE} else UNKNOWN
        )
    metadata = updated.get("harness_diagnostic_metadata")
    if isinstance(metadata, Mapping):
        updated["harness_diagnostic_metadata"] = {**metadata, **_metadata_view(updated)}
    return updated


def _case_info(case: Mapping[str, Any]) -> dict[str, str | None]:
    clock_reset = case.get("clock_reset", {})
    if not isinstance(clock_reset, Mapping):
        clock_reset = {}

    clock = str(clock_reset.get("clock") or "").strip()
    clock_edge = str(clock_reset.get("clock_edge") or "posedge").strip() or "posedge"
    reset = str(clock_reset.get("reset") or "").strip()
    reset_polarity = str(clock_reset.get("reset_polarity") or UNKNOWN).strip() or UNKNOWN
    reset_asserted = _reset_asserted_expr(reset, reset_polarity)
    reset_deasserted = _reset_deasserted_expr(reset, reset_polarity)

    return {
        "case_id": str(case.get("case_id") or ""),
        "source_property_id": str(case.get("property_id") or "generated_property"),
        "clock": clock,
        "clock_edge": clock_edge,
        "clock_event": f"@({clock_edge} {clock})" if clock else "@(posedge clk)",
        "reset": reset,
        "reset_polarity": reset_polarity,
        "reset_asserted": reset_asserted,
        "reset_deasserted": reset_deasserted,
        "disable_iff": f"disable iff ({reset_asserted})" if reset_asserted else None,
    }


def _reset_asserted_expr(reset: str, reset_polarity: str) -> str | None:
    if not reset:
        return None
    if reset_polarity == "active_low":
        return f"!{reset}"
    return reset


def _reset_deasserted_expr(reset: str, reset_polarity: str) -> str | None:
    if not reset:
        return None
    if reset_polarity == "active_low":
        return reset
    return f"!{reset}"


def _reset_release_sequence(info: Mapping[str, str | None]) -> str:
    asserted = info.get("reset_asserted")
    deasserted = info.get("reset_deasserted")
    if asserted and deasserted:
        return f"{asserted} ##1 {deasserted}"
    return "1'b1"


def _render_cover_property(
    property_id: str,
    clock_event: str,
    disable_iff: str | None,
    condition: str,
) -> str:
    timing = " ".join(part for part in [clock_event.strip(), (disable_iff or "").strip()] if part)
    return f"{property_id}: cover property ({timing} ({condition.strip()}));"


def _prediction(
    case: Mapping[str, Any],
    info: Mapping[str, str | None],
    diagnostic_kind: str,
    property_id: str,
    sva: str,
    disable_iff: str | None,
    condition: str,
    signal: str | None = None,
) -> dict[str, Any]:
    metadata = {
        "diagnostic_kind": diagnostic_kind,
        "case_id": str(case.get("case_id") or ""),
        "source_property_id": str(case.get("property_id") or ""),
        "clock": info.get("clock") or "",
        "clock_edge": info.get("clock_edge") or "",
        "clock_event": info.get("clock_event") or "",
        "clock_event_assumed": info.get("clock_event") or "",
        "reset": info.get("reset") or "",
        "reset_polarity_used": info.get("reset_polarity") or UNKNOWN,
        "reset_asserted": info.get("reset_asserted"),
        "reset_deasserted": info.get("reset_deasserted"),
        "disable_iff": disable_iff,
        "disable_iff_used": bool(disable_iff),
        "condition": condition,
        "signal": signal,
        "reset_release_reachable": UNKNOWN,
        "post_reset_reachable": UNKNOWN,
        "reachability_status": NOT_RUN,
        "reachability_ok": False,
        "is_reachable": None,
        "cover_status": NOT_RUN,
        "proof_metadata": {
            "backend": "none",
            "status": NOT_RUN,
            "syntax_status": NOT_RUN,
            "proof_status": None,
            "vacuity_status": None,
        },
    }
    return {
        "case_id": metadata["case_id"],
        "property_id": property_id,
        "source_property_id": metadata["source_property_id"],
        "diagnostic_kind": diagnostic_kind,
        "check_kind": "cover",
        "sva": sva,
        "helper_code": "",
        **metadata,
        "harness_diagnostic_metadata": metadata,
    }


def _metadata_view(prediction: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "cover_status",
        "reachability_status",
        "reachability_ok",
        "is_reachable",
        "reset_release_reachable",
        "post_reset_reachable",
    )
    return {key: prediction[key] for key in keys if key in prediction}


def _visible_interface_signals(
    case: Mapping[str, Any],
    info: Mapping[str, str | None],
) -> list[str]:
    excluded = {str(info.get("clock") or ""), str(info.get("reset") or "")}
    visible = case.get("visible_signals", [])
    if not isinstance(visible, list):
        return []

    signals: list[str] = []
    seen: set[str] = set()
    for raw in visible:
        signal = str(raw).strip()
        if not signal or signal in excluded or signal in seen:
            continue
        seen.add(signal)
        signals.append(signal)
    return signals


def _diagnostic_property_id(info: Mapping[str, str | None], suffix: str) -> str:
    source = str(info.get("source_property_id") or "generated_property")
    return _sanitize_identifier(f"cov_{source}_{suffix}")


def _sanitize_identifier(identifier: str) -> str:
    cleaned = _IDENTIFIER_RE.sub("_", identifier.strip()).strip("_")
    if not cleaned:
        cleaned = "cov_harness_diagnostic"
    if not re.match(r"[A-Za-z_]", cleaned):
        cleaned = "cov_" + cleaned
    return cleaned


def _cover_status_from_metadata(status: str | Mapping[str, Any] | None) -> str:
    if isinstance(status, Mapping):
        for key in ("cover_status", "proof_status", "status"):
            value = status.get(key)
            if value is not None:
                return _normalize_status(value)
        proof = status.get("proof_metadata")
        if isinstance(proof, Mapping):
            return _cover_status_from_metadata(proof)
        return NOT_RUN
    return _normalize_status(status)


def _reachability_from_cover_status(status: str) -> str:
    if status in {"covered", REACHABLE, "hit", "passed", "pass"}:
        return REACHABLE
    if status in {UNREACHABLE}:
        return UNREACHABLE
    if status in {"uncovered", "not_covered", "cover_failed", "unhit", "missed"}:
        return BOUNDED_UNCOVERED
    if status in {"", NOT_RUN, "dry_run", "none"}:
        return NOT_RUN
    return UNKNOWN


def _normalize_status(status: Any) -> str:
    if status is None:
        return NOT_RUN
    text = str(status).strip()
    if not text:
        return ""
    if "." in text and text.split(".")[-1].isupper():
        text = text.split(".")[-1].lower()
    normalized = re.sub(r"[\s-]+", "_", text.lower())
    return {"dry_run": NOT_RUN, "none": NOT_RUN}.get(normalized, normalized)


generate_harness_diagnostic_predictions = build_harness_diagnostic_predictions
generate_design2sva_harness_diagnostics = build_harness_diagnostic_predictions
build_reset_release_cover_prediction = build_reset_release_prediction
build_post_reset_cover_prediction = build_post_reset_cycle_prediction
build_clock_advance_cover_prediction = build_clock_advance_prediction
build_visible_signal_cover_predictions = build_visible_signal_nonreset_predictions

__all__ = [
    "BOUNDED_UNCOVERED",
    "NOT_RUN",
    "REACHABLE",
    "UNKNOWN",
    "UNREACHABLE",
    "apply_diagnostic_cover_status",
    "build_clock_advance_cover_prediction",
    "build_clock_advance_prediction",
    "build_harness_diagnostic_bundle",
    "build_harness_diagnostic_predictions",
    "build_post_reset_cover_prediction",
    "build_post_reset_cycle_prediction",
    "build_reset_release_cover_prediction",
    "build_reset_release_prediction",
    "build_visible_signal_cover_predictions",
    "build_visible_signal_nonreset_predictions",
    "generate_design2sva_harness_diagnostics",
    "generate_harness_diagnostic_predictions",
]
