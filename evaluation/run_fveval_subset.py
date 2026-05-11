#!/usr/bin/env python3
"""Evaluate a small imported FVEval-compatible subset.

The runner treats reference assertions as evaluation-only data. Prompt payloads
emitted by this script omit reference_sva and expected_sva to avoid answer
leakage.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.sva_library import extract_identifiers, normalize_sva, syntax_scaffold_ok  # noqa: E402
from evaluation.metrics import valid_json_rate  # noqa: E402

DEFAULT_CASES = Path("benchmarks/fveval_subset/cases.json")
DEFAULT_MARKDOWN = Path("evaluation/results/fveval_subset_results.md")

EVIDENCE_FIELDS = [
    "Source benchmark: FVEval-compatible subset.",
    "Case count: 30.",
    "External reference retained as evaluation metadata only.",
    "Reference answers omitted from prompt payloads.",
    "No JasperGold, Codex, or Qwen execution is performed by this runner.",
]

LIMITATIONS = [
    "This local subset runner is not apples-to-apples with FVEval official results.",
    "This local subset runner does not reproduce FVEval's commercial functional-equivalence flow.",
    "Design2SVA exact/reference match is not treated as functional equivalence.",
    "Jasper proof is reported as `not_run` unless a future local harness integration is added and explicitly enabled.",
]

SVA_NON_SIGNAL_IDENTIFIERS = {
    "assert",
    "asrt",
    "assume",
    "automatic",
    "begin",
    "bins",
    "bit",
    "cover",
    "disable",
    "end",
    "endproperty",
    "eventually",
    "iff",
    "int",
    "integer",
    "logic",
    "max",
    "min",
    "not",
    "or",
    "posedge",
    "property",
    "reset",
    "s_eventually",
    "sequence",
}


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(resolve_repo_path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    cases = [case for case in data if isinstance(case, dict)]
    if len(cases) != len(data):
        raise ValueError(f"{path} contains non-object case entries")
    return cases


def load_predictions(path: Path | None) -> tuple[dict[str, dict[str, Any]], int, int]:
    if path is None:
        return {}, 0, 0
    prediction_path = resolve_repo_path(path)
    text = prediction_path.read_text(encoding="utf-8")
    if prediction_path.suffix.lower() == ".jsonl":
        parsed: list[dict[str, Any]] = []
        invalid = 0
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            if isinstance(item, dict):
                parsed.append(item)
            else:
                invalid += 1
        return index_predictions(parsed), len(parsed), invalid

    data = json.loads(text)
    if isinstance(data, dict) and isinstance(data.get("predictions"), list):
        data = data["predictions"]
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array or an object with a predictions array")
    parsed = [item for item in data if isinstance(item, dict)]
    invalid = len(data) - len(parsed)
    return index_predictions(parsed), len(parsed), invalid


def index_predictions(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        case_id = item.get("case_id")
        prediction = item.get("prediction")
        if isinstance(prediction, dict):
            case_id = case_id or prediction.get("case_id")
            payload = prediction
        else:
            payload = item
        if case_id:
            indexed[str(case_id)] = payload
    return indexed


def fallback_prediction(case: dict[str, Any], reason: str) -> dict[str, Any]:
    property_id = str(case.get("property_id") or "fveval_fallback_property")
    clock = str(case.get("clock") or "clk")
    reset = str(case.get("reset") or "")
    reset_expr = ""
    if reset:
        reset_condition = f"!{reset}" if reset.endswith("_") or reset.endswith("n") else reset
        reset_expr = f" disable iff ({reset_condition})"
    return {
        "case_id": case.get("case_id"),
        "property_id": property_id,
        "sva": f"{property_id}: assert property (@(posedge {clock}){reset_expr} 1'b1);",
        "explanation": f"Deterministic fallback used: {reason}.",
        "fallback": True,
        "fallback_reason": reason,
    }


def prediction_for_case(
    case: dict[str, Any],
    predictions: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    case_id = str(case.get("case_id"))
    prediction = dict(predictions.get(case_id, {}))
    if not prediction:
        return fallback_prediction(case, "missing prediction"), False
    if not str(prediction.get("sva", "")).strip():
        return fallback_prediction(case, "missing sva field"), True
    prediction.setdefault("case_id", case_id)
    prediction.setdefault("property_id", case.get("property_id"))
    prediction.setdefault("fallback", False)
    return prediction, True


def build_prompt_payload(case: dict[str, Any]) -> dict[str, Any]:
    omitted = {"expected_sva", "reference_sva", "source", "notes"}
    payload = {key: value for key, value in case.items() if key not in omitted}
    payload["reference_available"] = bool(case.get("reference_sva") or case.get("expected_sva"))
    return payload


def write_prompt_payloads(cases: list[dict[str, Any]], out_path: Path | None) -> None:
    if out_path is None:
        return
    payloads = [build_prompt_payload(case) for case in cases]
    path = resolve_repo_path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payloads, indent=2) + "\n", encoding="utf-8")


def hallucinated_identifiers(case: dict[str, Any], sva: str) -> list[str]:
    allowed = set(case.get("allowed_signals", []))
    allowed.update(case.get("signals", []))
    allowed.add(str(case.get("property_id", "")))
    allowed.update(SVA_NON_SIGNAL_IDENTIFIERS)
    return sorted(identifier for identifier in extract_identifiers(sva) if identifier not in allowed)


def evaluate_case(
    case: dict[str, Any],
    prediction: dict[str, Any],
    valid_json: bool,
    jasper_mode: str,
) -> dict[str, Any]:
    sva = str(prediction.get("sva", ""))
    reference = str(case.get("reference_sva") or case.get("expected_sva") or "")
    hallucinated = hallucinated_identifiers(case, sva)
    exact_match = None
    if reference:
        exact_match = normalize_sva(sva) == normalize_sva(reference)
    return {
        "case_id": case.get("case_id"),
        "subset": case.get("subset"),
        "design_id": case.get("design_id"),
        "source_task_id": case.get("source_task_id"),
        "syntax_pass": syntax_scaffold_ok(sva),
        "exact_match": exact_match,
        "reference_available": bool(reference),
        "valid_json": valid_json,
        "fallback": bool(prediction.get("fallback")),
        "has_hallucinated_signal": bool(hallucinated),
        "hallucinated_identifiers": hallucinated,
        "jasper_proof_status": jasper_mode,
    }


def summarize(rows: list[dict[str, Any]], invalid_prediction_json: int) -> dict[str, Any]:
    total = len(rows)
    reference_rows = [row for row in rows if row["reference_available"]]
    exact_rows = [row for row in reference_rows if row["exact_match"] is not None]
    by_subset = collections.Counter(str(row["subset"]) for row in rows)
    return {
        "num_cases": total,
        "cases_by_subset": dict(sorted(by_subset.items())),
        "syntax_pass_rate": rate(rows, "syntax_pass"),
        "exact_match_rate": rate(exact_rows, "exact_match"),
        "exact_match_cases": len(exact_rows),
        "valid_json_rate": valid_json_rate(total, sum(1 for row in rows if row["valid_json"])),
        "fallback_rate": rate(rows, "fallback"),
        "hallucinated_signal_rate": rate(rows, "has_hallucinated_signal"),
        "invalid_prediction_json": invalid_prediction_json,
    }


def rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get(key)) / len(rows)


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]], source: dict[str, Any]) -> str:
    subset_lines = "\n".join(
        f"- {subset}: {count}" for subset, count in summary["cases_by_subset"].items()
    )
    evidence_lines = "\n".join(f"- {field}" for field in EVIDENCE_FIELDS)
    limitation_lines = "\n".join(f"- {limitation}" for limitation in LIMITATIONS)
    return f"""# FVEval Subset Results

