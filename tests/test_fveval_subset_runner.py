import json
from pathlib import Path

from evaluation.run_fveval_subset import (
    build_prompt_payload,
    load_cases,
    main,
    render_markdown,
    summarize,
)


CASES_PATH = Path("benchmarks/fveval_subset/cases.json")


def test_reference_sva_not_in_prompt_context() -> None:
    cases = load_cases(CASES_PATH)

    for case in cases:
        payload = build_prompt_payload(case)
        serialized = json.dumps(payload)

        assert "reference_sva" not in payload
        assert "expected_sva" not in payload
        assert "source" not in payload
        if case.get("reference_sva"):
            assert case["reference_sva"] not in serialized
        if case.get("expected_sva"):
            assert case["expected_sva"] not in serialized


def test_no_answer_leakage_in_emitted_prompt_payloads(tmp_path, monkeypatch) -> None:
    prompt_path = tmp_path / "prompts.json"
    markdown_path = tmp_path / "results.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_fveval_subset.py",
            "--emit-prompts",
            str(prompt_path),
            "--markdown",
            str(markdown_path),
        ],
    )

    assert main() == 0
    prompts = json.loads(prompt_path.read_text(encoding="utf-8"))
    source_cases = load_cases(CASES_PATH)

    assert len(prompts) == 30
    for case, prompt in zip(source_cases, prompts, strict=True):
        serialized = json.dumps(prompt)
        assert "reference_sva" not in prompt
        assert "expected_sva" not in prompt
        assert "source" not in prompt
        if case.get("reference_sva"):
            assert case["reference_sva"] not in serialized
        if case.get("expected_sva"):
            assert case["expected_sva"] not in serialized


def test_case_metadata_has_source_attribution() -> None:
    cases = load_cases(CASES_PATH)

    assert len(cases) == 30
    for case in cases:
        source = case.get("source")
        assert source["repository"] == "https://github.com/NVlabs/FVEval"
        assert source["commit"] == "141afe7dcf03a0b86547b94657d9d610b6087724"
        assert source["license"] == "Apache-2.0"
        assert source["path"]


def test_runner_markdown_includes_limitations() -> None:
    cases = load_cases(CASES_PATH)
    rows = [
        {
            "case_id": case["case_id"],
            "subset": case["subset"],
            "syntax_pass": True,
            "exact_match": None,
            "reference_available": False,
            "valid_json": True,
            "fallback": True,
            "has_hallucinated_signal": False,
            "jasper_proof_status": "not_run",
        }
        for case in cases
    ]
    summary = summarize(rows, invalid_prediction_json=0)
    markdown = render_markdown(
        summary,
        rows,
        {
            "source_repository": "https://github.com/NVlabs/FVEval",
            "source_commit": "141afe7dcf03a0b86547b94657d9d610b6087724",
        },
    )

    assert "FVEval-compatible subset" in markdown
    assert "Case count: 30" in markdown
    assert "External reference retained as evaluation metadata only" in markdown
    assert "Reference answers omitted from prompt payloads" in markdown
    assert "not apples-to-apples with FVEval official results" in markdown
    assert "does not reproduce FVEval's commercial functional-equivalence flow" in markdown
    assert "Design2SVA exact/reference match is not treated as functional equivalence" in markdown
    assert "No JasperGold, Codex, or Qwen execution is performed by this runner" in markdown
