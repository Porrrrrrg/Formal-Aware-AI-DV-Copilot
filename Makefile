PYTHON ?= python3
BENCH ?= local_dv
SPLIT ?= test
TOP_K ?= 5
OUT_ROOT ?= reports/eval

.PHONY: test retrieval-registry retrieval-index retrieval-eval nightly-bench

test:
	$(PYTHON) -m pytest

retrieval-registry:
	@if [ -d app/retrieval ]; then \
		$(PYTHON) -m app.retrieval.benchmark_registry --write-local-dv; \
	else \
		echo "app/retrieval not present on this integration branch; skipping retrieval registry."; \
	fi

retrieval-index: retrieval-registry
	@if [ -d app/retrieval ]; then \
		$(PYTHON) -m app.retrieval.symbol_index --benchmark $(BENCH) --out benchmarks/$(BENCH)/symbol_index.json; \
	else \
		echo "app/retrieval not present on this integration branch; skipping retrieval index."; \
	fi

retrieval-eval: retrieval-registry
	@if [ -d app/retrieval ]; then \
		$(PYTHON) -m app.retrieval.evaluate --benchmark $(BENCH) --split $(SPLIT) --top-k $(TOP_K) --out-root $(OUT_ROOT) --write-index; \
	else \
		echo "app/retrieval not present on this integration branch; skipping retrieval eval."; \
	fi

nightly-bench: retrieval-registry
	@if [ -d app/retrieval ]; then \
		$(PYTHON) -m app.retrieval.evaluate --benchmark $(BENCH) --split all --top-k $(TOP_K) --out-root $(OUT_ROOT) --write-index; \
	else \
		echo "app/retrieval not present on this integration branch; skipping retrieval nightly-bench."; \
	fi
