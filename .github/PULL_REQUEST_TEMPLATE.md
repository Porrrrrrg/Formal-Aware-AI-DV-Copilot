## Summary

<!-- What changed and why? -->

## Validation

- [ ] `python -m ruff check .`
- [ ] `python -m pytest`
- [ ] `python scripts/build_all_evidence_packets.py --out-dir artifacts/schema/case_packets`
- [ ] `python evaluation/run_agent_eval.py --all-systems --packet-source minimal`
- [ ] JasperGold/moore validation is not required for this PR.
- [ ] JasperGold/moore validation is required and tracked separately.

## Security Checklist

- [ ] No long-lived cloud secrets, personal tokens, license files, or `.env` files were added.
- [ ] No default workflow step sends benchmark content to an external LLM or unapproved endpoint.
- [ ] Workflow permissions are least privilege and set explicitly.
- [ ] Attestation, CodeQL, and secret scanning coverage were preserved or improved.
- [ ] If this changes schemas, generated agent outputs and evidence packets were checked for schema drift.

## Labels

Suggested labels: `ci`, `security`, `schema`, `benchmark`, `jasper`, `needs-moore`, `external-llm`, `docs`.

## Cross-Agent Review

REVIEW_REQUESTED: Please check whether CI covers schema drift, adapter smoke, and artifact attestation.
