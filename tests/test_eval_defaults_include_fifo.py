from __future__ import annotations

import inspect
from pathlib import Path

from evaluation import run_agent_eval, run_coverage_eval
from scripts import refresh_eval_results


def test_refresh_eval_defaults_include_fifo() -> None:
    assert Path("benchmarks/fifo_1r1w/cases") in refresh_eval_results.CASE_DIRS


def test_eval_runner_help_defaults_include_fifo() -> None:
    assert "benchmarks/fifo_1r1w/cases" in inspect.getsource(run_agent_eval.main)
    assert "benchmarks/fifo_1r1w/cases" in inspect.getsource(run_coverage_eval.main)
