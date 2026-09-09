"""Derived semantic index over agent metadata.

    agents.json  ──authoritative──>  factual metadata (owner, access, URLs)
         │
         └──derived──>  embedding text  ──>  ChromaDB  ──>  ranked by similarity
                                                              │
                                              floors + visibility (search.py)

agents.json stays the source of truth. Nothing is ever read back out of Chroma
as fact: retrieval returns agent ids and a similarity, and the agent itself is
then looked up in the store. Deleting the index directory costs nothing but a
rebuild.

Why this exists: lexical matching has a hard ceiling. The stemmer treats "Risk
scoring" and "Score the risk" as unrelated, and no amount of token overlap
connects "AML" to "anti-money-laundering" or "sanctions screening" to
"watchlist checks". Embeddings do.

Embeddings are computed ONCE per agent and stored. Re-embedding happens only
when an agent's searchable text actually changes, which is detected with a
content fingerprint held in the record's metadata. A query is embedded per
search, because the query is new each time.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from pathlib import Path

from .models import Agent

log = logging.getLogger("mufg.semantic")

COLLECTION = "agents"
# Retrieval is the ranking. Ask for more than we show so the similarity floors
# and the per-user visibility drop still leave a full page.
DEFAULT_CANDIDATES = 12


def embedding_text(agent: Agent) -> str:
    """One natural-language description of the agent, for embedding.

    Field labels are kept so the sentence reads like prose rather than a bag of
    keywords -- retrieval models are trained on prose.
    """
    parts = [
        f"{agent.name}.",
        agent.tagline,
        agent.description,
    ]
    if agent.business_domains:
        parts.append("Business domains: " + ", ".join(agent.business_domains) + ".")
    if agent.capabilities:
        parts.append("Capabilities: " + ", ".join(agent.capabilities) + ".")
    if agent.use_cases:
        parts.append("Use cases: " + "; ".join(agent.use_cases) + ".")
    if agent.tags:
        parts.append("Tags: " + ", ".join(agent.tags) + ".")
    return " ".join(p.strip() for p in parts if p and p.strip())


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def enabled() -> bool:
    return os.environ.get("CREDITWIZ_DISABLE_SEMANTIC") not in ("1", "true")


def _embedding_function():
    """Chroma's default MiniLM, with the ONNX session pinned to one thread.

    onnxruntime sizes its intra-op pool from the HOST's core count. Inside a
    small container that is dozens of threads contending for a fraction of a
    core, and a 50 ms inference took 12-15 s on Render's free tier. One thread
    for a 22M-parameter model on a short query is the right size anywhere.

    Subclasses DefaultEmbeddingFunction rather than the base class so the
    registered name stays "default" and an index created before this change
    reopens without an embedding-function mismatch.
    """
    from functools import cached_property

    from chromadb.utils import embedding_functions

    class OneThreadMiniLM(embedding_functions.DefaultEmbeddingFunction):
        @cached_property
        def model(self):  # type: ignore[override]
            import os as _os

            ort = self.ort
            providers = ort.get_available_providers()
            providers = [p for p in providers if p != "CoreMLExecutionProvider"]
            so = ort.SessionOptions()
            so.log_severity_level = 3
            so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            so.intra_op_num_threads = 1
            so.inter_op_num_threads = 1
            return ort.InferenceSession(
                _os.path.join(self.DOWNLOAD_PATH, self.EXTRACTED_FOLDER_NAME, "model.onnx"),
                providers=providers,
                sess_options=so,
            )

    return OneThreadMiniLM()


class SemanticIndex:
    """Chroma-backed retrieval with a hard rule: never break search.

    Every failure path -- import error, unwritable directory, model download
    failure, a corrupt index -- disables this index and the caller falls back
    to plain token overlap. A prototype that cannot embed should still find
    agents.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._collection = None
        self._broken = False

    def _open(self):
        if self._collection is not None or self._broken or not enabled():
            return self._collection
        with self._lock:
            if self._collection is not None or self._broken:
                return self._collection
            try:
                import chromadb

                from ..database import VAR_DIR

                # Override so a test suite can hold one index for its whole run
                # instead of an empty one per temp directory.
                path = Path(os.environ.get("CREDITWIZ_INDEX_DIR") or VAR_DIR / "chroma")
                path.mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(path=str(path))
                self._collection = client.get_or_create_collection(
                    COLLECTION,
                    embedding_function=_embedding_function(),
                    # Cosine, so a similarity is 1 - distance and comparable
                    # across queries of different lengths.
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as exc:  # noqa: BLE001 - degrade, never fail search
                log.warning("Semantic index unavailable, using lexical search: %s", exc)
                self._broken = True
        return self._collection

    def sync(self, agents: list[Agent]) -> dict[str, int]:
        """Bring the index in line with the catalogue.

        Covers the whole lifecycle in one idempotent pass: new agents are added,
        edited agents are re-embedded, and ids no longer in the catalogue are
        deleted. Unchanged agents are skipped, so a restart re-embeds nothing.
        """
        collection = self._open()
        if collection is None:
            return {"added": 0, "updated": 0, "removed": 0, "unchanged": 0}
        try:
            existing = collection.get(include=["metadatas"])
            known = {
                i: (m or {}).get("fingerprint")
                for i, m in zip(existing["ids"], existing["metadatas"])
            }
            ids, documents, metadatas = [], [], []
            added = updated = unchanged = 0
            for agent in agents:
                text = embedding_text(agent)
                mark = _fingerprint(text)
                if known.get(agent.id) == mark:
                    unchanged += 1
                    continue
                updated += agent.id in known
                added += agent.id not in known
                ids.append(agent.id)
                documents.append(text)
                metadatas.append({"fingerprint": mark, "name": agent.name})
            if ids:
                collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            stale = [i for i in known if i not in {a.id for a in agents}]
            if stale:
                collection.delete(ids=stale)
            return {
                "added": added,
                "updated": updated,
                "removed": len(stale),
                "unchanged": unchanged,
            }
        except Exception as exc:  # noqa: BLE001
            log.warning("Semantic sync failed: %s", exc)
            self._broken = True
            return {"added": 0, "updated": 0, "removed": 0, "unchanged": 0}

    def search(self, query: str, limit: int = DEFAULT_CANDIDATES) -> dict[str, float]:
        """Candidate agent ids mapped to cosine similarity in 0..1.

        An empty result means "nothing close enough", which is also what a
        disabled or broken index returns; the caller then falls back.
        """
        collection = self._open()
        if collection is None or not query.strip():
            return {}
        try:
            found = collection.query(query_texts=[query], n_results=limit)
            ids = found.get("ids", [[]])[0]
            distances = found.get("distances", [[]])[0]
            # Cosine distance can drift marginally outside [0, 2]; clamp so a
            # similarity never leaves 0..1.
            return {
                i: max(0.0, min(1.0, 1.0 - float(d))) for i, d in zip(ids, distances)
            }
        except Exception as exc:  # noqa: BLE001
            log.warning("Semantic query failed, using lexical search: %s", exc)
            return {}

    @property
    def available(self) -> bool:
        """Open AND populated. A collection that exists but holds nothing -- a
        first boot before sync, a wiped disk -- must not answer "no agents";
        the caller falls back instead."""
        collection = self._open()
        if collection is None:
            return False
        try:
            return collection.count() > 0
        except Exception:  # noqa: BLE001
            return False


index = SemanticIndex()