## Summary

Source: [{source["source_repository"]}]({source["source_repository"]}) at `{source["source_commit"]}`.

{subset_lines}

| Metric | Value |
| --- | ---: |
| Cases | {summary["num_cases"]} |
| Syntax pass | {summary["syntax_pass_rate"]:.3f} |
| Exact/reference match | {summary["exact_match_rate"]:.3f} |
| Exact/reference eligible cases | {summary["exact_match_cases"]} |
| Valid JSON | {summary["valid_json_rate"]:.3f} |
| Fallback | {summary["fallback_rate"]:.3f} |
| Hallucinated signal rate | {summary["hallucinated_signal_rate"]:.3f} |
| Invalid prediction JSON rows | {summary["invalid_prediction_json"]} |

## Evidence Fields

{evidence_lines}

## Case Rows

| Case | Subset | Syntax | Exact | JSON | Fallback | Hallucinated | Jasper |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
{render_rows(rows)}

## Limitations

{limitation_lines}
"""


def render_rows(rows: list[dict[str, Any]]) -> str:
    rendered = []
    for row in rows:
        exact = "n/a" if row["exact_match"] is None else str(bool(row["exact_match"]))
        rendered.append(
            "| {case_id} | {subset} | {syntax} | {exact} | {json_ok} | {fallback} | "
            "{hallucinated} | {jasper} |".format(
                case_id=row["case_id"],
                subset=row["subset"],
                syntax=bool(row["syntax_pass"]),
                exact=exact,
                json_ok=bool(row["valid_json"]),
                fallback=bool(row["fallback"]),
                hallucinated=bool(row["has_hallucinated_signal"]),
                jasper=row["jasper_proof_status"],
            )
        )
    return "\n".join(rendered)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--emit-prompts", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    write_prompt_payloads(cases, args.emit_prompts)

    predictions, valid_prediction_json, invalid_prediction_json = load_predictions(args.predictions)
    rows = []
    outputs = []
    for case in cases:
        prediction, parsed = prediction_for_case(case, predictions)
        valid_json = parsed or args.predictions is None
        row = evaluate_case(case, prediction, valid_json=valid_json, jasper_mode="not_run")
        rows.append(row)
        outputs.append(
            {
                "case_id": case.get("case_id"),
                "prompt": build_prompt_payload(case),
                "prediction": prediction,
                "metrics": row,
            }
        )

    manifest_path = ROOT / "benchmarks" / "fveval_subset" / "source_manifest.json"
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = summarize(rows, invalid_prediction_json)
    summary["valid_prediction_json_rows"] = valid_prediction_json
    payload = {
        "summary": summary,
        "evidence_fields": EVIDENCE_FIELDS,
        "limitations": LIMITATIONS,
        "rows": rows,
        "outputs": outputs,
    }

    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if args.markdown:
        markdown_path = resolve_repo_path(args.markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(summary, rows, source), encoding="utf-8")

    print(
        json.dumps(
            {"summary": summary, "evidence_fields": EVIDENCE_FIELDS, "limitations": LIMITATIONS},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
