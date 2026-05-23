from __future__ import annotations

from app.retrieval.benchmark_registry import build_local_dv_registry, split_payloads


def test_local_dv_registry_splits_by_design_without_overlap() -> None:
    registry = build_local_dv_registry()
    split_to_designs: dict[str, set[str]] = {}
    split_to_cases: dict[str, set[str]] = {}
    for item in registry["items"]:
        split_to_designs.setdefault(item["split"], set()).add(item["design_id"])
        split_to_cases.setdefault(item["split"], set()).add(item["case_id"])

    assert len(registry["items"]) == 53
    assert split_to_designs == {
        "train": {"arbiter_rr2"},
        "dev": {"rv_buffer"},
        "test": {"apb_regblock", "fifo_1r1w"},
    }
    assert not (split_to_cases["train"] & split_to_cases["dev"])
    assert not (split_to_cases["train"] & split_to_cases["test"])
    assert not (split_to_cases["dev"] & split_to_cases["test"])


def test_registry_retrieval_documents_exclude_answer_bearing_cases() -> None:
    registry = build_local_dv_registry()
    paths = [doc["path"] for doc in registry["documents"]]
    assert paths
    assert all("/cases/" not in path for path in paths)
    assert all(not path.endswith("_cases.json") for path in paths)
    assert all(doc["contains_gold_answer"] is False for doc in registry["documents"])
    assert registry["contamination_evidence"]["indexed_case_or_answer_files"] == []


def test_split_payloads_reference_registry_items() -> None:
    registry = build_local_dv_registry()
    payloads = split_payloads(registry["items"])
    assert set(payloads) == {"train", "dev", "test"}
    assert len(payloads["train"]["item_ids"]) == 12
    assert len(payloads["dev"]["item_ids"]) == 12
    assert len(payloads["test"]["item_ids"]) == 29
