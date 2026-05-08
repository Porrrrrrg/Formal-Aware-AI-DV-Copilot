# Ablation Results

| Variant | Issue Acc. | Action Acc. | Proven Final | Notes |
| --- | ---: | ---: | ---: | --- |
| Full structured packet | 1.000 | 1.000 | N/A | Deterministic triage scaffold. |
| No assertion manifest | 0.933 | 0.933 | N/A | Removes assertion intent text from the packet. |
| No assumption manifest | 0.800 | 0.800 | N/A | Removes active assumption and assumption-risk context. |
| No JG CEX | 1.000 | 1.000 | N/A | Removes structured counterexample summaries; current scaffold still relies heavily on manifests. |
| No coverage plan | 0.633 | 0.633 | N/A | Removes coverage context, causing coverage cases to collapse into assertion-style diagnoses. |
| Minimal packet | 0.400 | 0.400 | N/A | Keeps only IDs and Jasper status summary. |
| No repair loop | TBD | TBD | TBD | Applies to SVA repair experiments, not current triage scaffold. |
