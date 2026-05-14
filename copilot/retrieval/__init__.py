"""ProofLoop-style RTL retrieval helpers for copilot agents."""

from copilot.retrieval.rtl_index import (
    build_rtl_index,
    get_clock_reset_candidates,
    get_hierarchy,
    get_module_interface,
    get_signal_logic,
    search_signal,
)

__all__ = [
    "build_rtl_index",
    "get_clock_reset_candidates",
    "get_hierarchy",
    "get_module_interface",
    "get_signal_logic",
    "search_signal",
]
