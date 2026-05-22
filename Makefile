PYTHON ?= python3
BENCH ?= local_dv
SPLIT ?= test
TOP_K ?= 5
OUT_ROOT ?= reports/eval

.PHONY: test retrieval-registry retrieval-index retrieval-eval nightly-bench

test:
	$(PYTHON) -m pytest

retrieval-registry:
	$(PYTHON) -m app.retrieval.benchmark_registry --write-local-dv

retrieval-index: retrieval-registry
	$(PYTHON) -m app.retrieval.symbol_index --benchmark $(BENCH) --out benchmarks/$(BENCH)/symbol_index.json

retrieval-eval: retrieval-registry
	$(PYTHON) -m app.retrieval.evaluate --benchmark $(BENCH) --split $(SPLIT) --top-k $(TOP_K) --out-root $(OUT_ROOT) --write-index

nightly-bench: retrieval-registry
	$(PYTHON) -m app.retrieval.evaluate --benchmark $(BENCH) --split all --top-k $(TOP_K) --out-root $(OUT_ROOT) --write-index
