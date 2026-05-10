from __future__ import annotations

from app.retrieval.vector_index import VectorRetriever


def test_vector_backend_is_unspecified_without_qdrant_env(monkeypatch) -> None:
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_COLLECTION", raising=False)
    status = VectorRetriever().status()
    assert status.backend == "qdrant"
    assert status.status == "unspecified"
    assert "not configured" in status.reason

