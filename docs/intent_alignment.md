# Intent Alignment Evaluation

Stage 5C adds a bounded static/offline evaluator for repaired or generated SVA candidates. It compares candidate SVA text against available intent metadata, reference SVA, allowed signals, and optional proof-status context.

The evaluator is heuristic unless a future flow adds an explicit formal equivalence check. It extracts conservative SVA surface features such as referenced signals, clock/reset context, antecedent and consequent fragments, implication and delay operators, comparisons, constants, onehot usage, and obvious tautology patterns. It then emits an `IntentAlignmentResult` with a label, score, weak-property flags, vacuity-risk flags, rationale, and evidence references.

Jasper proof is intentionally kept separate from intent alignment. A property can prove while checking the wrong behavior, omitting the intended trigger, using a weaker consequent, changing a delay, or referencing a related but incorrect signal. Proof status may appear in `proof_status_context`, but it does not force an `aligned` label and is not treated as semantic equivalence to the original intent.

Manual review remains required for ambiguous cases, hallucinated or unknown signals, weak-property flags, vacuity risk, or partial/misaligned labels. The static evaluator is meant to prioritize review and catch obvious drift, not replace engineer review or formal equivalence.

Best-of-k candidate selection is also separate from single-output success. A best candidate can look aligned under these heuristics while other generated candidates are weak or misaligned; report consumers should not reinterpret best-of-k summaries as per-output intent success.

## CLI

Run a local offline smoke:

```powershell
jasperloop align-intent --cases benchmarks/sva_repair_cases.json --candidates reports/repair/artifacts/codex_repair_outputs_20260511T035613Z.jsonl --out-dir reports/alignment --dry-run
```

The command writes a Markdown smoke summary, JSON manifest, and JSONL result records. It does not call Codex, Qwen, JasperGold, Moore, or any external service.

## Labels

- `aligned`: candidate exactly matches the available reference structure with no weak flags and no proof-status-only rationale.
- `likely_aligned`: candidate is structurally close but still bounded as heuristic evidence.
- `partially_aligned`: important structure overlaps, but at least one trigger, delay, or signal issue needs review.
- `likely_misaligned`: consequent loss, unrelated signals, temporal reversal, or severe weak-property evidence.
- `unknown_needs_review`: insufficient reference metadata for a stronger static label.
