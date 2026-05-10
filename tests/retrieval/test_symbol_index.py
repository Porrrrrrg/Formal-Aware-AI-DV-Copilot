from __future__ import annotations

from app.retrieval.benchmark_registry import build_local_dv_registry
from app.retrieval.symbol_index import SymbolIndex, extract_symbols


def test_extract_symbols_keeps_sva_identifiers() -> None:
    symbols = extract_symbols("p_mutex: assert property (!(gnt0 && gnt1)); $stable(out_data)")
    assert "p_mutex" in symbols
    assert "gnt0" in symbols
    assert "$stable" in symbols
    assert "out_data" in symbols


def test_symbol_index_retrieves_design_context() -> None:
    registry = build_local_dv_registry()
    index = SymbolIndex.from_registry(registry)
    hits = index.search(
        "apb_regblock p_read_next_cycle PSEL PENABLE PRDATA read latency",
        top_k=5,
        design_id="apb_regblock",
    )
    assert hits
    assert any(hit.design_id == "apb_regblock" for hit in hits)
    assert any(hit.kind in {"formal", "rtl", "spec", "manifest"} for hit in hits)

