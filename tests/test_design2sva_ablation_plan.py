from __future__ import annotations

import json

from evaluation.run_design2sva_ablation_plan import REQUIRED_METRICS, main


def test_design2sva_ablation_plan_outputs_required_variants(tmp_path, monkeypatch) -> None:
    out = tmp_path / "ablation.json"
    plan = tmp_path / "ablation.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_ablation_plan.py",
            "--limit",
            "2",
            "--k",
            "2",
            "--out",
            str(out),
            "--plan",
            str(plan),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["mode"] == "dry_run_replay_plan"
    assert payload["llm_prompts_sent"] is False
    assert payload["required_metrics"] == REQUIRED_METRICS
    assert {variant["variant"] for variant in payload["variants"]} == {
        "direct_prompt",
        "retrieval_context",
        "retrieval_plus_reachability_guidance",
        "retrieval_plus_anti_vacuity_repair",
        "reference_oracle",
        "native_oracle",
    }
    for variant in payload["variants"]:
        assert variant["llm_prompts_sent"] is False
        assert set(REQUIRED_METRICS) <= set(variant["metrics"])

    markdown = plan.read_text(encoding="utf-8")
    assert "direct_prompt" in markdown
    assert "production signoff" in markdown
