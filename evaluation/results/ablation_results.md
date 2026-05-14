# Ablation Results

| Variant | Issue Acc. | Action Acc. | Proven Final | Notes |
| --- | ---: | ---: | ---: | --- |
| Full structured packet | 0.906 | 0.906 | N/A | Deterministic triage scaffold. |
| No assertion manifest | 0.868 | 0.868 | N/A | Removes assertion intent text from the packet. |
| No assumption manifest | 0.755 | 0.755 | N/A | Removes active assumption and assumption-risk context. |
| No JG CEX | 0.906 | 0.906 | N/A | Removes structured counterexample summaries; current scaffold still relies heavily on manifests. |
| No coverage plan | 0.604 | 0.604 | N/A | Removes coverage context, causing coverage cases to collapse into assertion-style diagnoses. |
| Minimal packet | 0.434 | 0.434 | N/A | Keeps only IDs and Jasper status summary. |
| No repair loop | TBD | TBD | TBD | Applies to SVA repair experiments, not current triage scaffold. |
