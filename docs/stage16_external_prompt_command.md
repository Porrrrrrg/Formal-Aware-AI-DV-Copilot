# Stage 16 External Codex Design2SVA Command

The Stage 16 external Codex run was performed only after the local prompt audit
reported zero gold-label leakage.

## Prompt Audit

Run locally before any external prompt submission:

```powershell
python scripts/export_codex_prompts.py --task design2sva --design2sva-cases benchmarks/design2sva_cases.json --limit 12 --design2sva-context-budget 24 --out-dir evaluation/prompt_previews/design2sva_expanded --audit-markdown evaluation/prompt_previews/design2sva_expanded_prompt_audit.md --require-no-gold-labels
```

Audit output:

- `evaluation/prompt_previews/design2sva_expanded_prompt_audit.md`
- 12 prompts over 12 cases
- `reference_sva` absent
- `expected_proof_status` absent
- exact reference SVA text absent
- Jasper evidence absent

## Approved External Run

The approved Stage 16 run command was:

```powershell
python scripts/run_codex_llm_eval.py --task design2sva --cases benchmarks/design2sva_cases.json --k 3 --max-repair-rounds 0 --timeout 900 --out evaluation/results/design2sva_eval_codex_expanded_subset.json --prompt-audit evaluation/prompt_previews/design2sva_expanded_prompt_audit.md --acknowledge-external-send
```

Measured generation-only output:

- `evaluation/results/design2sva_eval_codex_expanded_subset.json`
- `mode = "real_llm"`
- `formal_check_mode = "not_run"`
- `summary.num_cases = 12`
- `summary.k = 3`
- `summary.source_counts.llm = 36`
- `summary.real_llm_count = 36`
- `summary.valid_json_rate = 1.0`
- `summary.fallback_rate = 0.0`
- `summary.hallucinated_signal_rate = 0.0`
- `summary.candidate_count_by_case` has 12 entries with 3 candidates each

The LLM-only artifact must not be cited as a formal success result. Formal
success is measured only in `design2sva_eval_codex_expanded_jasper.json`.
