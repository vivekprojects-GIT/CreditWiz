"""Keyword (BM25) index over the same searchable text the semantic index embeds.

Semantic retrieval is strong on meaning and weak on exact tokens: near-duplicate
names ("Sanctions Review Agent v2" vs "... EMEA"), acronyms and IDs. BM25 is the
opposite. Hybrid search fuses the two by RANK (see search.rank), so their
incomparable score scales never meet.

Both rankers read `semantic.embedding_text(agent)`, so an agent is described
identically to both and a difference in ranking is a difference in method,
not in input. Built in-process, no dependency: at catalogue scale (hundreds to
low thousands of agents) scoring a query is O(agents x query terms) and takes
microseconds. Rebuilt only when the catalogue's ids or texts change.
"""

from __future__ import annotations

import hashlib
import math
import threading

from .models import Agent

# Standard BM25 parameters: k1 = term-frequency saturation, b = length normalisation.
K1 = 1.5
B = 0.75
DEFAULT_CANDIDATES = 12


class KeywordIndex:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fingerprint = ""
        self._docs: dict[str, list[str]] = {}
        self._df: dict[str, int] = {}
        self._avgdl = 1.0

    def sync(self, agents: list[Agent]) -> bool:
        """Rebuild if the catalogue changed. Returns True when it did."""
        from .search import tokens
        from .semantic import embedding_text

        texts = {a.id: embedding_text(a) for a in agents}
        mark = hashlib.sha256(
            "\n".join(f"{i}\t{t}" for i, t in sorted(texts.items())).encode("utf-8")
        ).hexdigest()[:16]
        if mark == self._fingerprint:
            return False
        with self._lock:
            docs = {i: tokens(t) for i, t in texts.items()}
            df: dict[str, int] = {}
            for terms in docs.values():
                for term in set(terms):
                    df[term] = df.get(term, 0) + 1
            self._docs = docs
            self._df = df
            self._avgdl = (sum(len(d) for d in docs.values()) / len(docs)) if docs else 1.0
            self._fingerprint = mark
        return True

    def search(self, text: str, limit: int = DEFAULT_CANDIDATES) -> dict[str, float]:
        """Agent ids mapped to BM25 score, best first, only agents with a hit."""
        from .search import tokens

        query = tokens(text)
        if not query or not self._docs:
            return {}
        n = len(self._docs)
        scored: dict[str, float] = {}
        for agent_id, doc in self._docs.items():
            score = 0.0
            dl = len(doc)
            for term in query:
                df = self._df.get(term)
                if not df:
                    continue
                tf = doc.count(term)
                if not tf:
                    continue
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * dl / self._avgdl))
            if score > 0:
                scored[agent_id] = round(score, 4)
        top = sorted(scored.items(), key=lambda kv: -kv[1])[:limit]
        return dict(top)

    @property
    def size(self) -> int:
        return len(self._docs)


index = KeywordIndex()
