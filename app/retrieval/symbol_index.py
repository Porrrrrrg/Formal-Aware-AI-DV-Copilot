"""Sparse symbol index for benchmark context retrieval."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.retrieval.benchmark_registry import load_registry, repo_relative, resolve_repo_path

TOKEN_RE = re.compile(r"\$?[A-Za-z_][A-Za-z0-9_$]*|[0-9]+'[bdho][0-9a-fA-F_xzXZ]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "can",
    "for",
    "from",
    "if",
    "in",
    "is",
    "must",
    "not",
    "of",
    "on",
    "or",
    "per",
    "the",
    "to",
    "under",
    "when",
}


@dataclass(frozen=True)
class RetrievalHit:
    doc_id: str
    path: str
    score: float
    matched_symbols: list[str]
    kind: str
    design_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "path": self.path,
            "score": self.score,
            "matched_symbols": self.matched_symbols,
            "kind": self.kind,
            "design_id": self.design_id,
        }


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().lower()


def extract_symbols(text: str) -> list[str]:
    symbols = []
    for match in TOKEN_RE.finditer(text):
        token = normalize_symbol(match.group(0))
        if len(token) <= 1 or token in STOPWORDS:
            continue
        symbols.append(token)
    return symbols


def content_hash(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


class SymbolIndex:
    """Simple BM25-like sparse index over code/spec symbols."""

    def __init__(self, documents: list[dict[str, Any]], postings: dict[str, dict[str, int]]):
        self.documents = {str(doc["doc_id"]): doc for doc in documents}
        self.postings = postings
        self.document_count = len(documents)
        self.doc_lengths = {
            doc_id: sum(counts.get(doc_id, 0) for counts in postings.values())
            for doc_id in self.documents
        }
        self.avg_doc_length = (
            sum(self.doc_lengths.values()) / self.document_count if self.document_count else 0.0
        )

    @classmethod
    def from_registry(cls, registry: dict[str, Any]) -> "SymbolIndex":
        indexed_docs: list[dict[str, Any]] = []
        postings: dict[str, dict[str, int]] = {}
        for doc in registry.get("documents", []):
            path = resolve_repo_path(str(doc["path"]))
            text = path.read_text(errors="ignore")
            counts = collections.Counter(extract_symbols(text))
            doc_record = dict(doc)
            doc_record["content_sha256"] = content_hash(text)
            doc_record["bytes"] = path.stat().st_size
            doc_record["symbol_count"] = sum(counts.values())
            indexed_docs.append(doc_record)
            for symbol, count in counts.items():
                postings.setdefault(symbol, {})[str(doc["doc_id"])] = count
        return cls(indexed_docs, postings)

    def search(
        self,
        query: str,
        top_k: int = 5,
        design_id: str | None = None,
        kinds: set[str] | None = None,
    ) -> list[RetrievalHit]:
        query_counts = collections.Counter(extract_symbols(query))
        if not query_counts:
            return []
        scores: dict[str, float] = collections.defaultdict(float)
        matched: dict[str, set[str]] = collections.defaultdict(set)
        avg_len = self.avg_doc_length or 1.0
        for symbol, query_tf in query_counts.items():
            doc_counts = self.postings.get(symbol, {})
            if not doc_counts:
                continue
            idf = math.log((self.document_count + 1) / (len(doc_counts) + 0.5)) + 1.0
            for doc_id, doc_tf in doc_counts.items():
                doc = self.documents[doc_id]
                if design_id and doc.get("design_id") != design_id:
                    continue
                if kinds and doc.get("kind") not in kinds:
                    continue
                length_norm = 1.0 + 0.25 * (self.doc_lengths.get(doc_id, 0) / avg_len)
                scores[doc_id] += (query_tf * doc_tf * idf) / length_norm
                matched[doc_id].add(symbol)

        hits = []
        for doc_id, score in scores.items():
            doc = self.documents[doc_id]
            path_text = str(doc.get("path", "")).lower()
            if design_id and design_id.lower() in path_text:
                score *= 1.15
            hits.append(
                RetrievalHit(
                    doc_id=doc_id,
                    path=str(doc["path"]),
                    score=round(score, 6),
                    matched_symbols=sorted(matched[doc_id])[:20],
                    kind=str(doc.get("kind", "context")),
                    design_id=str(doc.get("design_id")) if doc.get("design_id") else None,
                )
            )
        return sorted(hits, key=lambda hit: (-hit.score, hit.path))[:top_k]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "jasperloop.symbol_index.v1",
            "document_count": self.document_count,
            "documents": sorted(self.documents.values(), key=lambda doc: str(doc["doc_id"])),
            "postings": self.postings,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SymbolIndex":
        return cls(
            documents=list(payload.get("documents", [])),
            postings={
                str(symbol): {str(doc_id): int(count) for doc_id, count in doc_counts.items()}
                for symbol, doc_counts in payload.get("postings", {}).items()
            },
        )

    def save(self, path: Path | str) -> None:
        resolved = resolve_repo_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n")

    @classmethod
    def load(cls, path: Path | str) -> "SymbolIndex":
        return cls.from_dict(json.loads(resolve_repo_path(path).read_text()))


def timed_search(
    index: SymbolIndex,
    query: str,
    top_k: int,
    design_id: str | None = None,
) -> tuple[list[RetrievalHit], float]:
    started = time.perf_counter()
    hits = index.search(query=query, top_k=top_k, design_id=design_id)
    return hits, (time.perf_counter() - started) * 1000.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="local_dv")
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--out", type=Path, default=Path("benchmarks/local_dv/symbol_index.json"))
    args = parser.parse_args()
    registry = load_registry(args.benchmark, args.registry)
    index = SymbolIndex.from_registry(registry)
    index.save(args.out)
    print(
        json.dumps(
            {
                "benchmark": args.benchmark,
                "index": repo_relative(resolve_repo_path(args.out)),
                "documents": index.document_count,
                "symbols": len(index.postings),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
