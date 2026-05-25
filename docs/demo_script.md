# Demo Script

## Three-Minute Demo

1. Open `README.md` and state the principle: the LLM proposes; JasperGold is the formal oracle when formal checks are run.
2. Show `docs/architecture.md` and point to the evidence-packet boundary.
3. Show `evaluation/results/final_results.md` and explain the three evidence sources: local Qwen, deterministic/local validation, and JasperGold-backed SVA repair re-check.
4. Run local validation:

```bash
python -m pytest
python scripts/refresh_eval_results.py --allow-rebuild-packets
```

5. Show `docs/reports/final_research_summary.md` for supported claims and non-claims.

## Eight-Minute Demo

Add these steps:

1. Run backend preflight:

```bash
python scripts/doctor_llm_backend.py --json
python scripts/test_llm_backend_contract.py
```

2. Show one benchmark case under `benchmarks/` and the generated evidence packet contract from `tools/build_evidence_packet.py`.
3. Explain how raw model/Jasper outputs stay local while curated summaries stay in git.
4. If a JasperGold environment is available, run:

```bash
bash scripts/run_jasper_smoke.sh
```

If JasperGold is unavailable, say so explicitly.
