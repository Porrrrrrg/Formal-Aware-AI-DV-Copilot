# Experiment Registry

Last updated: 20260510T214913Z. Git SHA: `3bb6821e687db39d384abd7f6fcb00cee6f7c6c1`.

| Experiment | Run ID | Artifact | Status |
| --- | --- | --- | --- |
| triage_all_systems_baseline | triage_all_systems_baseline_20260510T214913Z | reports\research\runs\20260510T214913Z\triage_all_systems.json | pass |
| triage_structured_ablation | triage_structured_ablation_20260510T214913Z | reports\research\runs\20260510T214913Z\triage_ablation.json | pass |
| coverage_all_systems_baseline | coverage_all_systems_baseline_20260510T214913Z | reports\research\runs\20260510T214913Z\coverage_all_systems.json | pass |
| sva_generation_baseline | sva_generation_baseline_20260510T214913Z | reports\research\runs\20260510T214913Z\sva_generation.json | pass |
| sva_repair_baseline | sva_repair_baseline_20260510T214913Z | reports\research\runs\20260510T214913Z\sva_repair.json | pass |
| sva_repair_loop_ablation | sva_repair_loop_ablation_20260510T214913Z | reports\research\runs\20260510T214913Z\sva_repair_ablation.json | pass |
| prompt_audit | prompt_audit_20260510T214913Z | reports\research\runs\20260510T214913Z\prompt_audit.stdout.txt | pass |
| retrieval_local_dv_revalidation | run_20260511T000415Z_0b7d76718814_2e9785 | reports\eval\local_dv\run_20260511T000415Z_0b7d76718814_2e9785\summary.md | pass |

The retrieval revalidation row was regenerated after the #13 retrieval benchmark schema landed. It uses the local deterministic sparse index only and writes canonical `ProblemSpec`, `Candidate`, and `VerifierOutcome` artifacts; it is not LLM, Qwen, cloud, or JasperGold performance evidence.

## Required Next Runs

| Route | Command Shape | Required Manifest Fields |
| --- | --- | --- |
| local-qwen | python evaluation/run_agent_eval.py --all-systems --llm --llm-command <qwen_adapter> --out artifacts/runs/<date>/<run_id>/triage_qwen.json | model, quantization, serving stack, max_model_len, git_sha, run_id, latency p50/p95, cost proxy, failures |
| cloud fallback | python scripts/run_codex_llm_eval.py --task triage --limit <n> --acknowledge-external-send --out artifacts/runs/<date>/<run_id>/triage_cloud.json | provider/model, prompt audit, external-send approval, git_sha, run_id, latency, cost, JSON validity, fallback/error rate |
| moore JasperGold | python scripts/build_all_evidence_packets.py --strict-reports --out-dir artifacts/runs/<date>/<run_id>/case_packets | Jasper binary/version, report paths, trace count, git_sha, run_id, command status |
