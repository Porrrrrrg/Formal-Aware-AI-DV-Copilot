"""Benchmark registry helpers.

The local DV benchmark is intentionally represented as a repo-local overlay:
it references existing benchmark files, records a split policy, and excludes
answer-bearing case files from the retrieval corpus by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DV_DESIGN_SPLITS = {
    "arbiter_rr2": "train",
    "rv_buffer": "dev",
    "apb_regblock": "test",
    "fifo_1r1w": "test",
}
PUBLIC_SOURCE_NAMES = ["miniF2F", "ProofNet", "SMT-LIB", "traced_repos"]


def resolve_repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_json(path: Path | str) -> Any:
    return json.loads(resolve_repo_path(path).read_text())


def write_json(path: Path | str, payload: Any) -> None:
    resolved = resolve_repo_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def _document_id(benchmark: str, path: Path) -> str:
    rel = repo_relative(path)
    stem = rel.replace("/", ":").replace("\\", ":")
    return f"{benchmark}:{stem}"


def _kind_for(path: Path) -> str:
    parts = set(path.parts)
    if path.name == "spec.md":
        return "spec"
    if "rtl" in parts:
        return "rtl"
    if "formal" in parts:
        return "formal"
    if "manifests" in parts:
        return "manifest"
    if "coverage" in parts:
        return "coverage"
    return "context"


def _document_record(benchmark: str, design: str, path: Path) -> dict[str, Any]:
    return {
        "doc_id": _document_id(benchmark, path),
        "path": repo_relative(path),
        "design_id": design,
        "kind": _kind_for(path),
        "sha256": file_sha256(path),
        "contains_gold_answer": False,
    }


def discover_local_dv_documents(benchmark: str = "local_dv") -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for design in LOCAL_DV_DESIGN_SPLITS:
        design_root = ROOT / "benchmarks" / design
        paths = [design_root / "spec.md"]
        for subdir, patterns in {
            "rtl": ["*.sv"],
            "formal": ["*.sv", "*.tcl"],
            "manifests": ["*.yaml", "*.yml"],
            "coverage": ["*.yaml", "*.yml"],
        }.items():
            folder = design_root / subdir
            for pattern in patterns:
                paths.extend(sorted(folder.glob(pattern)))
        for path in sorted({path for path in paths if path.exists()}):
            documents.append(_document_record(benchmark, design, path))
    return documents


def discover_local_dv_items(
    documents: list[dict[str, Any]],
    benchmark: str = "local_dv",
) -> list[dict[str, Any]]:
    docs_by_design: dict[str, list[dict[str, Any]]] = {}
    for doc in documents:
        docs_by_design.setdefault(str(doc["design_id"]), []).append(doc)

    items: list[dict[str, Any]] = []
    for design, split in LOCAL_DV_DESIGN_SPLITS.items():
        case_dir = ROOT / "benchmarks" / design / "cases"
        for case_path in sorted(case_dir.glob("*.json")):
            case = json.loads(case_path.read_text())
            variant = case.get("variant")
            gold_docs = [
                doc["doc_id"]
                for doc in docs_by_design.get(design, [])
                if doc["kind"] in {"spec", "formal", "manifest", "coverage"}
            ]
            if variant:
                variant_text = str(variant)
                for doc in docs_by_design.get(design, []):
                    if doc["kind"] == "rtl" and (
                        variant_text in Path(str(doc["path"])).stem
                        or Path(str(doc["path"])).stem.endswith("_correct")
                    ):
                        gold_docs.append(doc["doc_id"])
            items.append(
                {
                    "item_id": f"{benchmark}:{case['case_id']}",
                    "case_id": case["case_id"],
                    "case_path": repo_relative(case_path),
                    "design_id": design,
                    "split": split,
                    "task_type": case.get("task_type", "unspecified"),
                    "property_id": case.get("property_id"),
                    "query_fields": [
                        "case_id",
                        "design_id",
                        "variant",
                        "task_type",
                        "property_id",
                        "property_intent",
                        "design_intent",
                    ],
                    "gold_context_doc_ids": sorted(set(gold_docs)),
                    "answer_fields": [
                        "expected_issue_type",
                        "expected_next_action",
                        "root_cause",
                    ],
                }
            )
    return items


def split_payloads(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for split in ["train", "dev", "test"]:
        split_items = [item for item in items if item["split"] == split]
        payloads[split] = {
            "split": split,
            "policy": "repo-local overlay; split by design family",
            "design_ids": sorted({str(item["design_id"]) for item in split_items}),
            "item_ids": [str(item["item_id"]) for item in split_items],
        }
    return payloads


def contamination_evidence(
    items: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    split_to_cases: dict[str, set[str]] = {}
    split_to_designs: dict[str, set[str]] = {}
    for item in items:
        split_to_cases.setdefault(str(item["split"]), set()).add(str(item["case_id"]))
        split_to_designs.setdefault(str(item["split"]), set()).add(str(item["design_id"]))

    case_overlaps: dict[str, list[str]] = {}
    design_overlaps: dict[str, list[str]] = {}
    splits = sorted(split_to_cases)
    for idx, left in enumerate(splits):
        for right in splits[idx + 1 :]:
            key = f"{left}:{right}"
            case_overlaps[key] = sorted(split_to_cases[left] & split_to_cases[right])
            design_overlaps[key] = sorted(split_to_designs[left] & split_to_designs[right])

    indexed_case_paths = [
        doc["path"]
        for doc in documents
        if "/cases/" in str(doc["path"]) or str(doc["path"]).endswith("_cases.json")
    ]
    return {
        "official_splits_modified": False,
        "split_policy": "by_design_family",
        "case_id_overlaps": case_overlaps,
        "design_id_overlaps": design_overlaps,
        "indexed_case_or_answer_files": indexed_case_paths,
        "test_answer_fields_indexed": False,
        "training_cache_policy": (
            "Benchmark originals and repair/gold answers must not enter a training cache "
            "unless records retain source, split, and answer-field metadata."
        ),
    }


def build_local_dv_registry() -> dict[str, Any]:
    benchmark = "local_dv"
    documents = discover_local_dv_documents(benchmark)
    items = discover_local_dv_items(documents, benchmark)
    present_sources = [
        {
            "name": "local_rtl_dv",
            "status": "present",
            "path": "benchmarks/{arbiter_rr2,rv_buffer,apb_regblock,fifo_1r1w}",
            "notes": "Repo-local SVA/RTL DV benchmark assets.",
        }
    ]
    absent_sources = [
        {
            "name": name,
            "status": "absent",
            "path": None,
            "notes": "No checked-in source directory found during registry creation.",
        }
        for name in PUBLIC_SOURCE_NAMES
    ]
    return {
        "name": benchmark,
        "version": "2026-05-10-local-overlay",
        "description": "Repo-local DV benchmark overlay for retrieval and nightly regression.",
        "source_priority": "Use checked-in benchmark assets before external public datasets.",
        "sources": present_sources + absent_sources,
        "splits": {
            "train": "benchmarks/local_dv/splits/train.json",
            "dev": "benchmarks/local_dv/splits/dev.json",
            "test": "benchmarks/local_dv/splits/test.json",
        },
        "documents": documents,
        "items": items,
        "contamination_evidence": contamination_evidence(items, documents),
        "vector_backend": {
            "status": "unspecified",
            "reason": "Qdrant URL/collection and embedding configuration are not present in repo.",
        },
    }


def registry_path(benchmark: str) -> Path:
    return ROOT / "benchmarks" / benchmark / "registry.json"


def load_registry(benchmark: str = "local_dv", path: Path | None = None) -> dict[str, Any]:
    path = path or registry_path(benchmark)
    return load_json(path)


def write_local_dv_registry(out_dir: Path | str = Path("benchmarks/local_dv")) -> dict[str, Any]:
    registry = build_local_dv_registry()
    out_dir = resolve_repo_path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "registry.json", registry)
    split_dir = out_dir / "splits"
    for split, payload in split_payloads(registry["items"]).items():
        write_json(split_dir / f"{split}.json", payload)
    readme = out_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# local_dv Benchmark Overlay",
                "",
                "This directory is a repo-local benchmark registry for the checked-in RTL/SVA DV",
                "cases under `benchmarks/arbiter_rr2`, `benchmarks/rv_buffer`,",
                "`benchmarks/apb_regblock`, and `benchmarks/fifo_1r1w`.",
                "",
                "Split policy:",
                "",
                "- `train`: `arbiter_rr2`",
                "- `dev`: `rv_buffer`",
                "- `test`: `apb_regblock`, `fifo_1r1w`",
                "",
                "The split is by design family, so case IDs and design IDs do not overlap across",
                "train/dev/test. The retrieval corpus excludes `cases/*.json` and top-level",
                "`*_cases.json` answer-bearing files by default. Public benchmark sources such as",
                "miniF2F, ProofNet, SMT-LIB, and traced repos are recorded as absent unless a",
                "checked-in source directory is later added.",
                "",
            ]
        )
    )
    return registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-local-dv", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("benchmarks/local_dv"))
    args = parser.parse_args()
    if args.write_local_dv:
        registry = write_local_dv_registry(args.out_dir)
    else:
        registry = build_local_dv_registry()
    print(
        json.dumps(
            {
                "name": registry["name"],
                "items": len(registry["items"]),
                "documents": len(registry["documents"]),
                "splits": registry["splits"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

