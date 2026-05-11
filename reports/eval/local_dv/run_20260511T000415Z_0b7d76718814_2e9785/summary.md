# Retrieval Benchmark Summary: local_dv

- Run ID: `run_20260511T000415Z_0b7d76718814_2e9785`
- Split: `all`
- Top-k: `5`
- Cases: `30`
- Vector backend: `unspecified` (QDRANT_URL and QDRANT_COLLECTION are not configured.)

## Correctness

| Metric | Value |
|---|---:|
| `query_success_rate` | 1.0 |
| `mean_recall_at_k` | 0.408788 |
| `mean_mrr` | 1.0 |

## Latency

| Metric | Value |
|---|---:|
| `avg_ms` | 0.066 |
| `p50_ms` | 0.059 |
| `p95_ms` | 0.102 |
| `timeout_ms` | 1000.0 |

## Cost

| Metric | Value |
|---|---:|
| `external_calls` | 0 |
| `llm_tokens` | 0 |
| `estimated_usd` | 0.0 |
| `indexed_documents` | 39 |
| `indexed_bytes` | 28839 |

## Failure Buckets

| Bucket | Count |
|---|---:|
| `syntax_error` | 0 |
| `missing_premise` | 0 |
| `timeout` | 0 |
| `solver_fail` | 0 |
| `schema_drift` | 0 |

## Contamination Evidence

- Official splits modified: `False`
- Split policy: `by_design_family`
- Indexed answer-bearing case files: `[]`
- Test answer fields indexed: `False`
- Training cache policy: Benchmark originals and repair/gold answers must not enter a training cache unless records retain source, split, and answer-field metadata.

## Notes

- Retrieval path evaluated: sparse symbolic index.
- A canonical `VerifierOutcome` is written for CI gating; no JasperGold solver
  invocation is performed by the retrieval evaluator.
- Vector retrieval is available only when Qdrant and query-vector configuration are supplied.
