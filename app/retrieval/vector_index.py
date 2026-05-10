"""Optional vector retrieval backend.

Qdrant is supported only when the caller supplies configuration. This module
does not invent connection parameters or embeddings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VectorBackendStatus:
    backend: str
    status: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {"backend": self.backend, "status": self.status, "reason": self.reason}


@dataclass(frozen=True)
class QdrantConfig:
    url: str
    collection: str
    api_key: str | None = None
    vector_name: str | None = None

    @classmethod
    def from_env(cls) -> "QdrantConfig | None":
        url = os.environ.get("QDRANT_URL")
        collection = os.environ.get("QDRANT_COLLECTION")
        if not url or not collection:
            return None
        return cls(
            url=url,
            collection=collection,
            api_key=os.environ.get("QDRANT_API_KEY"),
            vector_name=os.environ.get("QDRANT_VECTOR_NAME"),
        )


class VectorRetriever:
    """Small Qdrant wrapper that searches precomputed vectors."""

    def __init__(self, config: QdrantConfig | None = None):
        self.config = config or QdrantConfig.from_env()
        self._client: Any | None = None

    def status(self) -> VectorBackendStatus:
        if self.config is None:
            return VectorBackendStatus(
                backend="qdrant",
                status="unspecified",
                reason="QDRANT_URL and QDRANT_COLLECTION are not configured.",
            )
        try:
            import qdrant_client  # noqa: F401
        except ImportError:
            return VectorBackendStatus(
                backend="qdrant",
                status="unavailable",
                reason="qdrant_client is not installed in the active Python environment.",
            )
        return VectorBackendStatus(
            backend="qdrant",
            status="configured",
            reason="Qdrant connection parameters are present; caller must provide query vectors.",
        )

    def _ensure_client(self) -> Any:
        status = self.status()
        if status.status != "configured" or self.config is None:
            raise RuntimeError(status.reason)
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(url=self.config.url, api_key=self.config.api_key)
        return self._client

    def search_by_vector(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        if not query_vector:
            raise ValueError("query_vector must be a non-empty vector")
        if self.config is None:
            return []
        client = self._ensure_client()
        kwargs: dict[str, Any] = {
            "collection_name": self.config.collection,
            "query_vector": query_vector,
            "limit": top_k,
            "with_payload": True,
        }
        if self.config.vector_name:
            kwargs["query_vector"] = (self.config.vector_name, query_vector)
        results = client.search(**kwargs)
        return [
            {
                "id": str(point.id),
                "score": float(point.score),
                "payload": dict(point.payload or {}),
            }
            for point in results
        ]

