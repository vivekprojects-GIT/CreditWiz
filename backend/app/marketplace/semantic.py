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
from collections import OrderedDict
from pathlib import Path

from .models import Agent

log = logging.getLogger("mufg.semantic")

COLLECTION = "agents"
# What each retriever proposes to the fusion step. Matched to RESULT_LIMIT: on
# this catalogue, deepening either retriever to 12 changed no result and no
# ordering on a 14-query check, because the relevance gate cut the extra
# candidates anyway. Revisit alongside the gate if the catalogue grows enough
# that a real match can sit below rank 6 in both retrievers at once.
DEFAULT_CANDIDATES = 6
CACHE_SIZE = 256


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


def _fingerprint(text: str, groups: list[str] | None = None) -> str:
    """Identity of what is stored for an agent: the text and its audience.

    The audience is part of it because it is stored as metadata and filtered
    on. Fingerprinting the text alone would let a permission change pass
    silently, leaving the index enforcing yesterday's audience.
    """
    material = text if not groups else text + str(sorted(groups))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _audience_filter(groups: list[str]) -> dict | None:
    """Chroma `where` restricting results to agents this audience may see.

    Group membership is stored as a list, and Chroma matches into a list with
    `$contains`; `$in` and `$eq` both silently return nothing against a list
    value, so neither is a safe substitute here. `$or` needs at least two
    clauses, hence the single-group case.
    """
    clauses = [{"groups": {"$contains": g}} for g in sorted(set(groups))]
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$or": clauses}


def enabled() -> bool:
    return os.environ.get("CREDITWIZ_DISABLE_SEMANTIC") not in ("1", "true")


def _embedding_function():
    """One long-lived MiniLM with its ONNX session built once and pinned to one thread.

    Chroma's DefaultEmbeddingFunction is a thin wrapper whose __call__ does
    `return ONNXMiniLM_L6_V2()(input)`: it constructs a NEW model object per
    call, and each one builds its own InferenceSession from model.onnx. Every
    search was loading and graph-optimising the model from disk -- ~130 ms on
    a laptop, 4.5-6.6 s on a tenth of a core on Render. Holding one instance
    makes session construction a one-off, so the per-query cost is inference
    alone. That instance also pins onnxruntime to one intra-op thread: ORT
    otherwise sizes its pool from the host's core count, which in a small
    container is dozens of threads contending for a fraction of a core.

    name() still reports "default" so an index created with the stock
    function reopens without an embedding-function mismatch; it is the same
    model producing the same vectors.
    """
    from functools import cached_property

    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

    class OneSessionMiniLM(ONNXMiniLM_L6_V2):
        @cached_property
        def model(self):  # type: ignore[override]
            providers = [
                p for p in self.ort.get_available_providers() if p != "CoreMLExecutionProvider"
            ]
            so = self.ort.SessionOptions()
            so.log_severity_level = 3
            so.graph_optimization_level = self.ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            so.intra_op_num_threads = 1
            so.inter_op_num_threads = 1
            return self.ort.InferenceSession(
                os.path.join(self.DOWNLOAD_PATH, self.EXTRACTED_FOLDER_NAME, "model.onnx"),
                providers=providers,
                sess_options=so,
            )

        @staticmethod
        def name() -> str:
            return "default"

    return OneSessionMiniLM()


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
        # Retrieval results keyed by (text, limit). The embedding is the whole
        # cost of a search, and demo queries repeat; a hit skips the model
        # entirely. Cleared whenever sync() changes the index.
        self._cache: OrderedDict[
            tuple[str, int, tuple[str, ...]], dict[str, float]
        ] = OrderedDict()

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
                mark = _fingerprint(text, agent.audience_groups)
                if known.get(agent.id) == mark:
                    unchanged += 1
                    continue
                updated += agent.id in known
                added += agent.id not in known
                ids.append(agent.id)
                documents.append(text)
                metadata: dict[str, object] = {
                    "fingerprint": mark,
                    "name": agent.name,
                }
                # An agent with no audience is visible to nobody, so leave the
                # key off entirely: a $contains filter then cannot match it.
                if agent.audience_groups:
                    metadata["groups"] = list(agent.audience_groups)
                metadatas.append(metadata)
            if ids:
                collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            stale = [i for i in known if i not in {a.id for a in agents}]
            if stale:
                collection.delete(ids=stale)
            if ids or stale:
                self._cache.clear()
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

    def search(
        self,
        query: str,
        limit: int = DEFAULT_CANDIDATES,
        groups: list[str] | None = None,
    ) -> dict[str, float]:
        """Candidate agent ids mapped to cosine similarity in 0..1.

        `groups` is the caller's audience. Passing it filters inside the query,
        so the candidates come back already permitted: the alternative is to
        retrieve globally and drop afterwards, which silently costs recall,
        because invisible agents occupy slots that permitted ones would have
        taken. Callers still apply their own visibility check -- this narrows
        what is ranked, it is not the security boundary on its own.

        An empty result means "nothing close enough", which is also what a
        disabled or broken index returns; the caller then falls back.
        """
        collection = self._open()
        if collection is None or not query.strip():
            return {}
        audience = tuple(sorted(set(groups))) if groups is not None else ()
        if groups is not None and not audience:
            # Belongs to no group, so may see nothing. Chroma cannot express an
            # always-false filter, and there is nothing to ask it for anyway.
            return {}
        key = (query.strip().lower(), limit, audience)
        hit = self._cache.get(key)
        if hit is not None:
            self._cache.move_to_end(key)
            return dict(hit)
        try:
            where = _audience_filter(groups) if groups is not None else None
            found = collection.query(
                query_texts=[query], n_results=limit, **({"where": where} if where else {})
            )
            ids = found.get("ids", [[]])[0]
            distances = found.get("distances", [[]])[0]
            # Cosine distance can drift marginally outside [0, 2]; clamp so a
            # similarity never leaves 0..1.
            result = {
                i: max(0.0, min(1.0, 1.0 - float(d))) for i, d in zip(ids, distances)
            }
            self._cache[key] = dict(result)
            if len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
            return result
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
